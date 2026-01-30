import asyncio
import aiosqlite
from datetime import datetime
import re

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ================= CONFIG =================

TOKEN = "8357406219:AAFI756lzhQnFA3YzuWVClDWDOvlszsoScA"

ADMINS = {
    6051335819,
    672551095,
    8208387660,
    6375452214,
    8139964977
}

DB_NAME = "calculator.db"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================= DATABASE =================

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY,
            total_usd REAL,
            sent_usdt REAL
        )
        """)
        await db.execute(
            "INSERT OR IGNORE INTO stats VALUES (1, 0, 0)"
        )
        await db.commit()

# ================= START =================

@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id not in ADMINS:
        return
    await message.answer(
        "✅ Calculator ready\n\n"
        "Use:\n"
        "+100\n"
        "-50\n"
        "/report"
    )

# ================= REPORT =================

@dp.message(Command("report"))
async def report(message: types.Message):
    if message.from_user.id not in ADMINS:
        return

    async with aiosqlite.connect(DB_NAME) as db:
        total_usd, sent_usdt = await (
            await db.execute(
                "SELECT total_usd, sent_usdt FROM stats WHERE id=1"
            )
        ).fetchone()

    remaining = total_usd - sent_usdt

    await message.answer(
        f"📊 REPORT\n\n"
        f"💵 Received: {total_usd:.2f} USD\n"
        f"📤 Sent: {sent_usdt:.2f} USDT\n"
        f"📈 Remaining: {remaining:.2f} USDT"
    )

# ================= CALCULATOR =================

@dp.message()
async def calculator(message: types.Message):
    if message.from_user.id not in ADMINS:
        return

    text = message.text.lower().strip()

    match = re.match(r"^([+-])\s*(\d+(\.\d+)?)$", text)
    if not match:
        return

    sign = match.group(1)
    amount = float(match.group(2))

    async with aiosqlite.connect(DB_NAME) as db:
        if sign == "+":
            await db.execute(
                "UPDATE stats SET total_usd = total_usd + ?",
                (amount,)
            )
            reply = f"✅ Added {amount} USD"
        else:
            await db.execute(
                "UPDATE stats SET sent_usdt = sent_usdt + ?",
                (amount,)
            )
            reply = f"✅ Subtracted {amount} USDT"

        await db.commit()

    await message.answer(reply)

# ================= RUN =================

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
