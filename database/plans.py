from datetime import datetime, date, timedelta
from database.db import get_pool


async def add_plan(user_id: int, text: str, for_date: date | None = None) -> int:
    pool = await get_pool()
    created_at = datetime.combine(for_date, datetime.min.time()) if for_date else datetime.now()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO plans (user_id, text, created_at) VALUES ($1, $2, $3) RETURNING id",
            user_id, text, created_at,
        )
        return row["id"]


async def get_today_plans(user_id: int) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM plans WHERE user_id = $1 AND created_at::date = CURRENT_DATE ORDER BY id",
            user_id,
        )
        return [dict(r) for r in rows]


async def get_yesterday_undone(user_id: int) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM plans WHERE user_id = $1 AND created_at::date = CURRENT_DATE - 1 "
            "AND is_done = 0 AND carried_over = 0 ORDER BY id",
            user_id,
        )
        return [dict(r) for r in rows]


async def carry_over_plans(user_id: int, plan_ids: list[int]) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        for plan_id in plan_ids:
            row = await conn.fetchrow(
                "SELECT text, is_important FROM plans WHERE id = $1", plan_id
            )
            if row:
                await conn.execute(
                    "INSERT INTO plans (user_id, text, is_important, created_at) VALUES ($1, $2, $3, $4)",
                    user_id, row["text"], row["is_important"], datetime.now(),
                )
            await conn.execute(
                "UPDATE plans SET carried_over = 1 WHERE id = $1", plan_id
            )


async def dismiss_carryover(plan_ids: list[int]) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE plans SET carried_over = 1 WHERE id = ANY($1::int[])", plan_ids
        )


async def get_plan_by_pos(user_id: int, pos: int) -> dict | None:
    plans = await get_today_plans(user_id)
    if 1 <= pos <= len(plans):
        return plans[pos - 1]
    return None


async def set_plan_done(plan_id: int, is_done: bool) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE plans SET is_done = $1 WHERE id = $2",
            1 if is_done else 0, plan_id,
        )


async def set_plan_important(plan_id: int, is_important: bool) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE plans SET is_important = $1 WHERE id = $2",
            1 if is_important else 0, plan_id,
        )


async def delete_plan(plan_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM plans WHERE id = $1", plan_id)


async def get_plans_stats(user_id: int) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        today_row = await conn.fetchrow(
            "SELECT COUNT(*) AS total, SUM(is_done) AS done FROM plans "
            "WHERE user_id = $1 AND created_at::date = CURRENT_DATE",
            user_id,
        )
        week_row = await conn.fetchrow(
            "SELECT COUNT(*) AS total, SUM(is_done) AS done FROM plans "
            "WHERE user_id = $1 AND created_at::date >= CURRENT_DATE - 6",
            user_id,
        )
        month_row = await conn.fetchrow(
            "SELECT COUNT(*) AS total, SUM(is_done) AS done FROM plans "
            "WHERE user_id = $1 AND to_char(created_at, 'YYYY-MM') = to_char(NOW(), 'YYYY-MM')",
            user_id,
        )

    def parse(row) -> tuple[int, int]:
        return int(row["done"] or 0), int(row["total"] or 0)

    return {
        "today": parse(today_row),
        "week": parse(week_row),
        "month": parse(month_row),
    }
