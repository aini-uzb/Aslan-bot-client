"""
Пишет хештеги из постов во второй таблице cities того же bot.db, что использует Doctor Aslan.
Скопируйте этот файл во второй проект. Doctor Aslan менять не обязательно.

Перед запуском второго бота задайте переменную окружения:
  SHARED_CITIES_DB = полный путь к bot.db (например C:\\Users\\...\\бот\\bot.db)

Зависимости: aiosqlite
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import aiosqlite

# Путь к базе Doctor Aslan (обязательно задать, если файлы ботов в разных папках)
_DEFAULT_SIBLING = Path(__file__).resolve().parent.parent / "bot.db"
DB_PATH = Path(os.environ.get("SHARED_CITIES_DB", str(_DEFAULT_SIBLING))).resolve()


def normalize_city_key(s: str) -> str:
    """Должен совпадать с database.normalize_city_key в проекте Doctor Aslan."""
    if not s:
        return ""
    t = str(s).strip().lower().replace("ё", "е")
    t = re.sub(r"[\s\-_.,·]+", "", t)
    return t


def extract_hashtag_raw_tags(text: str | None) -> list[str]:
    """Сырой текст после # (как в Telegram), без дубликатов, порядок сохраняется."""
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for m in re.finditer(r"#([^\s#]+)", text):
        tag = m.group(1).strip()
        if tag and tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out


async def ensure_cities_table(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS cities (
            city TEXT PRIMARY KEY COLLATE NOCASE
        )
        """
    )
    await db.commit()


async def insert_city_key(key: str) -> None:
    """INSERT OR IGNORE одного нормализованного ключа."""
    k = normalize_city_key(key)
    if not k:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await ensure_cities_table(db)
        await db.execute("INSERT OR IGNORE INTO cities (city) VALUES (?)", (k,))
        await db.commit()


async def save_hashtags_from_text(text: str | None) -> int:
    """
    Разбирает #теги из текста/подписи, нормализует и пишет в cities.
    Возвращает число новых попыток вставки (дубликаты в БД игнорируются).
    """
    tags = extract_hashtag_raw_tags(text)
    if not tags:
        return 0
    count = 0
    async with aiosqlite.connect(DB_PATH) as db:
        await ensure_cities_table(db)
        for raw in tags:
            k = normalize_city_key(raw)
            if not k:
                continue
            await db.execute("INSERT OR IGNORE INTO cities (city) VALUES (?)", (k,))
            count += 1
        await db.commit()
    return count


# --- Пример для aiogram 3.x (вставьте в свой handlers второго бота) ---
#
# from aiogram import Router, F
# from aiogram.types import Message
# from city_writer import save_hashtags_from_text
#
# channel_router = Router()
#
# @channel_router.channel_post(F.text)
# async def on_channel_post_text(message: Message):
#     await save_hashtags_from_text(message.text)
#
# @channel_router.channel_post(F.caption)
# async def on_channel_post_caption(message: Message):
#     await save_hashtags_from_text(message.caption)
#
# # В dispatcher: dp.include_router(channel_router)
# # В allowed_updates добавьте channel_post
