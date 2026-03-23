from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from config import PRODUCTS

BTN_WATCH_LESSON = "🎬 Смотреть урок"
BTN_HELP = "❓ Помощь"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    # is_persistent=False — иначе Telegram снова показывает клавиатуру при входе в чат
    # до «Я посмотрел», даже после ReplyKeyboardRemove на /start
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_WATCH_LESSON), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=False,
    )


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Посмотреть бесплатный урок", callback_data="free_lesson")],
    ])


def after_lesson_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я посмотрел — продолжить", callback_data="watched_lesson")],
    ])


def products_keyboard() -> InlineKeyboardMarkup:
    """Меню продуктов после просмотра урока."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Закрытый канал", callback_data="group:channel")],
        [InlineKeyboardButton(text="📋 База проверенных врачей", callback_data="group:base")],
    ])


def tariff_keyboard(group: str) -> InlineKeyboardMarkup:
    buttons = []
    for key, p in PRODUCTS.items():
        if p["group"] == group:
            buttons.append([
                InlineKeyboardButton(
                    text=f"📅 {p['days']} дней — {p['price']} ₽",
                    callback_data=f"product:{key}",
                )
            ])
    buttons.append([InlineKeyboardButton(text="← Назад", callback_data="back_to_products")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_product_keyboard(product_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay:{product_key}")],
        [InlineKeyboardButton(text="← Назад", callback_data=f"group:{PRODUCTS[product_key]['group']}")],
    ])


def cancel_payment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить оплату", callback_data="back_to_products")],
    ])


def payment_also_services_keyboard() -> InlineKeyboardMarkup:
    """Под сообщением об оплате — другие услуги + отмена."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔐 Закрытый канал", callback_data="from_payment:channel"),
            InlineKeyboardButton(text="📋 База врачей", callback_data="from_payment:base"),
        ],
        [InlineKeyboardButton(text="❌ Отменить оплату", callback_data="back_to_products")],
    ])


def admin_approve_keyboard(user_id: int, product_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"approve:{user_id}:{product_key}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}:{product_key}"),
        ],
    ])


def renewal_keyboard(product_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, продлить", callback_data=f"renew:{product_key}")],
        [InlineKeyboardButton(text="❌ Нет, спасибо", callback_data="renew_no")],
    ])


def city_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад к продуктам", callback_data="back_to_products")],
    ])


def back_to_products_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Смотреть другие продукты", callback_data="back_to_products")],
    ])
