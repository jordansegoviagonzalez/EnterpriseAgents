from __future__ import annotations

from dataclasses import dataclass

from enterpriseagents.core.models import ToolCall, ToolResult
from enterpriseagents.tools.base import Tool
from enterpriseagents.tools.fs import FileSystemTool, ReadFileTool
from enterpriseagents.tools.git import GitCommitTool
from enterpriseagents.tools.shell import ShellTool


@dataclass
class ToolRegistry:
    """Maps tool names to implementations."""

    _tools: dict[str, Tool]

    @classmethod
    def default(cls) -> "ToolRegistry":
        tools = [FileSystemTool(), ReadFileTool(), ShellTool(), GitCommitTool()]
        return cls(_tools={t.spec.name: t for t in tools})

    def execute(self, *, call: ToolCall, workspace: str) -> ToolResult:
        tool = self._tools.get(call.tool_name)
        if tool is None:
            return ToolResult(call_id=call.call_id, ok=False, output=f"Unknown tool: {call.tool_name}")
        return tool.execute(call=call, workspace=workspace)
