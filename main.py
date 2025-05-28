import asyncio
import os

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from uvicorn import run as uv_run

from aiogram import Dispatcher, types
from aiogram.client.bot import DefaultBotProperties
from aiogram import Bot
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram import types


# — CONFIGURATION —
BOT_TOKEN = "7707637937:AAGiteK3cHH6CXxpzkYvkzvIibRA131BUPs"

# — FASTAPI SETUP —
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/webapp")
async def webapp(request: Request, tg_id: int):
    """
    Отдаёт страницу дизайна WebApp (пока без логики).
    Параметр tg_id нам пригодится позже в JS.
    """
    return templates.TemplateResponse("index.html", {
        "request": request,
        "tg_id": tg_id
    })

# — AIORGRAM BOT SETUP —
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton(
            text="Открыть стейкинг",
            web_app=WebAppInfo(url=f"http://localhost:8000/webapp?tg_id={msg.from_user.id}")
        )
    )
    await msg.answer(
        "Нажми кнопку, чтобы открыть дизайн‑версию нашего стейкинг‑приложения.",
        reply_markup=kb
    )

async def main():
    # запускаем параллельно FastAPI (uvicorn) и бота (polling)
    api_task = asyncio.create_task(
        uv_run(app, host="0.0.0.0", port=8000, reload=True)
    )
    bot_task = asyncio.create_task(dp.start_polling(bot))
    await asyncio.gather(api_task, bot_task)

if __name__ == "__main__":
    asyncio.run(main())
