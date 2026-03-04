import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

def require_env_path(env_name: str) -> Path:
    raw_value = os.getenv(env_name)
    if not raw_value:
        raise RuntimeError(f"Missing required environment variable: {env_name}")
    candidate = Path(raw_value).expanduser()
    return candidate if candidate.is_absolute() else BASE_DIR / candidate

DATA_DIR = require_env_path("DATA_DIR")
SCRAPING_LOG_DIR = require_env_path("SCRAPING_LOG_DIR")
DB_DIR = require_env_path("DB_DIR")
DB_PATH = require_env_path("DB_PATH")
