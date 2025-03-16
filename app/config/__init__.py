import json
import os

def load_mockup_config():
    config_path = os.path.join(os.path.dirname(__file__), "mockups.json")
    with open(config_path, "r") as f:
        config = json.load(f)
    return config
