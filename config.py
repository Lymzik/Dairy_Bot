import os

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

import os as _os
_data_dir = "/data" if _os.path.isdir("/data") else "."
DB_PATH: str = os.environ.get("DB_PATH", f"{_data_dir}/diary.db")
