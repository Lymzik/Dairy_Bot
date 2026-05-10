from datetime import date
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from database import plans as db
from keyboards.inline import plans_list_kb, carry_over_kb

router = Router()


async def _check_and_notify_carryover(target: Message, user_id: int) -> None:
    """Проверяет вчерашние невыполненные задачи и предлагает перенести."""
    yesterday_undone = await db.get_yesterday_undone(user_id)
    if not yesterday_undone:
        return
    lines = ["📌 <b>Вчера остались невыполненные задачи:</b>\n"]
    for i, p in enumerate(yesterday_undone, 1):
        icon = "❗" if p["is_important"] else "⬜"
        lines.append(f"{i}. {icon} {p['text']}")
    lines.append("\nПеренести их на сегодня?")
    ids = [p["id"] for p in yesterday_undone]
    await target.answer("\n".join(lines), reply_markup=carry_over_kb(ids), parse_mode="HTML")


def _format_plans(plans: list[dict]) -> str:
    if not plans:
        return "📋 <b>Планы на сегодня</b>\nПланов пока нет. Напиши что нужно сделать — добавлю в список."
    today_str = date.today().strftime("%d.%m.%Y")
    lines = [f"📋 <b>Планы на сегодня ({today_str})</b>\n"]
    for i, p in enumerate(plans, 1):
        text = p["text"]
        if p["is_important"] and not p["is_done"]:
            text = f"<b><i>{text}</i></b>"
        elif p["is_important"] and p["is_done"]:
            text = f"<s><b>{text}</b></s>"
        elif p["is_done"]:
            text = f"<s>{text}</s>"
        icon = "✅" if p["is_done"] else ("❗" if p["is_important"] else "⬜")
        lines.append(f"{i}. {icon} {text}")
    return "\n".join(lines)


@router.message(Command("plans"))
async def cmd_plans(message: Message) -> None:
    await _check_and_notify_carryover(message, message.from_user.id)
    plans = await db.get_today_plans(message.from_user.id)
    await message.answer(_format_plans(plans), reply_markup=plans_list_kb(plans), parse_mode="HTML")


@router.message(Command("addplan"))
async def cmd_addplan(message: Message) -> None:
    args = message.text.partition(" ")[2].strip()
    if not args:
        await message.answer("❗ Укажи текст плана: /addplan <i>купить продукты</i>", parse_mode="HTML")
        return
    items = _parse_items(args)
    for item in items:
        await db.add_plan(message.from_user.id, item)
    plans = await db.get_today_plans(message.from_user.id)
    added = len(items)
    await message.answer(
        f"✅ {'Добавлен 1 план' if added == 1 else f'Добавлено планов: {added}'}!\n\n{_format_plans(plans)}",
        reply_markup=plans_list_kb(plans),
        parse_mode="HTML",
    )


@router.message(Command("done"))
async def cmd_done(message: Message) -> None:
    args = message.text.partition(" ")[2].strip()
    plan = await _get_plan(message, args)
    if plan is None:
        return
    await db.set_plan_done(plan["id"], True)
    plans = await db.get_today_plans(message.from_user.id)
    await message.answer(_format_plans(plans), reply_markup=plans_list_kb(plans), parse_mode="HTML")


@router.message(Command("undone"))
async def cmd_undone(message: Message) -> None:
    args = message.text.partition(" ")[2].strip()
    plan = await _get_plan(message, args)
    if plan is None:
        return
    await db.set_plan_done(plan["id"], False)
    plans = await db.get_today_plans(message.from_user.id)
    await message.answer(_format_plans(plans), reply_markup=plans_list_kb(plans), parse_mode="HTML")


@router.message(Command("important"))
async def cmd_important(message: Message) -> None:
    args = message.text.partition(" ")[2].strip()
    plan = await _get_plan(message, args)
    if plan is None:
        return
    new_state = not bool(plan["is_important"])
    await db.set_plan_important(plan["id"], new_state)
    status = "помечен как важный ❗" if new_state else "снята отметка важности"
    plans = await db.get_today_plans(message.from_user.id)
    await message.answer(
        f"Пункт #{args} {status}\n\n{_format_plans(plans)}",
        reply_markup=plans_list_kb(plans),
        parse_mode="HTML",
    )


@router.message(Command("delplan"))
async def cmd_delplan(message: Message) -> None:
    args = message.text.partition(" ")[2].strip()
    plan = await _get_plan(message, args)
    if plan is None:
        return
    await db.delete_plan(plan["id"])
    plans = await db.get_today_plans(message.from_user.id)
    await message.answer(
        f"🗑 Пункт #{args} удалён.\n\n{_format_plans(plans)}",
        reply_markup=plans_list_kb(plans),
        parse_mode="HTML",
    )


# Временное хранилище текста: {message_id: text}
_pending: dict[int, str] = {}


def _parse_items(text: str) -> list[str]:
    """
    Парсит текст в список пунктов:
    - Многострочный текст → каждая строка отдельный пункт
    - Строки вида '1. текст', '1) текст', '- текст' → очищаем префикс
    - Однострочный текст с запятыми → разбиваем по запятой
    """
    import re
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    if len(lines) > 1:
        # Многострочный — каждая строка пункт, убираем нумерацию/маркеры
        items = []
        for line in lines:
            cleaned = re.sub(r'^(\d+[\.\)]\s*|[-•*]\s*)', '', line).strip()
            if cleaned:
                items.append(cleaned)
        return items

    # Однострочный — разбиваем по запятой
    return [t.strip() for t in text.split(",") if t.strip()]


@router.message(F.text & ~F.text.startswith("/"))
async def free_text_handler(message: Message) -> None:
    uid = message.from_user.id
    text = message.text.strip()
    if not text:
        return

    # Спрашиваем куда добавить
    from keyboards.inline import add_to_section_kb
    await message.answer(
        f"Куда добавить?\n\n<i>{text}</i>",
        reply_markup=add_to_section_kb(message.message_id),
        parse_mode="HTML",
    )
    _pending[message.message_id] = text


@router.callback_query(F.data.startswith("addto:"))
async def addto_callback(call: CallbackQuery) -> None:
    from database import shopping as shop_db
    from keyboards.inline import shopping_list_kb
    from handlers.shopping import _format_shopping

    parts = call.data.split(":")
    action = parts[1]

    if action == "cancel":
        msg_id = int(parts[2]) if len(parts) > 2 else None
        if msg_id:
            _pending.pop(msg_id, None)
        await call.message.edit_text("❌ Отменено.")
        await call.answer()
        return

    msg_id = int(parts[2])
    text = _pending.pop(msg_id, None)
    if not text:
        await call.answer("⚠️ Время ожидания истекло, введи текст заново.")
        await call.message.edit_text("⚠️ Сессия устарела. Введи текст ещё раз.")
        return

    items = _parse_items(text)
    uid = call.from_user.id

    if action == "plan":
        for item in items:
            await db.add_plan(uid, item)
        plans = await db.get_today_plans(uid)
        added = len(items)
        await call.message.edit_text(
            f"✅ {'Добавлен 1 план' if added == 1 else f'Добавлено планов: {added}'}!\n\n{_format_plans(plans)}",
            reply_markup=plans_list_kb(plans),
            parse_mode="HTML",
        )
    elif action == "shop":
        for item in items:
            await shop_db.add_item(uid, item)
        shopping = await shop_db.get_shopping_list(uid)
        added = len(items)
        await call.message.edit_text(
            f"🛒 {'Добавлен 1 товар' if added == 1 else f'Добавлено товаров: {added}'}!\n\n{_format_shopping(shopping)}",
            reply_markup=shopping_list_kb(shopping),
            parse_mode="HTML",
        )

    elif action == "remind":
        from keyboards.inline import remind_hour_kb
        from handlers.reminders import _text_pending as rem_pending
        from aiogram.fsm.state import State
        rem_pending[call.from_user.id] = text
        await call.message.edit_text(
            f"⏰ Выбери час или введи вручную (<code>14:30</code>):\n\n<i>{text}</i>",
            reply_markup=remind_hour_kb(),
            parse_mode="HTML",
        )

    await call.answer()


async def _get_plan(message: Message, arg: str) -> dict | None:
    if not arg.isdigit():
        await message.answer("❗ Укажи номер пункта, например: /done 2")
        return None
    plan = await db.get_plan_by_pos(message.from_user.id, int(arg))
    if plan is None:
        await message.answer("❗ Пункт с таким номером не найден.")
    return plan


# --- Inline callback handlers ---

@router.callback_query(F.data.startswith("plan:"))
async def plan_callback(call: CallbackQuery) -> None:
    parts = call.data.split(":")
    action = parts[1]

    if action == "refresh":
        plans = await db.get_today_plans(call.from_user.id)
        await call.message.edit_text(
            _format_plans(plans),
            reply_markup=plans_list_kb(plans),
            parse_mode="HTML",
        )
        await call.answer("Обновлено")
        return

    plan_id = int(parts[2])

    if action == "done":
        await db.set_plan_done(plan_id, True)
    elif action == "undone":
        await db.set_plan_done(plan_id, False)
    elif action == "imp":
        await db.set_plan_important(plan_id, True)
    elif action == "unimp":
        await db.set_plan_important(plan_id, False)
    elif action == "del":
        await db.delete_plan(plan_id)

    plans = await db.get_today_plans(call.from_user.id)
    await call.message.edit_text(
        _format_plans(plans),
        reply_markup=plans_list_kb(plans),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("carryover:"))
async def carryover_callback(call: CallbackQuery) -> None:
    parts = call.data.split(":", 2)
    action = parts[1]

    if action == "no":
        ids = [int(i) for i in parts[2].split(",") if i]
        await db.dismiss_carryover(ids)
        await call.message.edit_text("👌 Хорошо, старые задачи остались в прошлом.")
        await call.answer()
        return

    # action == "yes"
    ids = [int(i) for i in parts[2].split(",") if i]
    await db.carry_over_plans(call.from_user.id, ids)
    plans = await db.get_today_plans(call.from_user.id)
    await call.message.edit_text(
        f"✅ Перенесено задач: {len(ids)}\n\n{_format_plans(plans)}",
        reply_markup=plans_list_kb(plans),
        parse_mode="HTML",
    )
    await call.answer()
