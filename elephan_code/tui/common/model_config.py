from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


class ModelConfig:
    """Model configuration manager shared by TUI implementations."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (
            Path(__file__).resolve().parent.parent.parent / "config" / "models.json"
        )
        self._config: Dict = {}
        self._load_config()

    def _load_config(self):
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        else:
            self._config = {
                "default": "anthropic/claude-3.5-sonnet",
                "models": [
                    {
                        "id": "anthropic/claude-3.5-sonnet",
                        "name": "Claude 3.5 Sonnet",
                        "description": "Default model",
                    }
                ],
            }

    def get_models(self) -> List[Dict]:
        return self._config.get("models", [])

    def get_default(self) -> str:
        return self._config.get("default", "anthropic/claude-3.5-sonnet")

    def get_model_by_index(self, index: int) -> Optional[Dict]:
        models = self.get_models()
        if 0 <= index < len(models):
            return models[index]
        return None
