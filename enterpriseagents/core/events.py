from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class EventType(StrEnum):
    RUN_STARTED = "RUN_STARTED"
    TASK_CREATED = "TASK_CREATED"
    TASK_STARTED = "TASK_STARTED"
    TASK_MOVED = "TASK_MOVED"
    TOOL_CALLED = "TOOL_CALLED"
    TOOL_RESULT = "TOOL_RESULT"
    CHECK_FAILED = "CHECK_FAILED"
    TASK_DONE = "TASK_DONE"
    RUN_FINISHED = "RUN_FINISHED"


class Event(BaseModel):
    type: EventType
    ts: str
    run_id: str
    payload: dict[str, Any]
