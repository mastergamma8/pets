import datetime
import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# --- Подключаем общие функции/переменные из вашего common.py ---
from common import (
    load_data, save_data,
    ensure_user, require_login, require_web_login,
    bot as telegram_bot, dp as telegram_dp,
    DATA_FILE, DISK_PATH
)

# --- Telegram‑бот: команды покупки и ухода за питомцем ---

@telegram_dp.message(Command("buy_pet"))
@require_login
async def cmd_buy_pet(message: Message):
    data = load_data()
    catalog = data.get("pets_catalog", {})
    kb = InlineKeyboardMarkup(row_width=2)
    for key, pet in catalog.items():
        kb.insert(InlineKeyboardButton(
            text=f"{pet['name']} — {pet['price']} 💎",
            callback_data=f"buy_pet:{key}"
        ))
    await message.answer("Выберите питомца для покупки:", reply_markup=kb)

@telegram_dp.callback_query(lambda c: c.data and c.data.startswith("buy_pet:"))
async def cb_buy_pet(callback: CallbackQuery):
    _, pet_type = callback.data.split(":", 1)
    user_id = str(callback.from_user.id)
    data = load_data()
    user = data["users"][user_id]
    pet = data["pets_catalog"].get(pet_type)
    if not pet:
        await callback.answer("❗ Питомец не найден", show_alert=True); return
    if user.get("balance", 0) < pet["price"]:
        await callback.answer("Недостаточно 💎", show_alert=True); return

    user["balance"] -= pet["price"]
    data.setdefault("user_pets", {})[user_id] = {
        "type": pet_type,
        "hunger": 100,
        "happiness": 100,
        "last_care": datetime.datetime.now().isoformat()
    }
    save_data(data)
    await callback.answer(f"Вы купили {pet['name']}! 🎉")
    await callback.message.edit_reply_markup()

@telegram_dp.message(Command("pet"))
@require_login
async def cmd_show_pet(message: Message):
    user_id = str(message.from_user.id)
    data = load_data()
    up = data.get("user_pets", {}).get(user_id)
    if not up:
        await message.answer("У вас пока нет питомца. Купите его в /buy_pet"); return

    pet_info = data["pets_catalog"][up["type"]]
    text = (
        f"🐾 <b>Ваш питомец:</b> {pet_info['name']}\n"
        f"🍗 Голод: {up['hunger']}%\n"
        f"😊 Настроение: {up['happiness']}%"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Покормить 🍖", callback_data="care:feed")],
        [InlineKeyboardButton("Поиграть 🎾", callback_data="care:play")]
    ])
    await message.answer_animation(
        animation=FSInputFile(DISK_PATH / pet_info["animation"]),
        caption=text,
        parse_mode="HTML",
        reply_markup=kb
    )

@telegram_dp.callback_query(lambda c: c.data and c.data.startswith("care:"))
async def cb_care(callback: CallbackQuery):
    action = callback.data.split(":",1)[1]
    user_id = str(callback.from_user.id)
    data = load_data()
    up = data.setdefault("user_pets", {}).get(user_id)
    if not up:
        await callback.answer("У вас нет питомца", show_alert=True); return

    if action == "feed":
        up["hunger"] = min(100, up["hunger"] + 20)
        msg = "Вы покормили питомца! 🍖"
    else:
        up["happiness"] = min(100, up["happiness"] + 20)
        msg = "Вы поиграли с питомцем! 🎾"

    up["last_care"] = datetime.datetime.now().isoformat()
    save_data(data)
    await callback.answer(msg)
    await cmd_show_pet(callback.message)

# --- FastAPI: каталог питомцев и покупка через веб ---

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/pets", response_class=HTMLResponse)
async def pets_catalog(request: Request):
    user_id = request.cookies.get("user_id")
    data = load_data()
    catalog = data.get("pets_catalog", {})
    balance = None
    if user_id and data["users"].get(user_id):
        balance = data["users"][user_id].get("balance", 0)
    return templates.TemplateResponse("pets_catalog.html", {
        "request": request,
        "catalog": catalog,
        "balance": balance,
        "user_id": user_id
    })

@app.post("/pets/buy")
async def buy_pet_web(request: Request, pet_type: str = Form(...)):
    user_id = request.cookies.get("user_id")
    if not user_id or not require_web_login(request):
        return RedirectResponse("/pets", status_code=303)
    data = load_data()
    user = data["users"][user_id]
    pet = data.get("pets_catalog", {}).get(pet_type)
    if not pet:
        return HTMLResponse("❗ Питомец не найден", status_code=404)
    if user.get("balance", 0) < pet["price"]:
        return RedirectResponse("/pets?error=Недостаточно+средств", status_code=303)

    user["balance"] -= pet["price"]
    data.setdefault("user_pets", {})[user_id] = {
        "type": pet_type,
        "hunger": 100,
        "happiness": 100,
        "last_care": datetime.datetime.now().isoformat()
    }
    save_data(data)
    return RedirectResponse("/pets", status_code=303)

# --- Запуск Web + Bot ---

async def main():
    bot_task = asyncio.create_task(telegram_dp.start_polling(telegram_bot))
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    web_task = asyncio.create_task(server.serve())
    await asyncio.gather(bot_task, web_task)

if __name__ == "__main__":
    asyncio.run(main())
