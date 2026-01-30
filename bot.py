import asyncio
import aiosqlite
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import os
from aiogram import Bot

TOKEN = os.getenv("8357406219:AAFI756lzhQnFA3YzuWVClDWDOvlszsoScA")  # <--- must match the variable name exactly
bot = Bot(TOKEN)

ADMINS = {6051335819, 672551095, 8208387660, 6375452214, 8139964977, 5094875024}

dp = Dispatcher()

DB_NAME = "usd_bot.db"


# ---------- DB INIT ----------
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            rate REAL,
            fee REAL
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY,
            total_usd REAL,
            sent_usdt REAL
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            amount REAL,
            time TEXT
        )
        """)
        await db.execute("INSERT OR IGNORE INTO settings VALUES (1, 1, 0)")
        await db.execute("INSERT OR IGNORE INTO stats VALUES (1, 0, 0)")
        await db.commit()


# ---------- ADMIN CHECK ----------
def is_admin(message: types.Message) -> bool:
    return message.from_user.id in ADMINS


# ---------- INLINE MENU ----------
def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Report", callback_data="report"),
            InlineKeyboardButton(text="🔄 Reset", callback_data="reset")
        ],
        [
            InlineKeyboardButton(text="📤 Export CSV", callback_data="export")
        ]
    ])


# ---------- START ----------
@dp.message(Command("start"))
async def start(message: types.Message):
    if not is_admin(message):
        return
    await message.answer(
        "🤖 USD → USDT ბოტი მზადაა",
        reply_markup=main_keyboard()
    )


# ---------- SET RATE ----------
@dp.message(Command("rate"))
async def set_rate(message: types.Message):
    if not is_admin(message):
        return
    try:
        _, rate = message.text.split()
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE settings SET rate = ?", (float(rate),))
            await db.commit()
        await message.reply(f"✅ კურსი დაყენდა: {rate}")
    except:
        await message.reply("გამოყენება: /rate 1.00")


# ---------- SET FEE ----------
@dp.message(F.text.startswith("%"))
async def set_fee(message: types.Message):
    if not is_admin(message):
        return
    try:
        fee = float(message.text.replace("%", ""))
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE settings SET fee = ?", (fee,))
            await db.commit()
        await message.reply(f"✅ საკომისიო: {fee}%")
    except:
        await message.reply("გამოყენება: %5")


# ---------- DEPOSIT ----------
@dp.message(F.text.regexp(r"^\+\d+(\.\d+)?$"))
async def deposit(message: types.Message):
    if not is_admin(message):
        return
    amount = float(message.text.replace("+", ""))
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE stats SET total_usd = total_usd + ?", (amount,)
        )
        await db.execute(
            "INSERT INTO operations (type, amount, time) VALUES (?,?,?)",
            ("deposit", amount, datetime.now().isoformat())
        )
        await db.commit()
    await message.reply(f"✅ ჩარიცხულია {amount} USD")


# ---------- WITHDRAW ----------
@dp.message(F.text.regexp(r"^-\d+(\.\d+)?$"))
async def withdraw(message: types.Message):
    if not is_admin(message):
        return
    amount = float(message.text.replace("-", ""))
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE stats SET sent_usdt = sent_usdt + ?", (amount,)
        )
        await db.execute(
            "INSERT INTO operations (type, amount, time) VALUES (?,?,?)",
            ("withdraw", amount, datetime.now().isoformat())
        )
        await db.commit()
    await message.reply(f"✅ გაცემულია {amount} USDT")


# ---------- REPORT ----------
async def send_report(target):
    async with aiosqlite.connect(DB_NAME) as db:
        rate, fee = await (await db.execute(
            "SELECT rate, fee FROM settings WHERE id = 1"
        )).fetchone()

        total_usd, sent_usdt = await (await db.execute(
            "SELECT total_usd, sent_usdt FROM stats WHERE id = 1"
        )).fetchone()

    if rate == 0:
        if isinstance(target, types.CallbackQuery):
            await target.message.answer("❌ კურსი დაყენებული არ არის")
        else:
            await target.answer("❌ კურსი დაყენებული არ არის")
        return

    gross = total_usd / rate
    fee_amt = gross * (fee / 100)
    net = gross - fee_amt
    remaining = net - sent_usdt

    text = (
        "📊 <b>ფინანსური რეპორტი</b>\n\n"
        f"💵 ჩარიცხული: <b>{total_usd:.2f} USD</b>\n"
        f"📤 გაცემული: <b>{sent_usdt:.2f} USDT</b>\n"
        f"💰 საკომისიო: <b>{fee}%</b>\n"
        f"📈 გასაცემი: <b>{remaining:.2f} USDT</b>"
    )

    if isinstance(target, types.CallbackQuery):
        await target.message.answer(text, parse_mode="HTML")
        await target.answer()  # popup-ის გასაქრობად
    else:
        await target.answer(text, parse_mode="HTML")


@dp.message(Command("report"))
async def report_cmd(message: types.Message):
    if is_admin(message):
        await send_report(message)


@dp.callback_query(F.data == "report")
async def report_cb(call: types.CallbackQuery):
    if call.from_user.id in ADMINS:
        await send_report(call)


# ---------- RESET ----------
@dp.callback_query(F.data == "reset")
async def reset(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        return
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE stats SET total_usd = 0, sent_usdt = 0")
        await db.execute("DELETE FROM operations")
        await db.commit()
    await call.answer("Reset შესრულდა ✅", show_alert=True)


# ---------- EXPORT ----------
@dp.callback_query(F.data == "export")
async def export(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        return

    import csv
    filename = "operations.csv"

    async with aiosqlite.connect(DB_NAME) as db:
        rows = await (await db.execute(
            "SELECT type, amount, time FROM operations"
        )).fetchall()

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["type", "amount", "time"])
        writer.writerows(rows)

    await call.message.answer_document(types.FSInputFile(filename))


# ---------- MAIN ----------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())





