import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан. Создайте файл .env и укажите BOT_TOKEN=...")

DB_PATH: str = os.getenv("DB_PATH", "diary.db")
