from typing import Any

import pytest

from enterpriseagents.agents.builder import BuilderOutput
from enterpriseagents.agents.director import Plan
from enterpriseagents.agents.docs import DocsOutput
from enterpriseagents.core.models import AcceptanceCriteria, Task, ToolCall
from enterpriseagents.core.router import NextAction, RoutingDecision
from enterpriseagents.llm.provider import LlmProvider


class MockLlmProvider(LlmProvider):
    """A fake brain for testing."""
    
    def __init__(self):
        self._router_calls = 0

    def completion(self, messages: list[dict[str, str]], model: str | None = None) -> str:
        return "Mock completion"

    def structured(self, messages: list[dict[str, str]], schema: type[Any], model: str | None = None) -> Any:
        # Return valid objects based on what schema was requested
        
        if schema == Plan:
            return Plan(tasks=[
                Task(
                    id="t1", 
                    title="Mock Task 1", 
                    description="Do something", 
                    acceptance=AcceptanceCriteria(checks=[])
                ),
            ])
            
        if schema == BuilderOutput:
            return BuilderOutput(calls=[
                ToolCall(tool_name="write_file", args={"path": "mock.txt", "content": "hi"}, call_id="c1")
            ])
            
        if schema == DocsOutput:
            return DocsOutput(content="# Mock README")
            
        if schema == RoutingDecision:
            self._router_calls += 1
            if self._router_calls == 1:
                return RoutingDecision(action=NextAction.WORK, reason="Let's work")
            if self._router_calls == 2:
                return RoutingDecision(action=NextAction.REVIEW, reason="Let's review")
            return RoutingDecision(action=NextAction.FINISH, reason="Done")
            
        raise ValueError(f"Mock doesn't know how to fake {schema}")

@pytest.fixture
def mock_llm():
    return MockLlmProvider()
