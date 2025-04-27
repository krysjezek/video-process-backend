import json
import os
import tempfile
import pytest
from app.config import load_mockup_config

CONFIG_ENV = "MOCKUPS_PATH"

def test_load_valid_config(tmp_path, monkeypatch):
    # create a fake mockup.json
    data = {
        "mockup1": {  # Match the actual template ID from the config
            "scenes": [
                {
                    "scene_id": "scene1",
                    "default_effects_chain": [
                        {"effect": "corner_pin", "params": {"use_mask": True}},
                        {"effect": "reflections", "params": {"opacity": 0.5}}
                    ]
                }
            ]
        }
    }
    cfg_file = tmp_path / "mockups.json"
    cfg_file.write_text(json.dumps(data))
    monkeypatch.setenv(CONFIG_ENV, str(cfg_file))
    cfg = load_mockup_config()
    assert "mockup1" in cfg
    assert len(cfg["mockup1"]["scenes"]) == 1

def test_missing_config_raises(tmp_path, monkeypatch):
    # point at a non-existent file
    monkeypatch.setenv(CONFIG_ENV, str(tmp_path / "nope.json"))
    with pytest.raises(FileNotFoundError):
        load_mockup_config()

def test_malformed_json(tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_text("{ this is not json }")
    monkeypatch.setenv(CONFIG_ENV, str(bad))
    with pytest.raises(json.JSONDecodeError):
        load_mockup_config()
