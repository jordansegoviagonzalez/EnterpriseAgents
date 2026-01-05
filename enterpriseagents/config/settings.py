from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from env vars.

    WHAT:
    - Centralizes configuration for providers and filesystem outputs.

    WHY it matters:
    - Enterprises rotate/centralize secrets and endpoints.
    - Keeps providers swappable without code edits.
    """

    model_config = SettingsConfigDict(env_prefix="EA_", extra="ignore")

    openai_base_url: str | None = None
    openai_api_key: str | None = None

    deepseek_base_url: str | None = None
    deepseek_api_key: str | None = None

    ollama_base_url: str = "http://localhost:11434"

    runs_dir: str = "runs"
