import json
from pathlib import Path

from elephan_code.tui.common import ModelConfig



def test_model_config_loads_custom_file(tmp_path: Path):
    config_file = tmp_path / "models.json"
    config_file.write_text(
        json.dumps(
            {
                "default": "a/b",
                "models": [
                    {"id": "a/b", "name": "AB", "description": "x"},
                    {"id": "c/d", "name": "CD", "description": "y"},
                ],
            }
        ),
        encoding="utf-8",
    )

    cfg = ModelConfig(config_path=config_file)
    assert cfg.get_default() == "a/b"
    assert len(cfg.get_models()) == 2
    assert cfg.get_model_by_index(1)["id"] == "c/d"
