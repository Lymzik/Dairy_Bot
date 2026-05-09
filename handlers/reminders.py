from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from database import reminders as db
from keyboards.inline import reminders_list_kb, main_menu_kb

router = Router()


class ReminderForm(StatesGroup):
    waiting_for_new = State()
    waiting_for_edit_time = State()
    waiting_for_edit_text = State()


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
        return (
            "⏰ <b>Напоминания</b>\n\n"
            "Активных напоминаний нет.\n\n"
            "Нажми <b>➕ Добавить напоминание</b> или используй команду:\n"
            "/remind 14:30 позвонить маме"
        )
    lines = ["⏰ <b>Напоминания:</b>\n"]
    for i, r in enumerate(reminders, 1):
        dt = datetime.fromisoformat(r["remind_at"])
        lines.append(f"• 🔔 <b>{dt.strftime('%d.%m.%Y в %H:%M')}</b> — {r['text']}")
    return "\n".join(lines)


async def _show_reminders(target, uid: int, edit: bool = False) -> None:
    rems = await db.get_active_reminders(uid)
    text = _format_reminders(rems)
    kb = reminders_list_kb(rems)
    if edit:
        await target.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("reminders"))
async def cmd_reminders(message: Message) -> None:
    await _show_reminders(message, message.from_user.id)


# --- Добавление через команду ---

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
        f"✅ Напоминание установлено!\n"
        f"🔔 <b>{remind_at.strftime('%d.%m.%Y в %H:%M')}</b>\n"
        f"📝 {text_part}",
        parse_mode="HTML",
    )
    await _show_reminders(message, message.from_user.id)


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
    await _show_reminders(message, message.from_user.id)


# --- FSM: добавление через кнопку ---

@router.callback_query(F.data == "remind:add")
async def remind_add_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ReminderForm.waiting_for_new)
    await call.message.answer(
        "⏰ Введи напоминание в формате:\n\n"
        "<code>14:30 текст</code> — сегодня\n"
        "<code>15.05 14:30 текст</code> — конкретная дата\n\n"
        "Например: <code>18:00 позвонить маме</code>",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(ReminderForm.waiting_for_new)
async def remind_add_receive(message: Message, state: FSMContext) -> None:
    await state.clear()
    args = message.text.strip()
    parts = args.split(maxsplit=1)
    time_part = parts[0]
    text_part = parts[1] if len(parts) > 1 else ""

    if len(parts) >= 2 and ":" in parts[1].split()[0]:
        time_part = parts[0] + " " + parts[1].split()[0]
        text_part = " ".join(parts[1].split()[1:])

    remind_at = _parse_remind_at(time_part)

    if remind_at is None or not text_part:
        await message.answer(
            "❗ Не понял формат. Попробуй так:\n"
            "<code>18:00 позвонить маме</code>",
            parse_mode="HTML",
        )
        return

    if remind_at <= datetime.now():
        await message.answer("❗ Время уже прошло. Укажи будущее время.")
        return

    from scheduler import schedule_reminder
    reminder_id = await db.add_reminder(message.from_user.id, text_part, remind_at)
    await schedule_reminder(reminder_id, message.from_user.id, text_part, remind_at)

    await message.answer(
        f"✅ Напоминание установлено!\n"
        f"🔔 <b>{remind_at.strftime('%d.%m.%Y в %H:%M')}</b>\n"
        f"📝 {text_part}",
        parse_mode="HTML",
    )
    await _show_reminders(message, message.from_user.id)


# --- FSM: редактирование через кнопку ---

@router.callback_query(F.data.startswith("remind:edit:"))
async def remind_edit_start(call: CallbackQuery, state: FSMContext) -> None:
    reminder_id = int(call.data.split(":")[2])
    await state.update_data(edit_id=reminder_id)
    await state.set_state(ReminderForm.waiting_for_edit_time)
    await call.message.answer(
        "✏️ Введи новое время и текст:\n\n"
        "<code>14:30 текст</code> — сегодня\n"
        "<code>15.05 14:30 текст</code> — конкретная дата",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(ReminderForm.waiting_for_edit_time)
async def remind_edit_receive(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    reminder_id = data["edit_id"]
    await state.clear()

    args = message.text.strip()
    parts = args.split(maxsplit=1)
    time_part = parts[0]
    text_part = parts[1] if len(parts) > 1 else ""

    if len(parts) >= 2 and ":" in parts[1].split()[0]:
        time_part = parts[0] + " " + parts[1].split()[0]
        text_part = " ".join(parts[1].split()[1:])

    remind_at = _parse_remind_at(time_part)

    if remind_at is None or not text_part:
        await message.answer(
            "❗ Не понял формат. Попробуй так:\n"
            "<code>18:00 позвонить маме</code>",
            parse_mode="HTML",
        )
        return

    if remind_at <= datetime.now():
        await message.answer("❗ Время уже прошло. Укажи будущее время.")
        return

    from scheduler import cancel_reminder, schedule_reminder
    cancel_reminder(reminder_id)
    await db.delete_reminder(reminder_id)
    new_id = await db.add_reminder(message.from_user.id, text_part, remind_at)
    await schedule_reminder(new_id, message.from_user.id, text_part, remind_at)

    await message.answer(
        f"✅ Напоминание обновлено!\n"
        f"🔔 <b>{remind_at.strftime('%d.%m.%Y в %H:%M')}</b>\n"
        f"📝 {text_part}",
        parse_mode="HTML",
    )
    await _show_reminders(message, message.from_user.id)


# --- Inline callbacks ---

@router.callback_query(F.data.startswith("remind:"))
async def remind_callback(call: CallbackQuery) -> None:
    parts = call.data.split(":")
    action = parts[1]

    if action == "refresh":
        await _show_reminders(call.message, call.from_user.id, edit=True)
        await call.answer("Обновлено")
        return

    if action == "del":
        reminder_id = int(parts[2])
        from scheduler import cancel_reminder
        await db.delete_reminder(reminder_id)
        cancel_reminder(reminder_id)
        await _show_reminders(call.message, call.from_user.id, edit=True)
        await call.answer("Удалено")
