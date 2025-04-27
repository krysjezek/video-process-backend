import json
import os

CONFIG_ENV = "MOCKUPS_PATH"

def load_mockup_config():
    config_path = os.getenv(CONFIG_ENV)
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), "mockups.json")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at {config_path}")
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in config file: {str(e)}", e.doc, e.pos)
