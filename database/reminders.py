from datetime import datetime
import aiosqlite
from config import DB_PATH


async def add_reminder(user_id: int, text: str, remind_at: datetime) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO reminders (user_id, text, remind_at) VALUES (?, ?, ?)",
            (user_id, text, remind_at.isoformat()),
        )
        await db.commit()
        return cursor.lastrowid


async def get_active_reminders(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM reminders WHERE user_id = ? AND is_sent = 0 ORDER BY remind_at",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_all_pending_reminders() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM reminders WHERE is_sent = 0 ORDER BY remind_at",
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def mark_reminder_sent(reminder_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE reminders SET is_sent = 1 WHERE id = ?",
            (reminder_id,),
        )
        await db.commit()


async def delete_reminder(reminder_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        await db.commit()


async def get_reminder_by_pos(user_id: int, pos: int) -> dict | None:
    reminders = await get_active_reminders(user_id)
    if 1 <= pos <= len(reminders):
        return reminders[pos - 1]
    return None
