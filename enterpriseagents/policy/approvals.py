from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import typer

from enterpriseagents.core.models import ToolCall
from enterpriseagents.policy.policy import PolicyDecision
from enterpriseagents.utils.time import utc_now_iso


@dataclass(frozen=True)
class ApprovalResult:
    approved: bool
    reason: str | None = None

    @property
    def human_decision(self) -> str:
        return "approved" if self.approved else "denied"

    def to_record(self, *, call: ToolCall, policy_decision: PolicyDecision) -> dict[str, object]:
        target_path = call.args.get("path")
        command = call.args.get("command")
        return {
            "ts": utc_now_iso(),
            "timestamp": utc_now_iso(),
            "call_id": call.call_id,
            "tool": call.tool_name,
            "action_type": call.tool_name,
            "command": str(command) if command is not None else None,
            "target_path": str(target_path) if target_path is not None else None,
            "policy_decision": policy_decision.decision_label,
            "human_decision": self.human_decision,
            "reason": self.reason,
        }


class Approver(Protocol):
    def request(self, *, call: ToolCall, policy_decision: PolicyDecision) -> ApprovalResult:
        """Ask for a human or configured approval decision."""


@dataclass(frozen=True)
class DenyByDefaultApprover:
    reason: str = "Non-interactive mode denies approval-required actions by default"

    def request(self, *, call: ToolCall, policy_decision: PolicyDecision) -> ApprovalResult:
        return ApprovalResult(approved=False, reason=self.reason)


@dataclass(frozen=True)
class StaticApprover:
    approved: bool
    reason: str | None = None

    def request(self, *, call: ToolCall, policy_decision: PolicyDecision) -> ApprovalResult:
        return ApprovalResult(approved=self.approved, reason=self.reason)


class CliApprover:
    def request(self, *, call: ToolCall, policy_decision: PolicyDecision) -> ApprovalResult:
        target = call.args.get("command") or call.args.get("path") or call.tool_name
        approved = typer.confirm(
            f"Approve {call.tool_name} action '{target}'? Policy: {policy_decision.reason}",
            default=False,
        )
        reason = "Approved by interactive CLI" if approved else "Denied by interactive CLI"
        return ApprovalResult(approved=approved, reason=reason)
