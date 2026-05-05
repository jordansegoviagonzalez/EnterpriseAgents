from __future__ import annotations

import uuid
from dataclasses import dataclass

from enterpriseagents.core.events import Event, EventType
from enterpriseagents.core.models import Task, ToolCall
from enterpriseagents.tools.registry import ToolRegistry
from enterpriseagents.utils.time import utc_now_iso


@dataclass(frozen=True)
class ReviewResult:
    ok: bool
    events: list[Event]


@dataclass
class ReviewerAgent:
    """Runs deterministic checks defined in acceptance criteria."""

    name: str = "reviewer"
    tools: ToolRegistry | None = None

    def review(self, *, task: Task, workspace: str, dry_run: bool) -> ReviewResult:
        events: list[Event] = []
        if not task.acceptance.checks:
            return ReviewResult(ok=True, events=events)

        if dry_run:
            events.append(
                Event(
                    type=EventType.TOOL_RESULT,
                    ts=utc_now_iso(),
                    run_id="",
                    payload={"task_id": task.id, "note": "DRY_RUN: checks not executed"},
                )
            )
            return ReviewResult(ok=True, events=events)

        if self.tools is None:
            events.append(
                Event(
                    type=EventType.CHECK_FAILED,
                    ts=utc_now_iso(),
                    run_id="",
                    payload={"task_id": task.id, "reason": "Reviewer missing ToolRegistry"},
                )
            )
            return ReviewResult(ok=False, events=events)

        ok_all = True
        for cmd in task.acceptance.checks:
            call = ToolCall(tool_name="run_command", args={"command": cmd}, call_id=str(uuid.uuid4()))
            res = self.tools.execute(call=call, workspace=workspace)
            events.append(
                Event(
                    type=EventType.TOOL_RESULT,
                    ts=utc_now_iso(),
                    run_id="",
                    payload={"task_id": task.id, "cmd": cmd, "ok": res.ok, "output": res.output},
                )
            )
            if not res.ok:
                ok_all = False
                events.append(
                    Event(
                        type=EventType.CHECK_FAILED,
                        ts=utc_now_iso(),
                        run_id="",
                        payload={"task_id": task.id, "reason": f"Check failed: {cmd}"},
                    )
                )
        return ReviewResult(ok=ok_all, events=events)
