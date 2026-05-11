from datetime import date, datetime
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram import F
from database.plans import get_today_plans
from database.shopping import get_shopping_list
from database.reminders import get_active_reminders
from keyboards.inline import main_menu_kb

router = Router()


async def build_today_text(user_id: int) -> str:
    today_str = date.today().strftime("%d.%m.%Y")
    plans = await get_today_plans(user_id)
    shopping = await get_shopping_list(user_id)
    reminders = await get_active_reminders(user_id)

    lines = [f"📅 <b>Сводка на сегодня ({today_str})</b>\n"]

    # --- Планы ---
    lines.append("─────────────────────")
    lines.append("📋 <b>Планы на день</b>")
    if plans:
        for i, p in enumerate(plans, 1):
            text = p["text"]
            if p["is_important"] and not p["is_done"]:
                text = f"<b><i>{text}</i></b>"
            elif p["is_important"] and p["is_done"]:
                text = f"<s><b>{text}</b></s>"
            elif p["is_done"]:
                text = f"<s>{text}</s>"
            icon = "✅" if p["is_done"] else ("❗" if p["is_important"] else "⬜")
            lines.append(f"  {i}. {icon} {text}")
        done = sum(1 for p in plans if p["is_done"])
        lines.append(f"\n  <i>Выполнено: {done}/{len(plans)}</i>")
    else:
        lines.append("  <i>Пусто — напиши что нужно сделать</i>")

    # --- Покупки ---
    lines.append("")
    lines.append("─────────────────────")
    lines.append("🛒 <b>Список покупок</b>")
    if shopping:
        for i, item in enumerate(shopping, 1):
            text = item["text"]
            if item["is_bought"]:
                lines.append(f"  {i}. ✅ <s>{text}</s>")
            else:
                lines.append(f"  {i}. {text}")
        bought = sum(1 for s in shopping if s["is_bought"])
        lines.append(f"\n  <i>Куплено: {bought}/{len(shopping)}</i>")
    else:
        lines.append("  <i>Пусто — напиши что купить</i>")

    # --- Напоминания ---
    lines.append("")
    lines.append("─────────────────────")
    lines.append("⏰ <b>Напоминания</b>")
    if reminders:
        for r in reminders:
            from config import strip_tz
            dt = strip_tz(r["remind_at"]) if isinstance(r["remind_at"], datetime) else datetime.fromisoformat(str(r["remind_at"]))
            lines.append(f"  🔔 {dt.strftime('%H:%M')} — {r['text']}")
    else:
        lines.append("  <i>Нет активных напоминаний</i>")

    lines.append("─────────────────────")
    return "\n".join(lines)


@router.message(Command("today"))
async def cmd_today(message: Message) -> None:
    text = await build_today_text(message.from_user.id)
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())


@router.callback_query(F.data == "menu:today")
async def today_callback(call: CallbackQuery) -> None:
    text = await build_today_text(call.from_user.id)
    await call.message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())
    await call.answer()
