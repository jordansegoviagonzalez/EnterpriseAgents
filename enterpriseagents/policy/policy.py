from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from enterpriseagents.core.models import ToolCall
from enterpriseagents.utils.time import utc_now_iso


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    needs_approval: bool
    reason: str

    @property
    def denied(self) -> bool:
        return not self.allowed

    def to_record(self, call: ToolCall) -> dict[str, Any]:
        return {
            "ts": utc_now_iso(),
            "call_id": call.call_id,
            "tool": call.tool_name,
            "allowed": self.allowed,
            "needs_approval": self.needs_approval,
            "reason": self.reason,
        }


class PolicyEngine:
    """Central policy gate for tool calls."""

    def __init__(self) -> None:
        self._shell_allowlist = [
            re.compile(r"^python\s+-m\s+pytest(\s|$)"),
            re.compile(r"^ruff\s+check(\s|$)"),
            re.compile(r"^python\s+-m\s+pip\s+install(\s|$)"),
            re.compile(r"^git\s+(status|diff|log)(\s|$)"),
        ]

    def evaluate(self, *, call: ToolCall, workspace: str) -> PolicyDecision:
        _ = workspace
        if call.tool_name in {"write_file", "read_file"}:
            needs = self._is_protected_path(str(call.args.get("path", "")))
            return PolicyDecision(allowed=True, needs_approval=needs, reason="File access allowed")

        if call.tool_name == "run_command":
            cmd = str(call.args.get("command", "")).strip()
            allowed = any(p.match(cmd) for p in self._shell_allowlist)
            if not allowed:
                return PolicyDecision(allowed=False, needs_approval=False, reason="Command not in allowlist")
            return PolicyDecision(allowed=True, needs_approval=True, reason="Allowlisted command (approval required)")

        if call.tool_name == "git_commit":
            return PolicyDecision(allowed=True, needs_approval=True, reason="Commits require approval")

        return PolicyDecision(allowed=False, needs_approval=False, reason="Unknown tool")

    def _is_protected_path(self, path: str) -> bool:
        lowered = path.replace("\\", "/").lower()
        return lowered.startswith(".github/") or lowered.endswith("pyproject.toml")
