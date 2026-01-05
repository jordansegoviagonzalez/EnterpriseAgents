from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from enterpriseagents.agents.builder import BuilderAgent
from enterpriseagents.agents.director import DirectorAgent
from enterpriseagents.agents.docs import DocsAgent
from enterpriseagents.agents.reviewer import ReviewerAgent
from enterpriseagents.audit.logger import AuditLogger
from enterpriseagents.core.events import Event, EventType
from enterpriseagents.core.kanban import KanbanBoard
from enterpriseagents.core.models import TaskStatus
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
    
    The Run Coordinator serves as the central orchestration engine. It initializes the environment, manages the Kanban state, facilitates communication between agents, and ensures that all events are properly audited and governed by policy.
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
    ) -> None:
        self._run_id = run_id
        self._audit = audit
        self._policy = policy
        self._tools = tools
        self._director = director
        self._builder = builder
        self._reviewer = reviewer
        self._docs = docs

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
        tasks = self._director.plan(req.instruction)
        for ev in board.add_tasks(tasks):
            self._audit.event(ev)

        for t in board.tasks.values():
            self._audit.event(board.move(t.id, TaskStatus.READY))

        while True:
            task = board.next_ready()
            if task is None:
                break

            self._audit.event(
                Event(
                    type=EventType.TASK_STARTED,
                    ts=utc_now_iso(),
                    run_id=self._run_id,
                    payload={"task_id": task.id},
                )
            )
            self._audit.event(board.move(task.id, TaskStatus.DOING))

            tool_calls = self._builder.propose(task=task, workspace=req.workspace)

            for call in tool_calls:
                decision = self._policy.evaluate(call=call, workspace=req.workspace)
                self._audit.approval(decision.to_record(call))
                self._audit.tool_call(call)

                if decision.denied:
                    self._audit.event(
                        Event(
                            type=EventType.CHECK_FAILED,
                            ts=utc_now_iso(),
                            run_id=self._run_id,
                            payload={"task_id": task.id, "reason": f"Policy denied tool call: {call.tool_name}"},
                        )
                    )
                    self._audit.event(board.move(task.id, TaskStatus.BLOCKED))
                    break

                if req.dry_run:
                    self._audit.tool_result(call.call_id, ok=True, output="DRY_RUN: not executed")
                    continue

                result = self._tools.execute(call=call, workspace=req.workspace)
                self._audit.tool_result(result.call_id, ok=result.ok, output=result.output)

                if not result.ok:
                    self._audit.event(
                        Event(
                            type=EventType.CHECK_FAILED,
                            ts=utc_now_iso(),
                            run_id=self._run_id,
                            payload={"task_id": task.id, "reason": "Tool execution failed", "tool": call.tool_name},
                        )
                    )
                    self._audit.event(board.move(task.id, TaskStatus.REVIEW))
                    break

            review = self._reviewer.review(task=task, workspace=req.workspace, dry_run=req.dry_run)
            for ev in review.events:
                # normalize run_id if needed, or ensure Reviewer returns full Event
                ev2 = Event(type=ev.type, ts=ev.ts, run_id=self._run_id, payload=ev.payload)
                self._audit.event(ev2)

            if review.ok:
                self._audit.event(board.move(task.id, TaskStatus.DONE))
                self._audit.event(
                    Event(
                        type=EventType.TASK_DONE,
                        ts=utc_now_iso(),
                        run_id=self._run_id,
                        payload={"task_id": task.id},
                    )
                )
            else:
                self._audit.event(board.move(task.id, TaskStatus.REVIEW))

        docs_calls = self._docs.finalize(workspace=req.workspace, instruction=req.instruction)
        for call in docs_calls:
            decision = self._policy.evaluate(call=call, workspace=req.workspace)
            self._audit.approval(decision.to_record(call))
            self._audit.tool_call(call)
            if req.dry_run:
                self._audit.tool_result(call.call_id, ok=True, output="DRY_RUN: not executed")
                continue
            result = self._tools.execute(call=call, workspace=req.workspace)
            self._audit.tool_result(result.call_id, ok=result.ok, output=result.output)

        self._audit.finish(workspace=req.workspace)
        self._audit.event(
            Event(
                type=EventType.RUN_FINISHED,
                ts=utc_now_iso(),
                run_id=self._run_id,
                payload={"workspace": req.workspace},
            )
        )
