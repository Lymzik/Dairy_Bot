from datetime import datetime, date
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from database import reminders as db
from keyboards.inline import reminders_list_kb

router = Router()


def _parse_remind_at(arg: str) -> datetime | None:
    now = datetime.now()
    for fmt in ("%H:%M", "%d.%m %H:%M", "%d.%m.%Y %H:%M"):
        try:
            dt = datetime.strptime(arg, fmt)
            if fmt == "%H:%M":
                dt = dt.replace(year=now.year, month=now.month, day=now.day)
            elif fmt == "%d.%m %H:%M":
                dt = dt.replace(year=now.year)
            return dt
        except ValueError:
            continue
    return None


def _format_reminders(reminders: list[dict]) -> str:
    if not reminders:
        return "⏰ Активных напоминаний нет.\nДобавь: /remind 14:30 позвонить маме"
    lines = ["⏰ <b>Активные напоминания:</b>\n"]
    for i, r in enumerate(reminders, 1):
        dt = datetime.fromisoformat(r["remind_at"])
        lines.append(f"{i}. 🔔 {dt.strftime('%d.%m.%Y %H:%M')} — {r['text']}")
    return "\n".join(lines)


@router.message(Command("reminders"))
async def cmd_reminders(message: Message) -> None:
    rems = await db.get_active_reminders(message.from_user.id)
    await message.answer(_format_reminders(rems), reply_markup=reminders_list_kb(rems), parse_mode="HTML")


@router.message(Command("remind"))
async def cmd_remind(message: Message) -> None:
    args = message.text.partition(" ")[2].strip()
    if not args:
        await message.answer(
            "❗ Формат:\n"
            "/remind <i>ЧЧ:ММ текст</i> — сегодня\n"
            "/remind <i>ДД.ММ ЧЧ:ММ текст</i> — конкретная дата",
            parse_mode="HTML",
        )
        return

    parts = args.split(maxsplit=1)
    time_part = parts[0]
    text_part = parts[1] if len(parts) > 1 else ""

    # Попробуем формат "ДД.ММ ЧЧ:ММ текст"
    if len(parts) >= 2 and ":" in parts[1].split()[0]:
        time_part = parts[0] + " " + parts[1].split()[0]
        text_part = " ".join(parts[1].split()[1:])

    remind_at = _parse_remind_at(time_part)

    if remind_at is None:
        await message.answer(
            "❗ Не удалось разобрать время.\n"
            "Форматы: <code>14:30</code> или <code>15.05 14:30</code>",
            parse_mode="HTML",
        )
        return

    if not text_part:
        await message.answer("❗ Укажи текст напоминания.")
        return

    if remind_at <= datetime.now():
        await message.answer("❗ Время напоминания уже прошло. Укажи будущее время.")
        return

    from scheduler import schedule_reminder
    reminder_id = await db.add_reminder(message.from_user.id, text_part, remind_at)
    await schedule_reminder(reminder_id, message.from_user.id, text_part, remind_at)

    await message.answer(
        f"⏰ Напоминание установлено!\n"
        f"🔔 <b>{remind_at.strftime('%d.%m.%Y в %H:%M')}</b>\n"
        f"📝 {text_part}",
        parse_mode="HTML",
    )


@router.message(Command("delremind"))
async def cmd_delremind(message: Message) -> None:
    args = message.text.partition(" ")[2].strip()
    if not args.isdigit():
        await message.answer("❗ Укажи номер напоминания: /delremind 1")
        return
    reminder = await db.get_reminder_by_pos(message.from_user.id, int(args))
    if reminder is None:
        await message.answer("❗ Напоминание с таким номером не найдено.")
        return

    from scheduler import cancel_reminder
    await db.delete_reminder(reminder["id"])
    cancel_reminder(reminder["id"])

    rems = await db.get_active_reminders(message.from_user.id)
    await message.answer(
        f"🗑 Напоминание #{args} удалено.\n\n{_format_reminders(rems)}",
        reply_markup=reminders_list_kb(rems),
        parse_mode="HTML",
    )


# --- Inline callback handlers ---

@router.callback_query(F.data.startswith("remind:"))
async def remind_callback(call: CallbackQuery) -> None:
    parts = call.data.split(":")
    action = parts[1]

    if action == "refresh":
        rems = await db.get_active_reminders(call.from_user.id)
        await call.message.edit_text(
            _format_reminders(rems),
            reply_markup=reminders_list_kb(rems),
            parse_mode="HTML",
        )
        await call.answer("Обновлено")
        return

    if action == "del":
        reminder_id = int(parts[2])
        from scheduler import cancel_reminder
        await db.delete_reminder(reminder_id)
        cancel_reminder(reminder_id)

        rems = await db.get_active_reminders(call.from_user.id)
        await call.message.edit_text(
            _format_reminders(rems),
            reply_markup=reminders_list_kb(rems),
            parse_mode="HTML",
        )
        await call.answer("Удалено")
