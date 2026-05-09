from datetime import datetime, date
import aiosqlite
from config import DB_PATH


async def add_item(user_id: int, text: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO shopping (user_id, text, created_at) VALUES (?, ?, ?)",
            (user_id, text, datetime.now().isoformat()),
        )
        await db.commit()
        return cursor.lastrowid


async def get_shopping_list(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM shopping WHERE user_id = ? ORDER BY id",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_item_by_pos(user_id: int, pos: int) -> dict | None:
    items = await get_shopping_list(user_id)
    if 1 <= pos <= len(items):
        return items[pos - 1]
    return None


async def mark_bought(item_id: int, is_bought: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        bought_at = datetime.now().isoformat() if is_bought else None
        await db.execute(
            "UPDATE shopping SET is_bought = ?, bought_at = ? WHERE id = ?",
            (1 if is_bought else 0, bought_at, item_id),
        )
        await db.commit()


async def edit_item(item_id: int, new_text: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE shopping SET text = ? WHERE id = ?",
            (new_text, item_id),
        )
        await db.commit()


async def delete_item(item_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM shopping WHERE id = ?", (item_id,))
        await db.commit()


async def clear_bought(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM shopping WHERE user_id = ? AND is_bought = 1",
            (user_id,),
        )
        await db.commit()
        return cursor.rowcount


async def get_monthly_bought(user_id: int) -> list[dict]:
    month_str = date.today().strftime("%Y-%m")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT LOWER(text) as name, COUNT(*) as cnt
            FROM shopping
            WHERE user_id = ?
              AND is_bought = 1
              AND strftime('%Y-%m', bought_at) = ?
            GROUP BY LOWER(text)
            ORDER BY cnt DESC, name
            """,
            (user_id, month_str),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
