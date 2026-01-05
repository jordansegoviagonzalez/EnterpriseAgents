from __future__ import annotations

import subprocess
from pathlib import Path

from enterpriseagents.core.models import ToolCall, ToolResult
from enterpriseagents.tools.base import Tool, ToolSpec


class ShellTool(Tool):
    spec = ToolSpec(name="run_command", description="Run a shell command inside the workspace (approval-gated).")

    def execute(self, *, call: ToolCall, workspace: str) -> ToolResult:
        command = str(call.args.get("command", ""))
        cwd = Path(workspace)

        try:
            args = command.split()
            proc = subprocess.run(
                args,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            ok = proc.returncode == 0
            return ToolResult(call_id=call.call_id, ok=ok, output=out, metadata={"returncode": proc.returncode})
        except Exception as e:  # noqa: BLE001
            return ToolResult(call_id=call.call_id, ok=False, output=f"run_command failed: {e}")
