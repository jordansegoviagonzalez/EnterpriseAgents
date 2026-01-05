from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from enterpriseagents.core.events import Event, EventType
from enterpriseagents.core.models import Task, TaskStatus
from enterpriseagents.utils.time import utc_now_iso


@dataclass
class KanbanBoard:
    """Small, explicit state machine for tasks.

    WHY it matters:
    - Reduces drift by forcing state transitions.
    - Enables durable runs later (resume by replaying events).
    """

    run_id: str
    tasks: dict[str, Task] = field(default_factory=dict)

    def add_tasks(self, tasks: Iterable[Task]) -> list[Event]:
        events: list[Event] = []
        for t in tasks:
            self.tasks[t.id] = t
            events.append(
                Event(
                    type=EventType.TASK_CREATED,
                    ts=utc_now_iso(),
                    run_id=self.run_id,
                    payload={"task_id": t.id, "title": t.title, "status": t.status.value},
                )
            )
        return events

    def move(self, task_id: str, new_status: TaskStatus) -> Event:
        t = self.tasks[task_id]
        old = t.status
        t.status = new_status
        return Event(
            type=EventType.TASK_MOVED,
            ts=utc_now_iso(),
            run_id=self.run_id,
            payload={"task_id": task_id, "from": old.value, "to": new_status.value},
        )

    def next_ready(self) -> Task | None:
        for t in self.tasks.values():
            if t.status in (TaskStatus.READY, TaskStatus.BACKLOG):
                return t
        return None
