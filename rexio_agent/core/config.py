import os
import json
from typing import Dict, Any

# Standard directory for RexiO Agent configurations in user's home
GLOBAL_REXIO_DIR = os.path.expanduser("~/.rexio")
CONFIG_PATH = os.path.join(GLOBAL_REXIO_DIR, "config.json")
DB_DIR = GLOBAL_REXIO_DIR
DB_PATH = os.path.join(DB_DIR, "rexio_agent.db")

def load_environment() -> None:
    """Ensures the global config directory exists and loads config parameters into os.environ."""
    os.makedirs(GLOBAL_REXIO_DIR, exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                if isinstance(config_data, dict):
                    for key, val in config_data.items():
                        if val is not None:
                            os.environ[key] = str(val)
        except Exception:
            pass # Fail-safe

def save_config(config_data: Dict[str, Any]) -> None:
    """Saves configuration data globally as a JSON file."""
    os.makedirs(GLOBAL_REXIO_DIR, exist_ok=True)
    try:
        # Load existing config to merge it
        existing_data = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        
        # Merge changes
        existing_data.update(config_data)
        
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4)
            
        # Update current process environment
        for key, val in config_data.items():
            if val is not None:
                os.environ[key] = str(val)
    except Exception:
        pass
