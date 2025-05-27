import os
import json
from pathlib import Path
import datetime

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import Request

# === Пути и файлы ===
BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data.json"
DISK_PATH = BASE_DIR / "static"

# === Telegram Bot ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВАШ_TELEGRAM_BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === Работа с данными ===
def load_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def ensure_user(data: dict, user_id: str, username: str | None = None) -> dict:
    users = data.setdefault("users", {})
    if user_id not in users:
        users[user_id] = {
            "username": username or "",
            "balance": 0
        }
    return users[user_id]

# === Декоратор для бота ===
def require_login(handler):
    async def wrapper(message):
        data = load_data()
        user_id = str(message.from_user.id)
        ensure_user(data, user_id, message.from_user.username)
        save_data(data)
        return await handler(message)
    return wrapper

# === Зависимость для FastAPI ===
def require_web_login(request: Request) -> str | None:
    user_id = request.cookies.get("user_id")
    if not user_id: 
        return None
    data = load_data()
    if user_id in data.get("users", {}):
        return user_id
    return None
