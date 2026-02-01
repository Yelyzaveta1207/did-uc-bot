import os
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

BOT_TOKEN = "8522618996:AAG6J0isHcmTLYk-IbpRzwx7lnd9YDhLdJg"         # токен будет в Render
PAYMENT_LINK = os.getenv("PAYMENT_LINK", "")   # ссылка на оплату (mono)
PAYMENT_TEXT = os.getenv("PAYMENT_TEXT", "")   # реквизиты текстом (если нужно)
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))     # твой Telegram ID (для уведомлений)


DATA_FILE = "data.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# UC пакеты и цены
UC_PRICES = {
    660: 400,
    1800: 1000,
    3850: 1950,
    8100: 3900,
    16200: 7700,
    32400: 15400
}

# Реквизиты (каждая строка с \n !)
if not PAYMENT_TEXT:
    PAYMENT_TEXT = "💳 Реквизиты: напиши администратору"

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

# Главное меню
menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(KeyboardButton("🛒 Купить UC"))
menu.add(KeyboardButton("🎮 Мой PUBG ID"))
menu.add(KeyboardButton("📌 История"))

# Кнопки UC пакетов
uc_kb = InlineKeyboardMarkup(row_width=2)
for uc, price in UC_PRICES.items():
    uc_kb.insert(
        InlineKeyboardButton(
            text=f"💎 {uc} UC — {price} грн",
            callback_data=f"uc:{uc}"
        )
    )

# Кнопки статуса (добавим реквизиты)
def status_kb(order_id):
    kb = InlineKeyboardMarkup(row_width=1)

    if PAYMENT_LINK:
        kb.add(InlineKeyboardButton("💳 Оплатить", url=PAYMENT_LINK))

    kb.add(InlineKeyboardButton("📋 Скопировать реквизиты", callback_data="payinfo"))

    kb.add(
        InlineKeyboardButton("✅ Оплатил", callback_data=f"paid:{order_id}"),
        InlineKeyboardButton("❌ Отменить", callback_data=f"cancel:{order_id}")
    )
    return kb

@dp.callback_query_handler(lambda c: c.data == "payinfo")
async def payinfo(callback: types.CallbackQuery):
    await callback.message.answer(PAYMENT_TEXT)
    await callback.answer()

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "🎮 DID UC Shop\n\n"
        "Выбирай пакет UC с ценами 👇\n"
        "Бот сохраняет историю и статусы.\n\n"
        "⚠️ UC покупаются только официально.",
        reply_markup=menu
    )

@dp.message_handler(lambda m: m.text == "🛒 Купить UC")
async def buy_uc(message: types.Message):
    await message.answer("Выбери пакет UC:", reply_markup=uc_kb)

@dp.callback_query_handler(lambda c: c.data.startswith("uc:"))
async def uc_selected(callback: types.CallbackQuery):
    uc = int(callback.data.split(":")[1])
    price = UC_PRICES[uc]
    uid = str(callback.from_user.id)

    data = load_data()
    data.setdefault(uid, {})
    data[uid].setdefault("orders", [])

    order_id = len(data[uid]["orders"]) + 1

    data[uid]["orders"].append({
        "id": order_id,
        "time": now(),
        "uc": uc,
        "price": price,
        "status": "ожидает оплаты"
    })
    save_data(data)

    pubg_id = data[uid].get("pubg_id", "не задан")

    await callback.message.answer(
        f"🧾 Заказ #{order_id}\n\n"
        f"💎 UC: {uc}\n"
        f"💰 Цена: {price} грн\n"
        f"🎮 PUBG ID: {pubg_id}\n"
        f"📌 Статус: ожидает оплаты\n\n"
        "Нажми «📋 Скопировать реквизиты», затем после оплаты — «✅ Оплатил».",
        reply_markup=status_kb(order_id)
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("paid:"))
async def paid(callback: types.CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    uid = str(callback.from_user.id)
    data = load_data()

    for o in data.get(uid, {}).get("orders", []):
        if o["id"] == order_id:
            o["status"] = "оплачено"
            save_data(data)
            await callback.message.answer(f"✅ Заказ #{order_id} отмечен как ОПЛАЧЕН")
            break
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("cancel:"))
async def cancel(callback: types.CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    uid = str(callback.from_user.id)
    data = load_data()

    for o in data.get(uid, {}).get("orders", []):
        if o["id"] == order_id:
            o["status"] = "отменён"
            save_data(data)
            await callback.message.answer(f"❌ Заказ #{order_id} отменён")
            break
    await callback.answer()

@dp.message_handler(lambda m: m.text == "🎮 Мой PUBG ID")
async def my_id(message: types.Message):
    data = load_data()
    uid = str(message.from_user.id)
    pid = data.get(uid, {}).get("pubg_id")
    if pid:
        await message.answer(f"Твой PUBG ID: {pid}\nИзменить: /setid 123456789")
    else:
        await message.answer("PUBG ID не задан.\n/setid 123456789")

@dp.message_handler(commands=["setid"])
async def setid(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Формат: /setid 123456789")
        return
    uid = str(message.from_user.id)
    data = load_data()
    data.setdefault(uid, {})
    data[uid]["pubg_id"] = parts[1]
    save_data(data)
    await message.answer("✅ PUBG ID сохранён")

@dp.message_handler(lambda m: m.text == "📌 История")
async def history(message: types.Message):
    data = load_data()
    uid = str(message.from_user.id)
    orders = data.get(uid, {}).get("orders", [])

    if not orders:
        await message.answer("История пуста.")
        return

    text = ["📌 История заказов:"]
    for o in orders[-10:]:
        text.append(f"#{o['id']} | {o['uc']} UC | {o['price']} грн | {o['status']}")
    await message.answer("\n".join(text))

if __name__ == "__main__":
    executorx.start_polling(dp, skip_updates=True)
import os
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

def run_web():
    port = int(os.environ.get("PORT", "10000"))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

Thread(target=run_web, daemon=True).start()
