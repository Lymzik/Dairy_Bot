from datetime import datetime
from database.db import get_pool


async def add_reminder(user_id: int, text: str, remind_at: datetime) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO reminders (user_id, text, remind_at) VALUES ($1, $2, $3) RETURNING id",
            user_id, text, remind_at,
        )
        return row["id"]


async def get_active_reminders(user_id: int) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM reminders WHERE user_id = $1 AND is_sent = 0 ORDER BY remind_at",
            user_id,
        )
        return [dict(r) for r in rows]


async def get_all_pending_reminders() -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM reminders WHERE is_sent = 0 ORDER BY remind_at",
        )
        return [dict(r) for r in rows]


async def mark_reminder_sent(reminder_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE reminders SET is_sent = 1 WHERE id = $1", reminder_id,
        )


async def delete_reminder(reminder_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM reminders WHERE id = $1", reminder_id)


async def get_reminder_by_pos(user_id: int, pos: int) -> dict | None:
    reminders = await get_active_reminders(user_id)
    if 1 <= pos <= len(reminders):
        return reminders[pos - 1]
    return None
