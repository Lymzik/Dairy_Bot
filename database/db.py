import aiosqlite
from config import DB_PATH


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def create_tables() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                is_done INTEGER DEFAULT 0,
                is_important INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shopping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                is_bought INTEGER DEFAULT 0,
                bought_at TEXT,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                is_sent INTEGER DEFAULT 0
            )
        """)
        await db.commit()
