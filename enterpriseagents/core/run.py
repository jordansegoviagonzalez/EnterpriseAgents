from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from enterpriseagents.agents.builder import BuilderAgent
from enterpriseagents.agents.director import DirectorAgent
from enterpriseagents.agents.docs import DocsAgent
from enterpriseagents.agents.reviewer import ReviewerAgent
from enterpriseagents.audit.logger import AuditLogger
from enterpriseagents.core.events import Event, EventType
from enterpriseagents.core.kanban import KanbanBoard
from enterpriseagents.core.models import TaskStatus
from enterpriseagents.core.router import DynamicRouter, NextAction
from enterpriseagents.memory.store import MemoryStore
from enterpriseagents.policy.approvals import Approver, DenyByDefaultApprover
from enterpriseagents.policy.policy import PolicyEngine
from enterpriseagents.tools.registry import ToolRegistry
from enterpriseagents.utils.time import utc_now_iso


@dataclass(frozen=True)
class RunRequest:
    instruction: str
    workspace: str
    dry_run: bool = False


class RunCoordinator:
    """Manages the complete lifecycle of a workflow execution.

    The Run Coordinator serves as the central orchestration engine. It initializes
    the environment, manages the Kanban state, facilitates communication between agents
    via the Dynamic Router, and ensures that all events are properly audited and
    governed by policy.
    """

    def __init__(
        self,
        *,
        run_id: str,
        audit: AuditLogger,
        policy: PolicyEngine,
        tools: ToolRegistry,
        director: DirectorAgent,
        builder: BuilderAgent,
        reviewer: ReviewerAgent,
        docs: DocsAgent,
        router: DynamicRouter,
        memory: MemoryStore,
        approver: Approver | None = None,
    ) -> None:
        self._run_id = run_id
        self._audit = audit
        self._policy = policy
        self._tools = tools
        self._director = director
        self._builder = builder
        self._reviewer = reviewer
        self._docs = docs
        self._router = router
        self._memory = memory
        self._approver = approver or DenyByDefaultApprover()

    def execute(self, req: RunRequest) -> None:
        Path(req.workspace).mkdir(parents=True, exist_ok=True)

        self._audit.event(
            Event(
                type=EventType.RUN_STARTED,
                ts=utc_now_iso(),
                run_id=self._run_id,
                payload={"instruction": req.instruction},
            )
        )

        board = KanbanBoard(run_id=self._run_id)

        # Initial Planning Phase (Mandatory start)
        tasks = self._director.plan(req.instruction)

        # Save plan
        self._audit.save_plan({"tasks": [t.model_dump() for t in tasks]})

        for ev in board.add_tasks(tasks):
            self._audit.event(ev)

        # Dynamic Execution Loop
        while True:
            # Save task graph state
            self._audit.save_task_graph({"tasks": [t.model_dump() for t in board.tasks.values()]})

            # Ask the Brain what to do next
            decision = self._router.decide(board)

            if decision.action == NextAction.FINISH:
                break

            if decision.action == NextAction.PLAN:
                # In a future iteration, we can replan.
                # For now, we assume initial plan is sufficient or log a warning.
                pass

            elif decision.action == NextAction.WORK:
                task = board.next_ready()
                if task:
                    self._audit.event(board.move(task.id, TaskStatus.DOING))
                    self._run_builder(task, req.workspace, req.dry_run, board)

            elif decision.action == NextAction.REVIEW:
                # Find tasks that need review
                for t in board.tasks.values():
                    if t.status == TaskStatus.REVIEW:
                        self._run_reviewer(t, req.workspace, req.dry_run, board)

        # Final Documentation Phase
        self._run_docs(req.workspace, req.instruction, req.dry_run)

        self._audit.finish(workspace=req.workspace)
        self._audit.event(
            Event(
                type=EventType.RUN_FINISHED,
                ts=utc_now_iso(),
                run_id=self._run_id,
                payload={"workspace": req.workspace},
            )
        )

    def _run_builder(self, task: Any, workspace: str, dry_run: bool, board: KanbanBoard) -> None:
        tool_calls = self._builder.propose(task=task, workspace=workspace)
        for call in tool_calls:
            if not self._execute_tool(call, workspace, dry_run):
                self._audit.event(board.move(task.id, TaskStatus.BLOCKED))
                return
        self._audit.event(board.move(task.id, TaskStatus.REVIEW))

    def _run_reviewer(self, task: Any, workspace: str, dry_run: bool, board: KanbanBoard) -> None:
        review = self._reviewer.review(task=task, workspace=workspace, dry_run=dry_run)

        # Save test results
        for ev in review.events:
            if ev.type == EventType.TOOL_RESULT:
                cmd = ev.payload.get("cmd", "Unknown")
                ok = ev.payload.get("ok", False)
                output = ev.payload.get("output", "")
                self._audit.save_test_results(
                    f"Task {task.id} Check: {cmd} -> {'PASS' if ok else 'FAIL'}\nOutput: {output}\n"
                )

        if review.ok:
            self._audit.event(board.move(task.id, TaskStatus.DONE))
        else:
            # Send back to backlog or ready to retry
            self._audit.event(board.move(task.id, TaskStatus.READY))

    def _run_docs(self, workspace: str, instruction: str, dry_run: bool) -> None:
        docs_calls = self._docs.finalize(workspace=workspace, instruction=instruction)
        for call in docs_calls:
            self._execute_tool(call, workspace, dry_run)

        # Generate evidence packet
        evidence_md = (
            f"# EnterpriseAgents Run Evidence\n\n"
            f"**Run ID:** {self._run_id}\n"
            f"**Workspace:** {workspace}\n"
            f"**Instruction:** {instruction}\n\n"
            "This packet certifies that the software factory executed the workflow."
        )
        self._audit.save_evidence(evidence_md)

    def _execute_tool(self, call: Any, workspace: str, dry_run: bool) -> bool:
        decision = self._policy.evaluate(call=call, workspace=workspace)
        self._audit.approval(decision.to_record(call))
        self._audit.tool_call(call)

        if decision.denied:
            return False

        if decision.requires_approval:
            approval = self._approver.request(call=call, policy_decision=decision)
            self._audit.approval(approval.to_record(call=call, policy_decision=decision))
            if not approval.approved:
                self._audit.tool_result(
                    call.call_id,
                    ok=False,
                    output=f"APPROVAL_DENIED: {approval.reason or 'No reason provided'}",
                )
                return False

        if dry_run:
            self._audit.tool_result(call.call_id, ok=True, output="DRY_RUN: not executed")
            return True

        result = self._tools.execute(call=call, workspace=workspace)
        self._audit.tool_result(result.call_id, ok=result.ok, output=result.output)
        return result.ok
