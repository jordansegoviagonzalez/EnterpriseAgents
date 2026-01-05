from __future__ import annotations

import subprocess
from pathlib import Path

from enterpriseagents.core.models import ToolCall, ToolResult
from enterpriseagents.tools.base import Tool, ToolSpec


class GitCommitTool(Tool):
    spec = ToolSpec(name="git_commit", description="Create a git commit in the workspace (approval-gated).")

    def execute(self, *, call: ToolCall, workspace: str) -> ToolResult:
        msg = str(call.args.get("message", "enterpriseagents: commit"))
        cwd = Path(workspace)
        try:
            subprocess.run(["git", "add", "-A"], cwd=str(cwd), check=False, capture_output=True, text=True)
            proc = subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=str(cwd),
                check=False,
                capture_output=True,
                text=True,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            ok = proc.returncode == 0
            return ToolResult(call_id=call.call_id, ok=ok, output=out, metadata={"returncode": proc.returncode})
        except Exception as e:
            return ToolResult(call_id=call.call_id, ok=False, output=f"git_commit failed: {e}")
