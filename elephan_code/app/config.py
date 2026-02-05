from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration for constructing the application runtime."""

    api_key: str
    model_id: str
    mode: str = "auto"
    max_steps: int = 10
    provider: str = "openrouter"



def get_openrouter_api_key() -> Optional[str]:
    """Read OpenRouter API key from environment."""
    return os.environ.get("OPENROUTER_API_KEY")
