from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    BACKLOG = "backlog"
    READY = "ready"
    DOING = "doing"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"


class AcceptanceCriteria(BaseModel):
    """Objective requirements that define DONE."""

    checks: list[str] = Field(default_factory=list)


class Task(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.BACKLOG
    acceptance: AcceptanceCriteria = Field(default_factory=AcceptanceCriteria)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    tool_name: str
    args: dict[str, Any]
    call_id: str


class ToolResult(BaseModel):
    call_id: str
    ok: bool
    output: str
    metadata: dict[str, Any] = Field(default_factory=dict)