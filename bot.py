
import asyncio
import aiosqlite
from datetime import datetime
import re

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

TOKEN = "8357406219:AAFI756lzhQnFA3YzuWVClDWDOvlszsoScA"
ADMIN_ID = 6051335819,
    672551095,
    8208387660,
    6375452214,
    8139964977

DB_NAME = "calculator.db"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ---------- DB ----------
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY,
            total REAL,
            sent REAL
        )
        """)
        await db.execute(
            "INSERT OR IGNORE INTO stats VALUES (1, 0, 0)"
        )
        await db.commit()

# ---------- START ----------
@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "✅ Calculator ready\n"
        "Commands:\n"
        "+100\n"
        "-50\n"
        "/report"
    )

# ---------- REPORT ----------
@dp.message(Command("report"))
async def report(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect(DB_NAME) as db:
        total, sent = await (
            await db.execute(
                "SELECT total, sent FROM stats WHERE id=1"
            )
        ).fetchone()

    await message.answer(
        f"📊 REPORT\n\n"
        f"Received: {total}\n"
        f"Sent: {sent}\n"
        f"Remaining: {total - sent}"
    )

# ---------- CALCULATOR ----------
@dp.message()
async def calc(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    text = message.text.strip()
    m = re.match(r"^([+-])\s*(\d+(\.\d+)?)$", text)
    if not m:
        return

    sign = m.group(1)
    amount = float(m.group(2))

    async with aiosqlite.connect(DB_NAME) as db:
        if sign == "+":
            await db.execute(
                "UPDATE stats SET total = total + ?", (amount,)
            )
            reply = f"➕ Added {amount}"
        else:
            await db.execute(
                "UPDATE stats SET sent = sent + ?", (amount,)
            )
            reply = f"➖ Subtracted {amount}"

        await db.commit()

    await message.answer(reply)

# ---------- RUN ----------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
