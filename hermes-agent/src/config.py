import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_ALLOWED_USER_IDS = {
    int(uid.strip())
    for uid in os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "").split(",")
    if uid.strip()
}

TIMEZONE = os.environ.get("TIMEZONE", "Asia/Seoul")
DB_PATH = os.environ.get("DB_PATH", "./data/memory.db")
SKILLS_DIR = os.environ.get("SKILLS_DIR", "./skills")
