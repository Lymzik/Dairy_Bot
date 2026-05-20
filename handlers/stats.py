from datetime import date
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from database.plans import get_plans_stats
from database.shopping import get_monthly_bought, get_shopping_stats

router = Router()


def _pct(done: int, total: int) -> str:
    if total == 0:
        return "—"
    p = round(done / total * 100)
    return f"{p}%"


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    uid = message.from_user.id
    stats = await get_plans_stats(uid)
    shop_stats = await get_shopping_stats(uid)
    bought = await get_monthly_bought(uid)

    today_done, today_total = stats["today"]
    week_done, week_total = stats["week"]
    month_done, month_total = stats["month"]

    month_name = date.today().strftime("%B %Y")

    lines = [
        "📊 <b>Статистика</b>\n",
        "📋 <b>Выполнение планов:</b>",
        f"  Сегодня:  {today_done}/{today_total} ({_pct(today_done, today_total)})",
        f"  Неделя:   {week_done}/{week_total} ({_pct(week_done, week_total)})",
        f"  Месяц:    {month_done}/{month_total} ({_pct(month_done, month_total)})",
    ]

    if today_total > 0 and today_done == today_total:
        lines.append("\n🎉 <b>Все задачи на сегодня выполнены! Отличная работа!</b>")

    lines.append(f"\n🛒 <b>Покупки:</b>")
    lines.append(f"  Сегодня куплено:  {shop_stats['today']} поз.")
    lines.append(f"  За неделю:        {shop_stats['week']} поз.")
    lines.append(f"  За месяц:         {shop_stats['month']} поз.")

    lines.append(f"\n📦 <b>Что покупали в {month_name}:</b>")
    if bought:
        for row in bought:
            lines.append(f"  • {row['name'].capitalize()} — {row['cnt']} раз(а)")
    else:
        lines.append("  Пока ничего не куплено.")

    await message.answer("\n".join(lines), parse_mode="HTML")
