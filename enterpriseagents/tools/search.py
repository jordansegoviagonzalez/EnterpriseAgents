from __future__ import annotations

import os
from dataclasses import dataclass

from enterpriseagents.core.models import ToolCall, ToolResult
from enterpriseagents.tools.base import Tool, ToolSpec


@dataclass
class WebSearchTool(Tool):
    """Provides capability to query external search engines.
    
    This tool allows agents to retrieve real-time information from the web,
    enabling 'Deep Research' workflows where documentation or solutions
    must be discovered rather than hallucinated.
    """

    spec = ToolSpec(
        name="web_search",
        description="Search the internet for technical documentation or solutions."
    )

    def execute(self, *, call: ToolCall, workspace: str) -> ToolResult:
        query = str(call.args.get("query", ""))
        
        # In a real enterprise deployment, we would connect this to a paid API
        # like Tavily, Brave, or Bing. For this reference implementation,
        # we check for an environment variable or return a placeholder.
        
        api_key = os.environ.get("EA_SEARCH_API_KEY")
        if not api_key:
            return ToolResult(
                call_id=call.call_id,
                ok=False,
                output="Search is disabled. Please set EA_SEARCH_API_KEY."
            )

        # Mock implementation for the 'concept' - real implementation would use requests
        return ToolResult(
            call_id=call.call_id,
            ok=True,
            output=f"[Mock Search Result] Found documentation for: {query}"
        )
