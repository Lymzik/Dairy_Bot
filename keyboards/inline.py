from datetime import date, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

DAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def add_to_section_kb(msg_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 В планы на день", callback_data=f"addto:plan:{msg_id}"),
        InlineKeyboardButton(text="🛒 В покупки", callback_data=f"addto:shop:{msg_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="⏰ В напоминания", callback_data=f"addto:remind:{msg_id}"),
    )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="addto:cancel"))
    return builder.as_markup()


def plan_date_kb(msg_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора даты для плана: сегодня, завтра, следующие 5 дней."""
    builder = InlineKeyboardBuilder()
    today = date.today()

    # Сегодня и завтра
    builder.row(
        InlineKeyboardButton(
            text="📅 Сегодня",
            callback_data=f"plandate:{msg_id}:{today.isoformat()}",
        ),
        InlineKeyboardButton(
            text=f"➡️ Завтра ({DAYS_RU[(today + timedelta(days=1)).weekday()]})",
            callback_data=f"plandate:{msg_id}:{(today + timedelta(days=1)).isoformat()}",
        ),
    )
    # Следующие 5 дней
    for i in range(2, 7):
        d = today + timedelta(days=i)
        builder.button(
            text=f"{DAYS_RU[d.weekday()]} {d.strftime('%d.%m')}",
            callback_data=f"plandate:{msg_id}:{d.isoformat()}",
        )
    builder.adjust(2, 2, 3)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="addto:cancel"))
    return builder.as_markup()


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Сводка дня", callback_data="menu:today"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Планы на день", callback_data="menu:plans"),
        InlineKeyboardButton(text="🛒 Покупки", callback_data="menu:shopping"),
    )
    builder.row(
        InlineKeyboardButton(text="⏰ Напоминания", callback_data="menu:reminders"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="menu:stats"),
    )
    return builder.as_markup()


def carry_over_kb(plan_ids: list[int]) -> InlineKeyboardMarkup:
    ids_str = ",".join(str(i) for i in plan_ids)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Перенести все", callback_data=f"carryover:yes:{ids_str}"),
        InlineKeyboardButton(text="❌ Не переносить", callback_data="carryover:no"),
    )
    return builder.as_markup()


def plans_list_kb(plans: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i, plan in enumerate(plans, 1):
        done_btn = InlineKeyboardButton(
            text=f"{'↩️' if plan['is_done'] else '✅'} #{i}",
            callback_data=f"plan:{'undone' if plan['is_done'] else 'done'}:{plan['id']}",
        )
        imp_btn = InlineKeyboardButton(
            text=f"{'🔕' if plan['is_important'] else '❗'} #{i}",
            callback_data=f"plan:{'unimp' if plan['is_important'] else 'imp'}:{plan['id']}",
        )
        del_btn = InlineKeyboardButton(
            text=f"🗑 #{i}",
            callback_data=f"plan:del:{plan['id']}",
        )
        builder.row(done_btn, imp_btn, del_btn)
    builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="plan:refresh"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"))
    return builder.as_markup()


def remind_hour_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for hour in range(0, 24):
        builder.button(
            text=f"{hour:02d}",
            callback_data=f"remtime:hour:{hour}",
        )
    builder.adjust(6)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="remtime:cancel"))
    return builder.as_markup()


def remind_minute_kb(hour: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for minute in range(0, 60, 10):
        builder.button(
            text=f"{hour:02d}:{minute:02d}",
            callback_data=f"remtime:minute:{hour}:{minute}",
        )
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="remtime:back"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="remtime:cancel"))
    return builder.as_markup()


def shopping_list_kb(items: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i, item in enumerate(items, 1):
        if not item["is_bought"]:
            builder.row(
                InlineKeyboardButton(
                    text=f"✅ Купил #{i}",
                    callback_data=f"shop:buy:{item['id']}",
                ),
                InlineKeyboardButton(
                    text=f"🗑 #{i}",
                    callback_data=f"shop:del:{item['id']}",
                ),
            )
    builder.row(InlineKeyboardButton(text="➕ Добавить продукт", callback_data="shop:add"))
    builder.row(
        InlineKeyboardButton(text="🧹 Очистить купленные", callback_data="shop:clearbought"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data="shop:refresh"),
    )
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"))
    return builder.as_markup()


def reminders_list_kb(reminders: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i, r in enumerate(reminders, 1):
        builder.row(
            InlineKeyboardButton(
                text=f"✏️ #{i}",
                callback_data=f"remind:edit:{r['id']}",
            ),
            InlineKeyboardButton(
                text=f"🗑 #{i}",
                callback_data=f"remind:del:{r['id']}",
            ),
        )
    builder.row(InlineKeyboardButton(text="➕ Добавить напоминание", callback_data="remind:add"))
    builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="remind:refresh"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"))
    return builder.as_markup()
