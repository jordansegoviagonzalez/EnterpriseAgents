from __future__ import annotations

import uuid
from dataclasses import dataclass

from pydantic import BaseModel

from enterpriseagents.core.models import Task, ToolCall
from enterpriseagents.llm.provider import LlmProvider


class BuilderOutput(BaseModel):
    """Encapsulates the list of proposed tool executions."""
    calls: list[ToolCall]


@dataclass
class BuilderAgent:
    """Proposes concrete technical actions to fulfill assigned tasks.

    The Builder Agent acts as the primary engineering entity within the workflow. It analyzes the current task and workspace context to formulate a sequence of tool executions, such as file manipulations or shell commands, which are then submitted for policy review.
    """

    llm: LlmProvider
    name: str = "builder"

    def propose(self, *, task: Task, workspace: str) -> list[ToolCall]:
        """Determines the next set of actions required to advance the task.

        This method consults the language model to generate a step-by-step implementation plan. The resulting plan is returned as a list of structured tool calls ready for execution.
        """
        
        # I'm giving the LLM the context of the current task and the workspace path.
        # In a real enterprise app, I'd also list the current files in the workspace here.
        system_prompt = (
            "You are a Senior Software Engineer.\n"
            "Your goal is to complete the assigned task by proposing concrete tool actions.\n"
            "You have access to: write_file, read_file, run_command.\n"
            f"The workspace is at: {workspace}\n"
            "Think step-by-step, then return a list of tool calls."
        )

        user_prompt = (
            f"Task Title: {task.title}\n"
            f"Description: {task.description}\n"
            "Propose the necessary actions."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Get structured actions
        output = self.llm.structured(messages=messages, schema=BuilderOutput)
        
        # Sanitize IDs
        final_calls = []
        for call in output.calls:
            if not call.call_id:
                call.call_id = str(uuid.uuid4())
            final_calls.append(call)

        return final_calls