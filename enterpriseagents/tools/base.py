from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from enterpriseagents.core.models import ToolCall, ToolResult


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str


class Tool(ABC):
    spec: ToolSpec

    @abstractmethod
    def execute(self, *, call: ToolCall, workspace: str) -> ToolResult:
        raise NotImplementedError
