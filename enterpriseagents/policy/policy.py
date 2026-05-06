from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
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

    @property
    def requires_approval(self) -> bool:
        return self.allowed and self.needs_approval

    @property
    def decision_label(self) -> str:
        if not self.allowed:
            return "BLOCK"
        if self.needs_approval:
            return "REQUIRE_APPROVAL"
        return "ALLOW"

    def to_record(self, call: ToolCall) -> dict[str, Any]:
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
            "allowed": self.allowed,
            "decision": self.decision_label,
            "policy_decision": self.decision_label,
            "needs_approval": self.needs_approval,
            "reason": self.reason,
            "args": call.args,
        }


class PolicyEngine:
    """Central policy gate for tool calls."""

    def __init__(self) -> None:
        # Commands that are generally considered safe for automated workflows
        self._shell_allowlist = [
            re.compile(r"^python3?(\s+.*|$)"),
            re.compile(r"^pytest(\s+.*|$)"),
            re.compile(r"^ruff\s+check(\s+.*|$)"),
            re.compile(r"^ls(\s+.*|$)"),
            re.compile(r"^cat(\s+.*|$)"),
        ]
        # Keywords that are strictly forbidden regardless of allowlist
        self._dangerous_keywords = [
            "sudo", "rm -rf", "chmod", "chown", "curl", "wget", "nc", "bash", "sh", "mkfifo"
        ]

    def evaluate(self, *, call: ToolCall, workspace: str) -> PolicyDecision:
        ws_path = Path(workspace).resolve()

        # 1. Workspace Boundary Check for Files
        if call.tool_name in {"write_file", "read_file"}:
            rel_path = str(call.args.get("path", ""))
            try:
                target_path = (ws_path / rel_path).resolve()
                if ws_path not in target_path.parents and target_path != ws_path:
                    return PolicyDecision(allowed=False, needs_approval=False, reason="Path traversal blocked: outside workspace")
                
                # Block sensitive files
                if self._is_sensitive_file(target_path.relative_to(ws_path)):
                    return PolicyDecision(allowed=False, needs_approval=False, reason="Access to sensitive file blocked")
                
            except Exception:
                return PolicyDecision(allowed=False, needs_approval=False, reason="Invalid path structure")

            return PolicyDecision(allowed=True, needs_approval=False, reason="File access within workspace allowed")

        # 2. Command Security Check
        if call.tool_name == "run_command":
            cmd = str(call.args.get("command", "")).strip()
            allow_shell = bool(call.args.get("allow_shell", False))

            # Block dangerous keywords
            for kw in self._dangerous_keywords:
                if kw in cmd:
                    return PolicyDecision(allowed=False, needs_approval=False, reason=f"Dangerous keyword '{kw}' blocked")

            # Check allowlist
            allowed_pattern = any(p.match(cmd) for p in self._shell_allowlist)
            
            if allow_shell:
                return PolicyDecision(allowed=True, needs_approval=True, reason="High-risk shell=True requested (approval mandatory)")

            if not allowed_pattern:
                return PolicyDecision(allowed=False, needs_approval=False, reason="Command not in security allowlist")

            return PolicyDecision(allowed=True, needs_approval=True, reason="Allowlisted command (approval recommended)")

        if call.tool_name == "git_commit":
            return PolicyDecision(allowed=True, needs_approval=True, reason="Commits require approval")

        return PolicyDecision(allowed=False, needs_approval=False, reason="Unknown tool")

    def _is_sensitive_file(self, path: str | Path) -> bool:
        normalized_path = Path(str(path).replace("\\", "/"))
        lowered_parts = [part.lower() for part in normalized_path.parts]
        lowered_path = "/".join(lowered_parts)
        sensitive_terms = [
            "secret",
            "token",
            "key",
            "password",
            "credential",
            "credentials",
            "private",
            ".env",
            ".dev.vars",
            ".git",
            ".ssh",
            "id_rsa",
            "config",
            "history",
        ]
        return any(term in part for part in lowered_parts for term in sensitive_terms) or any(
            term in lowered_path for term in {".env", ".dev.vars"}
        )
