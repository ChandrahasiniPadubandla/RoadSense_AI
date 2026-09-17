import os
from pathlib import Path
from dotenv import load_dotenv

# Load from backend/.env first, then root .env if present
_backend_env = Path(__file__).resolve().parents[2] / ".env"
_root_env = Path(__file__).resolve().parents[3] / ".env"

if _backend_env.exists():
    load_dotenv(_backend_env)
elif _root_env.exists():
    load_dotenv(_root_env)
else:
    load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()

MAX_HISTORY_TURNS = 10
MAX_MESSAGE_LENGTH = 2000


def is_configured() -> bool:
    key = os.getenv("GROQ_API_KEY", GROQ_API_KEY).strip()
    return bool(key)
