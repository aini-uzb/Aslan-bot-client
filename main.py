"""
Doctor Aslan — Telegram-бот с подписками (30/90 дней),
автоудалением из каналов и напоминаниями.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, PRODUCTS
from handlers import router, channel_router, _admin_ids
from middleware import LoggingMiddleware
from database import init_db, get_expiring_soon, mark_notified, get_expired, deactivate_subscription, get_all_admin_ids
from keyboards import renewal_keyboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


async def subscription_checker(bot: Bot):
    """Фоновая задача: проверяет подписки каждый час."""
    while True:
        try:
            expiring = await get_expiring_soon(hours=24)
            for sub in expiring:
                product = PRODUCTS.get(sub["product_key"])
                if not product:
                    continue
                try:
                    await bot.send_message(
                        sub["user_id"],
                        f"⏰ <b>Подписка скоро заканчивается!</b>\n\n"
                        f"{product['emoji']} <b>{product['name']}</b>\n\n"
                        f"Ваш доступ истекает <b>завтра</b>.\n\n"
                        f"Хотите продлить подписку?\n\n"
                        f"Если не продлить — доступ к каналу "
                        f"будет закрыт автоматически.",
                        reply_markup=renewal_keyboard(sub["product_key"]),
                    )
                    logger.info("Renewal reminder sent: user=%s, product=%s", sub["user_id"], sub["product_key"])
                except Exception as e:
                    logger.warning("Failed to notify user=%s: %s", sub["user_id"], e)
                await mark_notified(sub["id"])

            expired = await get_expired()
            for sub in expired:
                product = PRODUCTS.get(sub["product_key"])
                if not product:
                    await deactivate_subscription(sub["id"])
                    continue

                chat_id = product.get("chat_id", 0)
                if chat_id:
                    try:
                        await bot.ban_chat_member(chat_id, sub["user_id"])
                        await bot.unban_chat_member(chat_id, sub["user_id"])
                        logger.info("Kicked user=%s from chat=%s", sub["user_id"], chat_id)
                    except Exception as e:
                        logger.warning("Failed to kick user=%s: %s", sub["user_id"], e)

                try:
                    await bot.send_message(
                        sub["user_id"],
                        f"🔒 <b>Подписка завершена</b>\n\n"
                        f"{product['emoji']} <b>{product['name']}</b>\n\n"
                        f"Ваш доступ закончился.\n"
                        f"Доступ к каналу закрыт.\n\n"
                        f"Хотите вернуться? Оформите подписку заново — "
                        f"мы всегда рады видеть вас снова! 🦷",
                        reply_markup=renewal_keyboard(sub["product_key"]),
                    )
                except Exception:
                    pass

                await deactivate_subscription(sub["id"])

        except Exception as e:
            logger.error("Subscription checker error: %s", e)

        await asyncio.sleep(3600)


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не задан! Проверьте файл .env")
        return

    await init_db()

    saved_admins = await get_all_admin_ids()
    _admin_ids.update(saved_admins)
    logger.info("Loaded %d admin IDs from DB: %s", len(saved_admins), saved_admins)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(LoggingMiddleware())
    dp.include_router(router)
    dp.include_router(channel_router)

    logger.info("🚀 Бот Doctor Aslan запущен!")

    asyncio.create_task(subscription_checker(bot))

    await dp.start_polling(
        bot,
        allowed_updates=["message", "callback_query", "channel_post"],
    )


if __name__ == "__main__":
    asyncio.run(main())
