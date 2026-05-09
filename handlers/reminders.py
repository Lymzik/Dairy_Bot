from datetime import datetime, date, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from database import reminders as db
from keyboards.inline import reminders_list_kb, main_menu_kb, remind_hour_kb, remind_minute_kb

router = Router()


class ReminderForm(StatesGroup):
    waiting_for_text = State()        # ввод текста
    waiting_for_manual_time = State() # ручной ввод времени (или кнопки)
    waiting_for_edit_text = State()   # ввод нового текста при редактировании


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


# --- Команды ---

@router.message(Command("reminders"))
async def cmd_reminders(message: Message) -> None:
    await _show_reminders(message, message.from_user.id)


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


# --- Добавление через кнопку: сначала текст, потом время ---

@router.callback_query(F.data == "remind:add")
async def remind_add_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ReminderForm.waiting_for_text)
    await call.message.answer(
        "📝 Напиши текст напоминания:",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(ReminderForm.waiting_for_text)
async def remind_text_received(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    await state.set_state(ReminderForm.waiting_for_manual_time)
    _text_pending[message.from_user.id] = text
    await message.answer(
        f"⏰ Выбери время или введи вручную:\n\n"
        f"<i>{text}</i>\n\n"
        f"<b>Вручную:</b> напиши <code>14:30</code> или <code>15.05 14:30</code>",
        reply_markup=remind_hour_kb(),
        parse_mode="HTML",
    )


@router.message(ReminderForm.waiting_for_manual_time)
async def remind_manual_time_received(message: Message, state: FSMContext) -> None:
    uid = message.from_user.id
    time_arg = message.text.strip()
    text = _text_pending.pop(uid, None)
    if not text:
        await state.clear()
        await message.answer("⚠️ Сессия устарела, попробуй снова.")
        return

    remind_at = _parse_remind_at(time_arg)
    if remind_at is None:
        _text_pending[uid] = text
        await message.answer(
            f"❗ Не понял формат. Попробуй: <code>14:30</code> или <code>15.05 14:30</code>\n\n"
            f"Или выбери час из кнопок выше.",
            parse_mode="HTML",
        )
        return

    if remind_at <= datetime.now():
        _text_pending[uid] = text
        await message.answer("❗ Это время уже прошло. Укажи будущее время.")
        return

    await state.clear()
    from scheduler import schedule_reminder
    reminder_id = await db.add_reminder(uid, text, remind_at)
    await schedule_reminder(reminder_id, uid, text, remind_at)
    await message.answer(
        f"✅ Напоминание установлено!\n"
        f"🔔 <b>{remind_at.strftime('%d.%m.%Y в %H:%M')}</b>\n"
        f"📝 {text}",
        parse_mode="HTML",
    )
    await _show_reminders(message, uid)


# --- Выбор времени через кнопки ---

_text_pending: dict[int, str] = {}
_edit_pending: dict[int, int] = {}  # user_id -> reminder_id


@router.callback_query(F.data.startswith("remtime:"))
async def remtime_callback(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split(":")
    action = parts[1]
    uid = call.from_user.id

    if action == "cancel":
        _text_pending.pop(uid, None)
        _edit_pending.pop(uid, None)
        await state.clear()
        await call.message.edit_text("❌ Отменено.")
        await call.answer()
        return

    if action == "back":
        text = _text_pending.get(uid, "")
        await call.message.edit_text(
            f"⏰ Выбери час для напоминания:\n\n<i>{text}</i>",
            reply_markup=remind_hour_kb(),
            parse_mode="HTML",
        )
        await call.answer()
        return

    if action == "hour":
        hour = int(parts[2])
        text = _text_pending.get(uid, "")
        await call.message.edit_text(
            f"⏰ Выбери минуты ({hour:02d}:?):\n\n<i>{text}</i>",
            reply_markup=remind_minute_kb(hour),
            parse_mode="HTML",
        )
        await call.answer()
        return

    if action == "minute":
        hour = int(parts[2])
        minute = int(parts[3])
        text = _text_pending.pop(uid, None)
        reminder_id = _edit_pending.pop(uid, None)

        now = datetime.now()
        remind_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        # Если время уже прошло сегодня — ставим на завтра
        if remind_at <= now:
            remind_at += timedelta(days=1)

        from scheduler import schedule_reminder, cancel_reminder

        if reminder_id:
            # Редактирование существующего
            cancel_reminder(reminder_id)
            await db.delete_reminder(reminder_id)

        if not text:
            await call.answer("⚠️ Текст напоминания потерян, попробуй снова.")
            return

        await state.clear()
        new_id = await db.add_reminder(uid, text, remind_at)
        await schedule_reminder(new_id, uid, text, remind_at)

        day_label = "завтра" if remind_at.date() > now.date() else "сегодня"
        await call.message.edit_text(
            f"✅ Напоминание установлено на <b>{day_label} в {remind_at.strftime('%H:%M')}</b>!\n"
            f"📝 {text}",
            parse_mode="HTML",
        )
        await _show_reminders(call.message, uid)
        await call.answer()


# --- Редактирование через кнопку ---

@router.callback_query(F.data.startswith("remind:edit:"))
async def remind_edit_start(call: CallbackQuery, state: FSMContext) -> None:
    reminder_id = int(call.data.split(":")[2])
    _edit_pending[call.from_user.id] = reminder_id
    await state.set_state(ReminderForm.waiting_for_edit_text)
    await call.message.answer(
        "✏️ Введи новый текст напоминания:",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(ReminderForm.waiting_for_edit_text)
async def remind_edit_text_received(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    await state.clear()
    _text_pending[message.from_user.id] = text
    await message.answer(
        f"⏰ Выбери новый час для напоминания:\n\n<i>{text}</i>",
        reply_markup=remind_hour_kb(),
        parse_mode="HTML",
    )


# --- Inline callbacks (удаление, обновление) ---

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
