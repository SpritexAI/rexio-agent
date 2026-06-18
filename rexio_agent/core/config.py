import os
from dotenv import load_dotenv

# Standard directory for RexiO Agent configurations in user's home
GLOBAL_REXIO_DIR = os.path.expanduser("~/.rexio")
ENV_PATH = os.path.join(GLOBAL_REXIO_DIR, ".env")
DB_DIR = GLOBAL_REXIO_DIR
DB_PATH = os.path.join(DB_DIR, "rexio_agent.db")

def load_environment() -> None:
    """Ensures the global config directory exists and loads environment variables."""
    os.makedirs(GLOBAL_REXIO_DIR, exist_ok=True)
    if os.path.exists(ENV_PATH):
        load_dotenv(dotenv_path=ENV_PATH, override=True)
