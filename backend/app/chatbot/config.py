import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()


MAX_HISTORY_TURNS = 10

MAX_MESSAGE_LENGTH = 2000


def is_configured() -> bool:
    return bool(GROQ_API_KEY)
