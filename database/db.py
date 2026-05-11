import asyncpg
from config import DATABASE_URL

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    return _pool


async def create_tables() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                text TEXT NOT NULL,
                is_done INTEGER DEFAULT 0,
                is_important INTEGER DEFAULT 0,
                carried_over INTEGER DEFAULT 0,
                deleted_at TIMESTAMPTZ DEFAULT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS shopping (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                text TEXT NOT NULL,
                is_bought INTEGER DEFAULT 0,
                bought_at TIMESTAMPTZ,
                deleted_at TIMESTAMPTZ DEFAULT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                text TEXT NOT NULL,
                remind_at TIMESTAMPTZ NOT NULL,
                is_sent INTEGER DEFAULT 0
            )
        """)
        # Миграции для существующих таблиц
        for col_sql in [
            "ALTER TABLE plans ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL",
            "ALTER TABLE shopping ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL",
        ]:
            try:
                await conn.execute(col_sql)
            except Exception:
                pass
