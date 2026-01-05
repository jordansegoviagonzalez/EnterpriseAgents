from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI
from pydantic import BaseModel

from enterpriseagents.llm.provider import LlmProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LlmProvider):
    """The standard adapter for OpenAI-compatible APIs.

    I'm using this for:
    1. OpenAI (GPT-4o)
    2. DeepSeek (via their compatible API)
    3. Ollama (running locally on localhost:11434)

    This prevents us from writing 3 separate clients.
    """

    def __init__(self, api_key: str, base_url: str | None = None, default_model: str = "gpt-4o") -> None:
        # If I don't have an API key (like for local Ollama), I'll just use a dummy
        # string because the client SDK validates presence, but local servers might ignore it.
        key = api_key or "sk-dummy-key-for-local-usage"
        
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.default_model = default_model

    def completion(self, messages: list[dict[str, str]], model: str | None = None) -> str:
        """Standard chat completion."""
        target_model = model or self.default_model
        
        # I'm wrapping this in a try/except because network flakes happen,
        # and I want to see exactly what failed in the logs.
        try:
            response = self.client.chat.completions.create(
                model=target_model,
                messages=messages,  # type: ignore
                temperature=0.0,    # deterministic is better for agents
            )
            content = response.choices[0].message.content
            return content or ""
        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            raise

    def structured(self, messages: list[dict[str, str]], schema: type[BaseModel], model: str | None = None) -> Any:
        """Force the model to output strict JSON validating against 'schema'."""
        target_model = model or self.default_model

        try:
            # This is the modern way to get JSON. 
            # It uses the provider's native 'response_format' if available.
            completion = self.client.beta.chat.completions.parse(
                model=target_model,
                messages=messages, # type: ignore
                response_format=schema,
            )
            parsed = completion.choices[0].message.parsed
            
            if parsed is None:
                # If the model refused to output JSON (rare with .parse), we fail hard.
                # In an enterprise context, a distinct failure is better than a hallucination.
                raise ValueError("Model refused to produce structured output.")
                
            return parsed
        except Exception as e:
            logger.error(f"LLM structured parse failed: {e}")
            raise
