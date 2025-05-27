import os
import json
import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from fastapi import Request

# === Настройка путей и файлов ===
BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data.json"
# Путь к статике — тут же project_root/static
DISK_PATH = BASE_DIR / "static"

# === Telegram Bot ===
# Подставьте свой реальный токен или заведите .env и читайте его через os.getenv
BOT_TOKEN = os.getenv("BOT_TOKEN", "7833095864:AAH4lvPpyP9ptiPxYutNKXPaOIUnlh-c3ac")
bot = Bot(token=BOT_TOKEN)
# Используем in‑memory storage, можно подключить Redis или файл
dp = Dispatcher(bot, storage=MemoryStorage())

# === Функции для работы с данными ===
def load_data() -> dict:
    """Загрузить весь словарь из data.json (или пустой, если файла нет)."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data: dict) -> None:
    """Сохранить словарь в data.json."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def ensure_user(data: dict, user_id: str, username: str | None = None) -> dict:
    """
    Убедиться, что в data['users'][user_id] есть запись.
    Если нет — создать с начальными значениями.
    """
    users = data.setdefault("users", {})
    if user_id not in users:
        users[user_id] = {
            "username": username or "",
            "balance": 0,
            # можно сразу добавить другие поля,
            # например "tokens": [], "referrer": None и т.д.
        }
    return users[user_id]

# === Декораторы для защиты команд ===
def require_login(handler):
    """
    Aiogram‑декоратор: перед выполнением команды
    гарантированно создаст пользователя в data.json.
    """
    async def wrapper(message):
        data = load_data()
        user_id = str(message.from_user.id)
        ensure_user(data, user_id, message.from_user.username)
        save_data(data)
        return await handler(message)
    return wrapper

def require_web_login(request: Request) -> str | None:
    """
    FastAPI‑зависимость: проверяет, что кука user_id
    есть в data.json → возвращает user_id или None.
    Можно расширить: проверять флаг logged_in.
    """
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    data = load_data()
    if user_id in data.get("users", {}):
        return user_id
    return None
