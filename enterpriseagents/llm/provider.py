from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LlmProvider(ABC):
    """Abstract interface for Language Model interactions.

    This base class defines a vendor-neutral contract that allows the system to communicate with various model providers. By abstracting the specific implementation details of services like OpenAI or local models, the core application logic remains decoupled from the underlying intelligence engine.
    """

    @abstractmethod
    def completion(self, messages: list[dict[str, str]], model: str | None = None) -> str:
        """Executes a standard chat completion request.

        This method accepts a history of conversation messages and returns the model's textual response as a string. It serves as the primary mechanism for unstructured interactions.
        """
        ...

    @abstractmethod
    def structured(self, messages: list[dict[str, str]], schema: type[Any], model: str | None = None) -> Any:
        """Executes a completion request that enforces a specific output schema.

        This method guarantees that the returned data conforms strictly to the provided Pydantic model. This structural validation is essential for reliable agent-to-system communication, eliminating the need for complex output parsing.
        """
        ...
