from datetime import datetime, date
import aiosqlite
from config import DB_PATH


async def add_plan(user_id: int, text: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO plans (user_id, text, created_at) VALUES (?, ?, ?)",
            (user_id, text, datetime.now().isoformat()),
        )
        await db.commit()
        return cursor.lastrowid


async def get_today_plans(user_id: int) -> list[dict]:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM plans WHERE user_id = ? AND DATE(created_at) = ? ORDER BY id",
            (user_id, today),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_plan_by_pos(user_id: int, pos: int) -> dict | None:
    plans = await get_today_plans(user_id)
    if 1 <= pos <= len(plans):
        return plans[pos - 1]
    return None


async def set_plan_done(plan_id: int, is_done: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE plans SET is_done = ? WHERE id = ?",
            (1 if is_done else 0, plan_id),
        )
        await db.commit()


async def set_plan_important(plan_id: int, is_important: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE plans SET is_important = ? WHERE id = ?",
            (1 if is_important else 0, plan_id),
        )
        await db.commit()


async def delete_plan(plan_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
        await db.commit()


async def get_plans_stats(user_id: int) -> dict:
    today = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async def fetch(where: str, params: tuple) -> tuple[int, int]:
            cur = await db.execute(
                f"SELECT COUNT(*) as total, SUM(is_done) as done FROM plans WHERE user_id = ? AND {where}",
                (user_id, *params),
            )
            row = await cur.fetchone()
            total = row["total"] or 0
            done = int(row["done"] or 0)
            return total, done

        today_total, today_done = await fetch("DATE(created_at) = ?", (today.isoformat(),))

        week_start = today.strftime("%Y-%m-%d")
        cur_week = await db.execute(
            "SELECT COUNT(*) as total, SUM(is_done) as done FROM plans "
            "WHERE user_id = ? AND DATE(created_at) >= DATE(?, '-6 days')",
            (user_id, week_start),
        )
        row = await cur_week.fetchone()
        week_total, week_done = row["total"] or 0, int(row["done"] or 0)

        month_str = today.strftime("%Y-%m")
        cur_month = await db.execute(
            "SELECT COUNT(*) as total, SUM(is_done) as done FROM plans "
            "WHERE user_id = ? AND strftime('%Y-%m', created_at) = ?",
            (user_id, month_str),
        )
        row = await cur_month.fetchone()
        month_total, month_done = row["total"] or 0, int(row["done"] or 0)

    return {
        "today": (today_done, today_total),
        "week": (week_done, week_total),
        "month": (month_done, month_total),
    }
