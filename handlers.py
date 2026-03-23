from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from states import UserFlow
from keyboards import (
    start_keyboard,
    products_keyboard,
    after_lesson_keyboard,
    tariff_keyboard,
    confirm_product_keyboard,
    payment_also_services_keyboard,
    admin_approve_keyboard,
    renewal_keyboard,
    back_to_products_keyboard,
    city_back_keyboard,
    main_reply_keyboard,
    BTN_WATCH_LESSON,
    BTN_HELP,
)
from config import (
    FREE_LESSON_LINK,
    FREE_LESSON_FILE_ID,
    START_PHOTO_FILE_ID,
    PRODUCTS,
    ADMIN_USERNAMES,
    ADMIN_IDS_FIXED,
    CARD_NUMBER,
    CARD_HOLDER,
    CARD_BANK,
    HELP_CONTACT_USERNAMES,
)
from database import (
    add_subscription, save_admin, get_all_admin_ids,
    add_city, get_all_cities, find_city, city_display_name,
)

router = Router()
channel_router = Router()

_lesson_file_id: str = ""
_start_photo_id: str = ""
_admin_ids: set[int] = set(ADMIN_IDS_FIXED)
_payment_messages: dict[str, list[tuple[int, int]]] = {}

PRODUCTS_MENU_TEXT = (
    "📦 <b>Что я подготовил для вас</b>\n\n"
    "Вы сделали главный первый шаг — посмотрели бесплатный урок. "
    "Дальше открывается то, ради чего люди остаются со мной надолго: "
    "<b>глубина, честность и практика без лишней воды</b>.\n\n"
    "🔐 <b>Закрытый канал Doctor Aslan</b>\n"
    "Это не «ещё один канал в ленте». Внутри — <b>эксклюзив</b>, которого нет в открытом доступе: "
    "разборы реальных клинических ситуаций, актуальные методики, ответы от практикующего врача "
    "и материалы, которые помогают <b>понимать, а не гадать</b>. "
    "Новые выпуски плюс архив — чтобы вы могли возвращаться к темам в любой момент.\n\n"
    "📋 <b>База проверенных врачей</b>\n"
    "Устали читать сотни отзывов и надеяться на удачу? Я собрал <b>стоматологов, которых знаю лично</b> — "
    "город, контакты, клиника, специализация. Только те, за кого могу поручиться. "
    "База живёт и обновляется: вы получаете <b>короткий путь к специалисту</b>, а не рулетку в интернете.\n\n"
    "<b>Выберите направление</b> — проведу вас дальше 👇"
)


async def register_admin(user) -> None:
    _admin_ids.add(user.id)
    await save_admin(user.id, user.username or "")


def is_admin_sync(user) -> bool:
    if user.id in _admin_ids:
        return True
    username = (user.username or "").lower()
    if username in ADMIN_USERNAMES:
        return True
    return False


async def check_admin(user) -> bool:
    if user.id in _admin_ids:
        return True
    username = (user.username or "").lower()
    if username in ADMIN_USERNAMES:
        await register_admin(user)
        return True
    return False


def help_contact_lines() -> str:
    lines = []
    for u in HELP_CONTACT_USERNAMES:
        lines.append(f"• @{u} — <a href=\"https://t.me/{u}\">написать в Telegram</a>")
    if not lines:
        lines.append("• Напишите нам через этот чат — администратор ответит.")
    return "\n".join(lines)


async def deliver_free_lesson(message: Message, state: FSMContext, delete_previous: bool = False):
    """Отправить бесплатный урок. Во время ожидания чека состояние не сбрасываем."""
    if delete_previous:
        try:
            await message.delete()
        except TelegramBadRequest:
            pass

    current = await state.get_state()
    paying = current == UserFlow.waiting_receipt

    if not paying:
        await state.set_state(UserFlow.after_lesson)

    caption_pay = (
        "🎬 <b>Ваш бесплатный урок от Доктора Аслана</b>\n\n"
        "Посмотрите внимательно — в этом видео я показываю, "
        "как на практике работает мой подход к лечению.\n\n"
        "📸 Когда будете готовы — <b>пришлите скриншот чека</b> "
        "как фото в этот чат."
    )
    caption_normal = (
        "🎬 <b>Ваш бесплатный урок от Доктора Аслана</b>\n\n"
        "Посмотрите внимательно — в этом видео я показываю, "
        "как на практике работает мой подход к лечению. "
        "Это лишь малая часть того, что ждёт вас "
        "в закрытых материалах.\n\n"
        "☝️ Посмотрите урок и нажмите кнопку ниже 👇"
    )
    caption = caption_pay if paying else caption_normal
    reply_kb = payment_also_services_keyboard() if paying else after_lesson_keyboard()

    video_id = FREE_LESSON_FILE_ID or _lesson_file_id
    if video_id:
        try:
            await message.answer_video(
                video_id,
                caption=caption,
                reply_markup=reply_kb,
            )
        except Exception:
            await message.answer_document(
                video_id,
                caption=caption,
                reply_markup=reply_kb,
            )
    elif FREE_LESSON_LINK:
        await message.answer(
            f"🎬 <b>Бесплатный урок от Доктора Аслана</b>\n\n"
            f"▶️ Смотреть: {FREE_LESSON_LINK}\n\n"
            + ("📸 Затем пришлите чек фото." if paying else "Посмотрите и нажмите кнопку ниже 👇"),
            reply_markup=reply_kb,
        )
    else:
        await message.answer(
            "⚠️ Урок пока не загружен. Обратитесь к администратору.",
        )

# ══════════════════════════════════════════════
#  Нижнее меню: Помощь / Смотреть урок (только после «Я посмотрел»)
# ══════════════════════════════════════════════
@router.message(F.text == BTN_HELP)
async def reply_menu_help(message: Message, state: FSMContext):
    await message.answer(
        "❓ <b>Помощь</b>\n\n"
        "Опишите вашу проблему или вопрос нашему администратору в личных сообщениях — "
        "мы ответим как можно скорее.\n\n"
        "<b>Контакты:</b>\n"
        f"{help_contact_lines()}",
        reply_markup=main_reply_keyboard(),
        disable_web_page_preview=True,
    )


@router.message(F.text == BTN_WATCH_LESSON)
async def reply_menu_lesson(message: Message, state: FSMContext):
    await deliver_free_lesson(message, state, delete_previous=False)


# ══════════════════════════════════════════════
#  Админ: пересылка из канала → показать chat_id
# ══════════════════════════════════════════════
@router.message(F.forward_origin)
async def admin_forward_info(message: Message):
    if not await check_admin(message.from_user):
        return

    chat_id = None
    title = "Неизвестно"

    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
        title = message.forward_from_chat.title or title

    if not chat_id and hasattr(message, "forward_origin") and message.forward_origin:
        origin = message.forward_origin
        if hasattr(origin, "chat"):
            chat_id = origin.chat.id
            title = origin.chat.title or title

    if chat_id:
        await message.answer(
            f"📌 Информация о канале:\n\n"
            f"Название: <b>{title}</b>\n"
            f"ID: <code>{chat_id}</code>\n\n"
            f"Скиньте этот ID сюда"
        )
    else:
        await message.answer(
            f"⚠️ Не удалось определить ID канала.\n\n"
            f"Добавьте бота @getidsbot в канал — он покажет ID."
        )


# ══════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(UserFlow.after_start)
    if is_admin_sync(message.from_user):
        await register_admin(message.from_user)

    text = (
        "🦷 <b>Doctor Aslan</b>\n\n"
        "Рад вас видеть! 👋\n\n"
        "Меня зовут <b>Доктор Аслан</b> — я практикующий стоматолог "
        "с многолетним опытом.\n\n"
        "Здесь я собрал всё самое ценное, "
        "что поможет вам разобраться в стоматологии "
        "и найти проверенного врача.\n\n"
        "Начните с <b>бесплатного видеоурока</b> 👇"
    )

    photo_id = START_PHOTO_FILE_ID or _start_photo_id
    if photo_id:
        await message.answer_photo(
            photo_id,
            caption=text,
            reply_markup=start_keyboard(),
        )
    else:
        await message.answer(text, reply_markup=start_keyboard())


# ══════════════════════════════════════════════
#  Бесплатный урок
# ══════════════════════════════════════════════
@router.callback_query(F.data == "free_lesson")
async def free_lesson(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await deliver_free_lesson(callback.message, state, delete_previous=True)


# ══════════════════════════════════════════════
#  Кнопка "Я посмотрел" → показать продукты
# ══════════════════════════════════════════════
@router.callback_query(F.data == "watched_lesson")
async def watched_lesson(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.message.answer(
        PRODUCTS_MENU_TEXT,
        reply_markup=products_keyboard(),
    )
    await callback.message.answer(
        " ",
        reply_markup=main_reply_keyboard(),
        disable_notification=True,
    )


@router.message(F.text == "/menu")
async def restore_bottom_menu(message: Message):
    await message.answer(
        "✅ Нижнее меню восстановлено.",
        reply_markup=main_reply_keyboard(),
    )


# ══════════════════════════════════════════════
#  Выбор группы продуктов (канал / база)
# ══════════════════════════════════════════════
@router.callback_query(F.data.startswith("group:"))
async def select_group(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    group = callback.data.split(":")[1]

    if group == "channel":
        text = (
            "🔐 <b>Закрытый канал Doctor Aslan</b>\n\n"
            "Это не просто канал — это ваш личный наставник "
            "в мире стоматологии.\n\n"
            "<b>Что внутри:</b>\n"
            "✦ Подробные видеоуроки по актуальным методикам\n"
            "✦ Разборы реальных клинических кейсов\n"
            "✦ Ответы на вопросы от практикующего врача\n"
            "✦ Новые материалы каждую неделю\n"
            "✦ Доступ к архиву всех прошлых публикаций\n\n"
            "Те, кто уже внутри, говорят: <i>«Лучшее вложение "
            "в своё здоровье за последний год»</i>\n\n"
            "Выберите срок подписки 👇"
        )
        await callback.message.edit_text(text, reply_markup=tariff_keyboard(group))
    else:
        await state.set_state(UserFlow.city_choice)
        await callback.message.edit_text(
            "📋 <b>База проверенных врачей</b>\n\n"
            "Найти хорошего стоматолога — задача не из лёгких. "
            "Я решил её за вас.\n\n"
            "🏙 <b>Напишите ваш город</b>, и я проверю, "
            "есть ли у нас проверенные врачи рядом с вами.\n\n"
            "Например: <i>Москва</i>, <i>Санкт-Петербург</i>, <i>Казань</i>",
            reply_markup=city_back_keyboard(),
        )


# ══════════════════════════════════════════════
#  Выбор тарифа (30 / 90 дней)
# ══════════════════════════════════════════════
@router.callback_query(F.data.startswith("product:"))
async def select_product(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    product_key = callback.data.split(":")[1]

    if product_key not in PRODUCTS:
        await callback.message.answer("⚠️ Тариф не найден.")
        return

    product = PRODUCTS[product_key]
    await state.update_data(selected_product=product_key)
    await state.set_state(UserFlow.product_selected)

    await callback.message.edit_text(
        f"💳 <b>Оформление доступа</b>\n\n"
        f"{product['emoji']} <b>{product['name']}</b>\n"
        f"💰 Стоимость: <b>{product['price']} ₽</b>\n"
        f"📅 Срок: <b>{product['days']} дней</b>\n\n"
        f"После оплаты вы мгновенно получите персональную "
        f"ссылку для доступа прямо в этот чат.\n\n"
        f"Нажмите «Оплатить» 👇",
        reply_markup=confirm_product_keyboard(product_key),
    )


# ══════════════════════════════════════════════
#  Назад
# ══════════════════════════════════════════════
@router.callback_query(F.data == "back_to_products")
async def back_to_products(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(UserFlow.after_lesson)
    await callback.message.edit_text(
        PRODUCTS_MENU_TEXT,
        reply_markup=products_keyboard(),
    )


@router.callback_query(F.data.startswith("from_payment:"))
async def from_payment_other_service(callback: CallbackQuery, state: FSMContext):
    """С экрана оплаты — перейти к другому продукту."""
    await callback.answer()
    side = callback.data.split(":")[1]

    if side == "channel":
        await state.set_state(UserFlow.after_lesson)
        text = (
            "🔐 <b>Закрытый канал Doctor Aslan</b>\n\n"
            "Это не просто канал — это ваш личный наставник "
            "в мире стоматологии.\n\n"
            "<b>Что внутри:</b>\n"
            "✦ Подробные видеоуроки по актуальным методикам\n"
            "✦ Разборы реальных клинических кейсов\n"
            "✦ Ответы на вопросы от практикующего врача\n"
            "✦ Новые материалы каждую неделю\n"
            "✦ Доступ к архиву всех прошлых публикаций\n\n"
            "Выберите срок подписки 👇"
        )
        await callback.message.edit_text(text, reply_markup=tariff_keyboard("channel"))
    else:
        await state.set_state(UserFlow.city_choice)
        await callback.message.edit_text(
            "📋 <b>База проверенных врачей</b>\n\n"
            "🏙 <b>Напишите ваш город</b>, и я проверю, "
            "есть ли у нас проверенные врачи рядом с вами.\n\n"
            "Например: <i>Москва</i>, <i>Санкт-Петербург</i>, <i>Казань</i>",
            reply_markup=city_back_keyboard(),
        )


@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(UserFlow.after_start)
    rm_msg = await callback.bot.send_message(
        callback.message.chat.id,
        ".",
        reply_markup=ReplyKeyboardRemove(),
        disable_notification=True,
    )
    await callback.message.edit_text(
        "🦷 <b>Doctor Aslan</b>\n\n"
        "Нажмите кнопку ниже, чтобы посмотреть "
        "бесплатный урок и узнать больше 👇",
        reply_markup=start_keyboard(),
    )
    try:
        await rm_msg.delete()
    except TelegramBadRequest:
        pass


# ══════════════════════════════════════════════
#  Оплата — показать карту и ждать чек
# ══════════════════════════════════════════════
@router.callback_query(F.data.startswith("pay:"))
async def show_payment_details(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    product_key = callback.data.split(":")[1]
    product = PRODUCTS.get(product_key)
    if not product:
        return

    await state.update_data(selected_product=product_key)
    await state.set_state(UserFlow.waiting_receipt)

    await callback.message.edit_text(
        f"💳 <b>Оплата</b>\n\n"
        f"{product['emoji']} <b>{product['name']}</b>\n"
        f"💰 Сумма к оплате: <b>{product['price']} ₽</b>\n"
        f"📅 Подписка: <b>{product['days']} дней</b>\n\n"
        f"Переведите точную сумму на карту:\n\n"
        f"🏦 Банк: <b>{CARD_BANK}</b>\n"
        f"💳 Карта: <code>{CARD_NUMBER}</code>\n"
        f"👤 Получатель: <b>{CARD_HOLDER}</b>\n\n"
        f"📸 После оплаты <b>отправьте скриншот чека</b> "
        f"прямо в этот чат.\n\n"
        f"Мы проверим оплату и мгновенно добавим вас "
        f"в закрытый канал ⚡\n\n"
        f"💡 <b>Пока готовите перевод</b> — можете посмотреть "
        f"другую услугу или бесплатный урок (кнопки под сообщением и внизу экрана).",
        reply_markup=payment_also_services_keyboard(),
    )


# ══════════════════════════════════════════════
#  Продление подписки
# ══════════════════════════════════════════════
@router.callback_query(F.data.startswith("renew:"))
async def renew_subscription(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    product_key = callback.data.split(":")[1]
    product = PRODUCTS.get(product_key)
    if not product:
        return

    await state.update_data(selected_product=product_key)
    await state.set_state(UserFlow.waiting_receipt)

    await callback.message.edit_text(
        f"🔄 <b>Продление подписки</b>\n\n"
        f"{product['emoji']} <b>{product['name']}</b>\n"
        f"💰 Сумма: <b>{product['price']} ₽</b>\n"
        f"📅 Ещё {product['days']} дней доступа\n\n"
        f"Переведите точную сумму на карту:\n\n"
        f"🏦 Банк: <b>{CARD_BANK}</b>\n"
        f"💳 Карта: <code>{CARD_NUMBER}</code>\n"
        f"👤 Получатель: <b>{CARD_HOLDER}</b>\n\n"
        f"📸 Отправьте <b>скриншот чека</b> сюда 👇\n\n"
        f"💡 Можете заглянуть в <b>другую услугу</b> — кнопки ниже.",
        reply_markup=payment_also_services_keyboard(),
    )


@router.callback_query(F.data == "renew_no")
async def renew_decline(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "👋 <b>Спасибо за время с нами!</b>\n\n"
        "Ваша подписка завершится по истечении срока.\n\n"
        "Вы всегда можете вернуться и оформить "
        "доступ заново — мы будем рады! 🦷",
        reply_markup=back_to_products_keyboard(),
    )


# ══════════════════════════════════════════════
#  Пользователь ввёл город
# ══════════════════════════════════════════════
@router.message(UserFlow.city_choice, F.text)
async def process_city(message: Message, state: FSMContext):
    if await check_admin(message.from_user) and message.text.startswith("/"):
        return

    query = message.text.strip()
    if query in (BTN_HELP, BTN_WATCH_LESSON):
        return
    # Текст города → тот же ключ, что у #хештега в постах канала (см. database.find_city)
    matched = await find_city(query)

    if matched:
        city_label = city_display_name(matched)
        await message.answer(
            f"✅ <b>Отлично!</b>\n\n"
            f"Да — у нас есть <b>проверенные стоматологи</b> "
            f"в городе <b>{city_label}</b>!\n\n"
            f"Оформите доступ — и вы получите контакты, "
            f"адреса клиник и специализации лучших врачей.\n\n"
            f"Выберите срок подписки 👇",
            reply_markup=tariff_keyboard("base"),
        )
    else:
        all_cities = await get_all_cities()
        if all_cities:
            cities_list = ", ".join(city_display_name(c) for c in all_cities)
            await message.answer(
                f"😔 К сожалению, в городе <b>{query}</b> "
                f"пока нет врачей в нашей базе.\n\n"
                f"🏙 <b>Сейчас у нас есть врачи в:</b>\n"
                f"{cities_list}\n\n"
                f"Напишите другой город или вернитесь назад 👇",
                reply_markup=city_back_keyboard(),
            )
        else:
            await message.answer(
                f"😔 К сожалению, в городе <b>{query}</b> "
                f"пока нет врачей в нашей базе.\n\n"
                f"Мы постоянно расширяем базу — "
                f"попробуйте позже или напишите другой город.",
                reply_markup=city_back_keyboard(),
            )


@router.message(UserFlow.city_choice)
async def city_choice_not_text(message: Message):
    await message.answer("✏️ Пожалуйста, напишите название города текстом.")


# ══════════════════════════════════════════════
#  Пользователь отправил чек (фото)
# ══════════════════════════════════════════════
@router.message(UserFlow.waiting_receipt, F.photo)
async def receive_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    product_key = data.get("selected_product", "")
    product = PRODUCTS.get(product_key)
    if not product:
        await message.answer("⚠️ Ошибка. Нажмите /start и попробуйте заново.")
        return

    await state.set_state(UserFlow.payment_sent)

    await message.answer(
        "⏳ <b>Чек получен!</b>\n\n"
        "Спасибо! Ваш чек отправлен на проверку.\n\n"
        "Как только администратор подтвердит оплату — "
        "вы мгновенно получите ссылку на доступ "
        "прямо сюда, в этот чат.\n\n"
        "Обычно это занимает не больше пары минут ⚡",
        reply_markup=main_reply_keyboard(),
    )

    photo_id = message.photo[-1].file_id
    admin_text = (
        f"💰 <b>Новая оплата — проверьте чек!</b>\n\n"
        f"👤 {message.from_user.full_name} "
        f"(@{message.from_user.username or 'нет'})\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n\n"
        f"{product['emoji']} <b>{product['name']}</b>\n"
        f"💰 Сумма: <b>{product['price']} ₽</b>\n"
        f"📅 Подписка: {product['days']} дней"
    )

    all_admins = await get_all_admin_ids() | _admin_ids
    payment_key = f"{message.from_user.id}:{product_key}"
    sent_messages = []
    for admin_id in all_admins:
        try:
            sent = await message.bot.send_photo(
                admin_id,
                photo_id,
                caption=admin_text,
                reply_markup=admin_approve_keyboard(message.from_user.id, product_key),
            )
            sent_messages.append((admin_id, sent.message_id))
        except Exception:
            pass
    _payment_messages[payment_key] = sent_messages


@router.message(UserFlow.waiting_receipt)
async def waiting_receipt_not_photo(message: Message):
    if await check_admin(message.from_user):
        return
    if message.text and message.text.strip() in (BTN_HELP, BTN_WATCH_LESSON):
        return
    await message.answer(
        "📸 Пожалуйста, отправьте <b>скриншот чека</b> (фото).\n\n"
        "Нужно именно фото — не файл и не текст.\n\n"
        "❓ Вопросы — кнопка «Помощь» внизу. "
        "🎬 Урок — «Смотреть урок».",
        reply_markup=main_reply_keyboard(),
    )


# ══════════════════════════════════════════════
#  Админ: принять оплату
# ══════════════════════════════════════════════
@router.callback_query(F.data.startswith("approve:"))
async def admin_approve(callback: CallbackQuery):
    if not await check_admin(callback.from_user):
        await callback.answer("⛔ Вы не администратор.", show_alert=True)
        return

    await callback.answer()
    parts = callback.data.split(":")
    user_id = int(parts[1])
    product_key = parts[2]

    product = PRODUCTS.get(product_key)
    if not product:
        await callback.message.answer("⚠️ Продукт не найден.")
        return

    invite_link = product.get("invite_link", "")
    if not invite_link:
        await callback.message.answer(f"⚠️ Ссылка для «{product['name']}» не настроена в .env")
        return

    days = product["days"]
    await add_subscription(user_id, product_key, days=days)

    try:
        await callback.bot.send_message(
            user_id,
            f"🎉 <b>Оплата подтверждена!</b>\n\n"
            f"{product['emoji']} <b>{product['name']}</b>\n\n"
            f"Спасибо за доверие! Вот ваша персональная ссылка:\n\n"
            f"👉 {invite_link}\n\n"
            f"📅 Ваш доступ активен <b>{days} дней</b>.\n"
            f"За день до окончания мы напомним о продлении.\n\n"
            f"Приятного обучения! 🦷✨",
            reply_markup=back_to_products_keyboard(),
        )
    except Exception as e:
        await callback.message.answer(f"⚠️ Не удалось отправить ссылку: {e}")
        return

    admin_name = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
    status_text = (
        f"\n\n✅ <b>ПРИНЯТО</b> — {admin_name}\n"
        f"📅 Подписка: {days} дней"
    )

    payment_key = f"{user_id}:{product_key}"
    sent_list = _payment_messages.pop(payment_key, [])
    for admin_id, msg_id in sent_list:
        try:
            await callback.bot.edit_message_caption(
                chat_id=admin_id,
                message_id=msg_id,
                caption=callback.message.caption + status_text,
                reply_markup=None,
            )
        except Exception:
            pass
    if not sent_list:
        try:
            await callback.message.edit_caption(
                caption=callback.message.caption + status_text,
                reply_markup=None,
            )
        except Exception:
            pass


# ══════════════════════════════════════════════
#  Админ: отклонить оплату
# ══════════════════════════════════════════════
@router.callback_query(F.data.startswith("reject:"))
async def admin_reject(callback: CallbackQuery):
    if not await check_admin(callback.from_user):
        await callback.answer("⛔ Вы не администратор.", show_alert=True)
        return

    await callback.answer()
    parts = callback.data.split(":")
    user_id = int(parts[1])
    product_key = parts[2]

    product = PRODUCTS.get(product_key)
    product_name = product["name"] if product else "продукт"

    try:
        await callback.bot.send_message(
            user_id,
            f"❌ <b>Оплата не подтверждена</b>\n\n"
            f"К сожалению, мы не смогли подтвердить "
            f"вашу оплату за «{product_name}».\n\n"
            f"Возможные причины:\n"
            f"• Сумма перевода не совпадает\n"
            f"• Чек нечитаемый или не соответствует\n\n"
            f"Попробуйте ещё раз или свяжитесь "
            f"с администратором для помощи.",
            reply_markup=back_to_products_keyboard(),
        )
    except Exception:
        pass

    admin_name = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
    status_text = f"\n\n❌ <b>ОТКЛОНЕНО</b> — {admin_name}"

    payment_key = f"{user_id}:{product_key}"
    sent_list = _payment_messages.pop(payment_key, [])
    for admin_id, msg_id in sent_list:
        try:
            await callback.bot.edit_message_caption(
                chat_id=admin_id,
                message_id=msg_id,
                caption=callback.message.caption + status_text,
                reply_markup=None,
            )
        except Exception:
            pass
    if not sent_list:
        try:
            await callback.message.edit_caption(
                caption=callback.message.caption + status_text,
                reply_markup=None,
            )
        except Exception:
            pass


# ══════════════════════════════════════════════
#  Админ: фото → сохранить для /start
# ══════════════════════════════════════════════
@router.message(F.photo)
async def admin_set_photo(message: Message):
    if not await check_admin(message.from_user):
        return
    file_id = message.photo[-1].file_id
    global _start_photo_id
    _start_photo_id = file_id
    await message.answer(
        f"✅ Фото сохранено для приветствия!\n\n"
        f"<code>START_PHOTO_FILE_ID={file_id}</code>"
    )


@router.message(F.video)
async def admin_set_video(message: Message):
    if not await check_admin(message.from_user):
        return
    file_id = message.video.file_id
    global _lesson_file_id
    _lesson_file_id = file_id
    await message.answer(
        f"✅ Видео сохранено как бесплатный урок!\n\n"
        f"<code>FREE_LESSON_FILE_ID={file_id}</code>"
    )


@router.message(F.document)
async def admin_set_document(message: Message):
    if not await check_admin(message.from_user):
        return
    mime = message.document.mime_type or ""
    if not mime.startswith("video/"):
        return
    file_id = message.document.file_id
    global _lesson_file_id
    _lesson_file_id = file_id
    await message.answer(
        f"✅ Видео-файл сохранено как бесплатный урок!\n\n"
        f"<code>FREE_LESSON_FILE_ID={file_id}</code>"
    )


# ══════════════════════════════════════════════
#  Админ: /grant и /send
# ══════════════════════════════════════════════
@router.message(F.text.startswith("/grant"))
async def admin_grant(message: Message):
    if not await check_admin(message.from_user):
        return

    parts = message.text.split()
    if len(parts) < 3:
        products_list = ", ".join(f"<b>{k}</b>" for k in PRODUCTS)
        await message.answer(f"Использование: <code>/grant USER_ID product_key</code>\nПродукты: {products_list}")
        return

    try:
        user_id = int(parts[1])
        product_key = parts[2]
    except (ValueError, IndexError):
        await message.answer("⚠️ Неверный формат.")
        return

    product = PRODUCTS.get(product_key)
    if not product:
        await message.answer("⚠️ Продукт не найден.")
        return

    invite_link = product.get("invite_link", "")
    if not invite_link:
        await message.answer("⚠️ Ссылка не настроена в .env")
        return

    days = product["days"]
    await add_subscription(user_id, product_key, days=days)

    try:
        await message.bot.send_message(
            user_id,
            f"🎉 <b>Доступ выдан!</b>\n\n"
            f"{product['emoji']} {product['name']}\n"
            f"👉 {invite_link}\n"
            f"📅 Доступ: <b>{days} дней</b>",
            reply_markup=back_to_products_keyboard(),
        )
        await message.answer(f"✅ Ссылка отправлена, подписка на {days} дней")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")


@router.message(F.text.startswith("/send"))
async def admin_send(message: Message):
    if not await check_admin(message.from_user):
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /send USER_ID текст")
        return

    try:
        user_id = int(parts[1])
        text = parts[2]
    except (ValueError, IndexError):
        await message.answer("⚠️ Неверный формат")
        return

    try:
        await message.bot.send_message(user_id, text)
        await message.answer("✅ Отправлено")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")


@router.message(F.text.startswith("/addcity"))
async def admin_addcity(message: Message):
    if not await check_admin(message.from_user):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "Использование: <code>/addcity москва, питер, казань</code>\n"
            "Города через запятую."
        )
        return

    cities_raw = parts[1].split(",")
    added = []
    for c in cities_raw:
        c = c.strip()
        if c:
            await add_city(c)
            added.append(c.lower())

    if added:
        await message.answer(f"✅ Добавлено городов: {len(added)}\n{', '.join(added)}")
    else:
        await message.answer("⚠️ Не удалось распознать города.")


@router.message(F.text.startswith("/cities"))
async def admin_list_cities(message: Message):
    if not await check_admin(message.from_user):
        return

    cities = await get_all_cities()
    if cities:
        lines = ", ".join(city_display_name(c) for c in cities)
        await message.answer(f"🏙 <b>Города в базе ({len(cities)}):</b>\n\n{lines}")
    else:
        await message.answer("Городов пока нет. Добавьте: <code>/addcity москва, питер</code>")


# ══════════════════════════════════════════════
#  Автосбор хештегов из канала "База врачей"
#  (#город → ключ в БД; пользователь пишет город текстом — find_city сравнивает тот же ключ)
# ══════════════════════════════════════════════
@channel_router.channel_post()
async def collect_hashtags(message: Message):
    if not message.entities:
        return
    for entity in message.entities:
        if entity.type == "hashtag":
            raw = message.text[entity.offset : entity.offset + entity.length]
            tag = raw[1:] if raw.startswith("#") else raw
            if tag:
                await add_city(tag)


@channel_router.channel_post(F.caption_entities)
async def collect_hashtags_caption(message: Message):
    for entity in message.caption_entities:
        if entity.type == "hashtag":
            raw = message.caption[entity.offset : entity.offset + entity.length]
            tag = raw[1:] if raw.startswith("#") else raw
            if tag:
                await add_city(tag)
