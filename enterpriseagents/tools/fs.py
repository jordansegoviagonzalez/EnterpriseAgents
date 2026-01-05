from __future__ import annotations

from pathlib import Path

from enterpriseagents.core.models import ToolCall, ToolResult
from enterpriseagents.tools.base import Tool, ToolSpec


class FileSystemTool(Tool):
    spec = ToolSpec(name="write_file", description="Create or update a file in the workspace (text).")

    def execute(self, *, call: ToolCall, workspace: str) -> ToolResult:
        try:
            rel = str(call.args["path"])
            content = str(call.args["content"])
            root = Path(workspace)
            path = (root / rel).resolve()

            if root.resolve() not in path.parents and path != root.resolve():
                return ToolResult(call_id=call.call_id, ok=False, output="Path traversal blocked")

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return ToolResult(call_id=call.call_id, ok=True, output=f"Wrote {rel}")
        except Exception as e:  # noqa: BLE001
            return ToolResult(call_id=call.call_id, ok=False, output=f"write_file failed: {e}")


class ReadFileTool(Tool):
    spec = ToolSpec(name="read_file", description="Read a text file from the workspace.")

    def execute(self, *, call: ToolCall, workspace: str) -> ToolResult:
        try:
            rel = str(call.args["path"])
            root = Path(workspace)
            path = (root / rel).resolve()

            if root.resolve() not in path.parents and path != root.resolve():
                return ToolResult(call_id=call.call_id, ok=False, output="Path traversal blocked")

            content = path.read_text(encoding="utf-8")
            return ToolResult(call_id=call.call_id, ok=True, output=content, metadata={"path": rel})
        except Exception as e:  # noqa: BLE001
            return ToolResult(call_id=call.call_id, ok=False, output=f"read_file failed: {e}")
