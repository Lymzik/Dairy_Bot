import os
from pathlib import Path

# Загружаем .env только при локальной разработке (файл существует)
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path, override=False)

BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан. На Railway: добавь в Variables. Локально: создай .env файл.")

DB_PATH: str = os.environ.get("DB_PATH", "diary.db")
