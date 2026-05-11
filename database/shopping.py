from datetime import datetime, date
from database.db import get_pool


async def add_item(user_id: int, text: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO shopping (user_id, text, created_at) VALUES ($1, $2, $3) RETURNING id",
            user_id, text, datetime.now(),
        )
        return row["id"]


async def get_shopping_list(user_id: int) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM shopping WHERE user_id = $1 AND deleted_at IS NULL ORDER BY id",
            user_id,
        )
        return [dict(r) for r in rows]


async def get_item_by_pos(user_id: int, pos: int) -> dict | None:
    items = await get_shopping_list(user_id)
    if 1 <= pos <= len(items):
        return items[pos - 1]
    return None


async def mark_bought(item_id: int, is_bought: bool) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        bought_at = datetime.now() if is_bought else None
        await conn.execute(
            "UPDATE shopping SET is_bought = $1, bought_at = $2 WHERE id = $3",
            1 if is_bought else 0, bought_at, item_id,
        )


async def edit_item(item_id: int, new_text: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE shopping SET text = $1 WHERE id = $2",
            new_text, item_id,
        )


async def soft_delete_item(item_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE shopping SET deleted_at = NOW() WHERE id = $1", item_id
        )


async def restore_item(item_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE shopping SET deleted_at = NULL WHERE id = $1", item_id
        )


async def delete_item(item_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM shopping WHERE id = $1", item_id)


async def clear_bought(user_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM shopping WHERE user_id = $1 AND is_bought = 1",
            user_id,
        )
        return int(result.split()[-1])


async def get_monthly_bought(user_id: int) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT LOWER(text) AS name, COUNT(*) AS cnt
            FROM shopping
            WHERE user_id = $1
              AND is_bought = 1
              AND to_char(bought_at, 'YYYY-MM') = to_char(NOW(), 'YYYY-MM')
            GROUP BY LOWER(text)
            ORDER BY cnt DESC, name
            """,
            user_id,
        )
        return [dict(r) for r in rows]
