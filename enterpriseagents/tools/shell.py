import shlex
import subprocess
from pathlib import Path

from enterpriseagents.core.models import ToolCall, ToolResult
from enterpriseagents.tools.base import Tool, ToolSpec


class ShellTool(Tool):
    spec = ToolSpec(name="run_command", description="Run a shell command inside the workspace (approval-gated).")

    def execute(self, *, call: ToolCall, workspace: str) -> ToolResult:
        command = str(call.args.get("command", ""))
        allow_shell = bool(call.args.get("allow_shell", False))
        cwd = Path(workspace)

        try:
            if allow_shell:
                # High-risk execution path: uses the shell
                proc = subprocess.run(
                    command,
                    cwd=str(cwd),
                    capture_output=True,
                    text=True,
                    timeout=600,
                    check=False,
                    shell=True,
                )
            else:
                # Secure execution path: no shell
                args = shlex.split(command)
                proc = subprocess.run(
                    args,
                    cwd=str(cwd),
                    capture_output=True,
                    text=True,
                    timeout=600,
                    check=False,
                    shell=False,
                )
            
            out = (proc.stdout or "") + (proc.stderr or "")
            ok = proc.returncode == 0
            return ToolResult(call_id=call.call_id, ok=ok, output=out, metadata={"returncode": proc.returncode, "shell": allow_shell})
        except Exception as e:
            return ToolResult(call_id=call.call_id, ok=False, output=f"run_command failed: {e}")
