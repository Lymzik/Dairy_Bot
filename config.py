import os
from datetime import datetime


def now() -> datetime:
    """Текущее время без timezone — совместимо с PostgreSQL TIMESTAMPTZ после strip."""
    return datetime.now()


def strip_tz(dt: datetime) -> datetime:
    """Убирает timezone info из datetime полученного из PostgreSQL."""
    return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt


try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не задан.\n"
        "На Railway: добавь переменную BOT_TOKEN в разделе Variables.\n"
        "Локально: создай файл .env с BOT_TOKEN=твой_токен"
    )

DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL не задан.\n"
        "На Railway: переменная добавляется автоматически при подключении PostgreSQL.\n"
        "Локально: добавь DATABASE_URL=postgresql://... в .env"
    )
