from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from keyboards.inline import main_menu_kb

router = Router()

WELCOME_TEXT = (
    "👋 Привет! Я твой личный <b>Ежедневник</b>.\n\n"
    "Я помогу тебе:\n"
    "📋 Планировать день\n"
    "🛒 Вести список покупок\n"
    "⏰ Не забывать важное\n"
    "📊 Отслеживать прогресс\n\n"
    "Выбери раздел:"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.callback_query(lambda c: c.data == "menu:main")
async def menu_main_callback(call: CallbackQuery) -> None:
    await call.message.answer(WELCOME_TEXT, reply_markup=main_menu_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("menu:") and c.data != "menu:main")
async def menu_section_callback(call: CallbackQuery) -> None:
    from database.plans import get_today_plans
    from database.shopping import get_shopping_list
    from database.reminders import get_active_reminders
    from database.plans import get_plans_stats
    from database.shopping import get_monthly_bought
    from handlers.plans import _format_plans
    from handlers.shopping import _format_shopping
    from handlers.reminders import _format_reminders
    from keyboards.inline import plans_list_kb, shopping_list_kb, reminders_list_kb
    from datetime import date

    section = call.data.split(":")[1]
    uid = call.from_user.id

    if section == "plans":
        from handlers.plans import _check_and_notify_carryover
        await _check_and_notify_carryover(call.message, uid)
        plans = await get_today_plans(uid)
        await call.message.answer(
            _format_plans(plans),
            reply_markup=plans_list_kb(plans),
            parse_mode="HTML",
        )
    elif section == "shopping":
        items = await get_shopping_list(uid)
        await call.message.answer(
            _format_shopping(items),
            reply_markup=shopping_list_kb(items),
            parse_mode="HTML",
        )
    elif section == "reminders":
        rems = await get_active_reminders(uid)
        await call.message.answer(
            _format_reminders(rems),
            reply_markup=reminders_list_kb(rems),
            parse_mode="HTML",
        )
    elif section == "today":
        from handlers.today import build_today_text
        text = await build_today_text(uid)
        await call.message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())
    elif section == "stats":
        stats = await get_plans_stats(uid)
        bought = await get_monthly_bought(uid)
        today_done, today_total = stats["today"]
        week_done, week_total = stats["week"]
        month_done, month_total = stats["month"]

        def pct(d, t):
            return f"{round(d/t*100)}%" if t else "—"

        month_name = date.today().strftime("%B %Y")
        lines = [
            "📊 <b>Статистика</b>\n",
            "📋 <b>Выполнение планов:</b>",
            f"  Сегодня:  {today_done}/{today_total} ({pct(today_done, today_total)})",
            f"  Неделя:   {week_done}/{week_total} ({pct(week_done, week_total)})",
            f"  Месяц:    {month_done}/{month_total} ({pct(month_done, month_total)})",
        ]
        if today_total > 0 and today_done == today_total:
            lines.append("\n🎉 <b>Все задачи на сегодня выполнены!</b>")
        lines.append(f"\n🛒 <b>Куплено за {month_name}:</b>")
        if bought:
            for row in bought:
                lines.append(f"  • {row['name'].capitalize()} — {row['cnt']} раз(а)")
        else:
            lines.append("  Пока ничего не куплено.")
        await call.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=main_menu_kb())

    await call.answer()
