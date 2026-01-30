import asyncio
import aiosqlite
from datetime import datetime
import re

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================

TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"

ADMINS = {
    6051335819,
    672551095,
    8208387660,
    6375452214,
    8139964977
}

DB_NAME = "usd_bot.db"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================= DB INIT =================

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

# ================= HELPERS =================

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


def keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Report", callback_data="report"),
            InlineKeyboardButton(text="🔄 Reset", callback_data="reset")
        ]
    ])

# ================= START =================

@dp.message(Command("start"))
async def start(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🤖 Bot ready", reply_markup=keyboard())

# ================= REPORT =================

async def send_report(target):
    async with aiosqlite.connect(DB_NAME) as db:
        rate, fee = await (await db.execute(
            "SELECT rate, fee FROM settings WHERE id=1"
        )).fetchone()

        total_usd, sent_usdt = await (await db.execute(
            "SELECT total_usd, sent_usdt FROM stats WHERE id=1"
        )).fetchone()

    gross = total_usd / rate if rate else 0
    fee_amt = gross * fee / 100
    net = gross - fee_amt
    remaining = net - sent_usdt

    text = (
        "📊 <b>REPORT</b>\n\n"
        f"💵 Deposited: <b>{total_usd:.2f} USD</b>\n"
        f"📤 Sent: <b>{sent_usdt:.2f} USDT</b>\n"
        f"💰 Fee: <b>{fee}%</b>\n"
        f"📈 Remaining: <b>{remaining:.2f} USDT</b>"
    )

    if isinstance(target, types.CallbackQuery):
        await target.message.answer(text, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(text, parse_mode="HTML")


@dp.message(Command("report"))
async def report_cmd(message: types.Message):
    if is_admin(message.from_user.id):
        await send_report(message)


@dp.callback_query(F.data == "report")
async def report_cb(call: types.CallbackQuery):
    if is_admin(call.from_user.id):
        await send_report(call)

# ================= RESET =================

@dp.callback_query(F.data == "reset")
async def reset(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE stats SET total_usd=0, sent_usdt=0")
        await db.execute("DELETE FROM operations")
        await db.commit()

    await call.answer("Reset done ✅", show_alert=True)

# ================= MAIN LOGIC (+ / -) =================

@dp.message(F.text)
async def handle_amount(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    text = message.text.lower().strip()

    # match +100 / + 100 usd / -50 usdt
    match = re.match(r"^([+-])\s*(\d+(\.\d+)?)(\s*(usd|usdt))?$", text)
    if not match:
        return

    sign = match.group(1)
    amount = float(match.group(2))

    async with aiosqlite.connect(DB_NAME) as db:
        if sign == "+":
            await db.execute(
                "UPDATE stats SET total_usd = total_usd + ?", (amount,)
            )
            op_type = "deposit"
            reply = f"✅ Deposited {amount} USD"
        else:
            await db.execute(
                "UPDATE stats SET sent_usdt = sent_usdt + ?", (amount,)
            )
            op_type = "withdraw"
            reply = f"✅ Sent {amount} USDT"

        await db.execute(
            "INSERT INTO operations (type, amount, time) VALUES (?,?,?)",
            (op_type, amount, datetime.now().isoformat())
        )
        await db.commit()

    await message.reply(reply)

# ================= RUN =================

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
