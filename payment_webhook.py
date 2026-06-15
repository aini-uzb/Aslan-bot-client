import asyncio
import logging

from aiohttp import web
from yookassa import Payment

from config import PRODUCTS, ADMIN_IDS_FIXED
from database import add_subscription, get_all_admin_ids, update_user_step
from keyboards import back_to_products_keyboard

logger = logging.getLogger(__name__)

_bot = None


def set_bot(bot) -> None:
    global _bot
    _bot = bot


async def handle_webhook(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except Exception:
        return web.Response(status=400)

    event = body.get("event", "")
    if event != "payment.succeeded":
        return web.Response(status=200)

    payment_id = body.get("object", {}).get("id")
    if not payment_id:
        return web.Response(status=400)

    try:
        payment = await asyncio.to_thread(Payment.find_one, payment_id)

        if payment.status != "succeeded":
            return web.Response(status=200)

        metadata = payment.metadata or {}
        user_id = int(metadata.get("user_id", 0))
        product_key = metadata.get("product_key", "")

        if not user_id or not product_key:
            logger.warning("Webhook missing metadata: user_id=%s product_key=%s", user_id, product_key)
            return web.Response(status=200)

        product = PRODUCTS.get(product_key)
        if not product:
            logger.warning("Webhook unknown product_key=%s", product_key)
            return web.Response(status=200)

        await add_subscription(user_id, product_key, days=product["days"])
        await update_user_step(user_id, "bought")
        logger.info("Payment confirmed: user=%s product=%s days=%s", user_id, product_key, product["days"])

        username = metadata.get("username", "")
        email = metadata.get("email", "")

        invite_link = product.get("invite_link", "")
        if _bot and invite_link:
            # Уведомление пользователю
            await _bot.send_message(
                user_id,
                f"🎉 <b>Оплата прошла успешно!</b>\n\n"
                f"{product['emoji']} <b>{product['name']}</b>\n\n"
                f"Вот ваша персональная ссылка для доступа:\n\n"
                f"👉 {invite_link}\n\n"
                f"📅 Доступ активен <b>{product['days']} дней</b>.\n"
                f"За день до окончания напомним о продлении.\n\n"
                f"Приятного обучения! 🦷✨",
                reply_markup=back_to_products_keyboard(),
            )

            # Уведомление всем админам
            admin_ids = await get_all_admin_ids()
            admin_ids.update(ADMIN_IDS_FIXED)

            try:
                chat = await _bot.get_chat(user_id)
                full_name = chat.full_name or str(user_id)
            except Exception:
                full_name = str(user_id)

            user_mention = f'<a href="tg://user?id={user_id}">{full_name}</a>'
            username_line = f"@{username}" if username else "нет username"

            admin_text = (
                f"💰 <b>Новая покупка!</b>\n\n"
                f"👤 {user_mention} ({username_line})\n"
                f"🆔 ID: <code>{user_id}</code>\n"
                f"📧 Email: {email or '—'}\n\n"
                f"{product['emoji']} <b>{product['name']}</b>\n"
                f"💵 Сумма: <b>{product['price']} ₽</b>\n"
                f"📅 Подписка: <b>{product['days']} дней</b>"
            )
            for admin_id in admin_ids:
                try:
                    await _bot.send_message(admin_id, admin_text)
                except Exception:
                    pass

    except Exception as e:
        logger.error("Webhook error: %s", e, exc_info=True)
        return web.Response(status=500)

    return web.Response(status=200)


async def start_webhook_server(bot, port: int = 8081) -> web.AppRunner:
    set_bot(bot)
    app = web.Application()
    app.router.add_post("/yookassa/webhook", handle_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logger.info("YooKassa webhook server listening on port %d", port)
    return runner
