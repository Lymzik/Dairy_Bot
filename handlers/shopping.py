from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from database import shopping as db
from keyboards.inline import shopping_list_kb

router = Router()


class ShoppingForm(StatesGroup):
    waiting_for_item = State()


def _format_shopping(items: list[dict]) -> str:
    if not items:
        return "🛒 <b>Список покупок пуст.</b>\n\nНажми <b>➕ Добавить продукт</b>"
    lines = ["🛒 <b>Список покупок:</b>\n"]
    for i, item in enumerate(items, 1):
        text = item["text"]
        if item["is_bought"]:
            lines.append(f"{i}. ✅ <s>{text}</s>")
        else:
            lines.append(f"{i}. {text}")
    return "\n".join(lines)


@router.message(Command("shopping"))
async def cmd_shopping(message: Message) -> None:
    items = await db.get_shopping_list(message.from_user.id)
    await message.answer(_format_shopping(items), reply_markup=shopping_list_kb(items), parse_mode="HTML")


@router.message(Command("addbuy"))
async def cmd_addbuy(message: Message) -> None:
    args = message.text.partition(" ")[2].strip()
    if not args:
        await message.answer("❗ Укажи название товара: /addbuy <i>молоко</i>", parse_mode="HTML")
        return
    await db.add_item(message.from_user.id, args)
    items = await db.get_shopping_list(message.from_user.id)
    await message.answer(
        f"✅ Добавлено!\n\n{_format_shopping(items)}",
        reply_markup=shopping_list_kb(items),
        parse_mode="HTML",
    )


@router.message(Command("buy"))
async def cmd_buy(message: Message) -> None:
    args = message.text.partition(" ")[2].strip()
    item = await _get_item(message, args)
    if item is None:
        return
    await db.mark_bought(item["id"], True)
    items = await db.get_shopping_list(message.from_user.id)
    await message.answer(_format_shopping(items), reply_markup=shopping_list_kb(items), parse_mode="HTML")


@router.message(Command("editbuy"))
async def cmd_editbuy(message: Message) -> None:
    args = message.text.partition(" ")[2].strip().split(maxsplit=1)
    if len(args) < 2 or not args[0].isdigit():
        await message.answer("❗ Формат: /editbuy <i>номер новое_название</i>", parse_mode="HTML")
        return
    item = await _get_item(message, args[0])
    if item is None:
        return
    await db.edit_item(item["id"], args[1])
    items = await db.get_shopping_list(message.from_user.id)
    await message.answer(
        f"✏️ Изменено!\n\n{_format_shopping(items)}",
        reply_markup=shopping_list_kb(items),
        parse_mode="HTML",
    )


@router.message(Command("delbuy"))
async def cmd_delbuy(message: Message) -> None:
    args = message.text.partition(" ")[2].strip()
    item = await _get_item(message, args)
    if item is None:
        return
    await db.delete_item(item["id"])
    items = await db.get_shopping_list(message.from_user.id)
    await message.answer(
        f"🗑 Удалено!\n\n{_format_shopping(items)}",
        reply_markup=shopping_list_kb(items),
        parse_mode="HTML",
    )


@router.message(Command("clearbought"))
async def cmd_clearbought(message: Message) -> None:
    count = await db.clear_bought(message.from_user.id)
    items = await db.get_shopping_list(message.from_user.id)
    await message.answer(
        f"🧹 Удалено купленных позиций: {count}\n\n{_format_shopping(items)}",
        reply_markup=shopping_list_kb(items),
        parse_mode="HTML",
    )


async def _get_item(message: Message, arg: str) -> dict | None:
    if not arg.isdigit():
        await message.answer("❗ Укажи номер товара, например: /buy 3")
        return None
    item = await db.get_item_by_pos(message.from_user.id, int(arg))
    if item is None:
        await message.answer("❗ Товар с таким номером не найден.")
    return item


# --- Inline callback handlers ---

@router.callback_query(F.data.startswith("shop:"))
async def shop_callback(call: CallbackQuery) -> None:
    parts = call.data.split(":")
    action = parts[1]

    if action == "refresh":
        items = await db.get_shopping_list(call.from_user.id)
        await call.message.edit_text(
            _format_shopping(items),
            reply_markup=shopping_list_kb(items),
            parse_mode="HTML",
        )
        await call.answer("Обновлено")
        return

    if action == "clearbought":
        count = await db.clear_bought(call.from_user.id)
        items = await db.get_shopping_list(call.from_user.id)
        await call.message.edit_text(
            f"🧹 Удалено: {count}\n\n{_format_shopping(items)}",
            reply_markup=shopping_list_kb(items),
            parse_mode="HTML",
        )
        await call.answer(f"Очищено: {count}")
        return

    if action == "add":
        await call.message.answer(
            "🛒 Напиши что добавить в список покупок.\n\n"
            "Можно сразу несколько через запятую:\n"
            "<code>молоко, хлеб, яйца</code>",
            parse_mode="HTML",
        )
        from aiogram.fsm.context import FSMContext
        # Устанавливаем состояние через отдельный обработчик ниже
        _shop_add_pending.add(call.from_user.id)
        await call.answer()
        return

    item_id = int(parts[2])
    if action == "buy":
        await db.mark_bought(item_id, True)
    elif action == "del":
        await db.delete_item(item_id)

    items = await db.get_shopping_list(call.from_user.id)
    await call.message.edit_text(
        _format_shopping(items),
        reply_markup=shopping_list_kb(items),
        parse_mode="HTML",
    )
    await call.answer()


_shop_add_pending: set[int] = set()


@router.message(F.text & ~F.text.startswith("/"))
async def shop_add_receive(message: Message) -> None:
    uid = message.from_user.id
    if uid not in _shop_add_pending:
        return
    _shop_add_pending.discard(uid)
    items_text = [t.strip() for t in message.text.split(",") if t.strip()]
    for item in items_text:
        await db.add_item(uid, item)
    items = await db.get_shopping_list(uid)
    added = len(items_text)
    await message.answer(
        f"✅ {'Добавлен 1 товар' if added == 1 else f'Добавлено товаров: {added}'}!\n\n{_format_shopping(items)}",
        reply_markup=shopping_list_kb(items),
        parse_mode="HTML",
    )
