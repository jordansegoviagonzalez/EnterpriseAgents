from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from enterpriseagents.core.kanban import KanbanBoard
from enterpriseagents.llm.provider import LlmProvider


class NextAction(str, Enum):
    PLAN = "plan"
    WORK = "work"
    REVIEW = "review"
    FINISH = "finish"


class RoutingDecision(BaseModel):
    """Represents the strategic decision for the next workflow phase."""
    action: NextAction
    reason: str
    target_task_id: str | None = None


class DynamicRouter:
    """Intelligent orchestration engine for workflow navigation.

    This class analyzes the current state of the Kanban board and employs the
    language model to determine the most effective next action. This replaces
    static looping with adaptive decision-making.
    """

    def __init__(self, llm: LlmProvider) -> None:
        self.llm = llm

    def decide(self, board: KanbanBoard) -> RoutingDecision:
        """Evaluates the board state to produce a routing decision."""
        
        # We summarize the board state for the LLM
        # This keeps the context small while providing necessary info
        summary = {
            "backlog": [t.title for t in board.tasks.values() if t.status == "backlog"],
            "ready": [t.title for t in board.tasks.values() if t.status == "ready"],
            "doing": [t.title for t in board.tasks.values() if t.status == "doing"],
            "review": [t.title for t in board.tasks.values() if t.status == "review"],
            "done": [t.title for t in board.tasks.values() if t.status == "done"],
            "blocked": [t.title for t in board.tasks.values() if t.status == "blocked"],
        }

        system_prompt = (
            "You are the Workflow Manager for an autonomous engineering team.\n"
            "Analyze the Kanban board state and decide the next phase.\n"
            "Rules:\n"
            "1. If Backlog has items but Ready is empty -> PLAN.\n"
            "2. If Ready has items -> WORK.\n"
            "3. If Review has items -> REVIEW.\n"
            "4. If Blocked has items -> PLAN (to unblock).\n"
            "5. If all tasks are Done -> FINISH.\n"
            "Choose the most critical action."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Current State: {summary}"},
        ]

        return self.llm.structured(messages=messages, schema=RoutingDecision)
