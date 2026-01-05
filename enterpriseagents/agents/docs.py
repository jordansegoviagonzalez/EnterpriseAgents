from __future__ import annotations

import uuid
from dataclasses import dataclass

from pydantic import BaseModel

from enterpriseagents.core.models import ToolCall
from enterpriseagents.llm.provider import LlmProvider


class DocsOutput(BaseModel):
    """Structured output for documentation."""
    content: str


@dataclass
class DocsAgent:
    """Final documentation pass for the workspace."""

    llm: LlmProvider
    name: str = "docs"

    def finalize(self, *, workspace: str, instruction: str) -> list[ToolCall]:
        """Ask the LLM to write a README based on the instruction."""
        
        system_prompt = (
            "You are a Technical Writer.\n"
            "Write a professional README.md for the generated project.\n"
            "Include: Purpose, Installation, Running, Testing.\n"
            "Keep it concise and formatted in Markdown."
        )

        user_prompt = (
            f"Project Instruction: {instruction}\n"
            f"Workspace Path: {workspace}\n"
            "Write the README content."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        # Get structured content to avoid Markdown block markers in the raw string
        out = self.llm.structured(messages=messages, schema=DocsOutput)
        
        return [
            ToolCall(
                tool_name="write_file", 
                args={"path": "README.md", "content": out.content}, 
                call_id=str(uuid.uuid4())
            )
        ]