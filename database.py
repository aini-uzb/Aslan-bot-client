"""
Города из канала «База врачей»:

Пользователь пишет город обычным текстом («Санкт Петербург»). Бот переводит это в тот же
ключ, что и у хештега в посте без символа # (санктпетербург ↔ #санктпетербург).

Хештеги из новых постов канала попадают в таблицу cities (обработчик channel_post).
Telegram не даёт боту «поиск по каналу» задним числом — только индекс при публикации
и ручное /addcity у админов.
"""
import re
import aiosqlite
import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "bot.db"


def normalize_city_key(s: str) -> str:
    """Нормализация строки как у хештега: без пробелов/дефисов, нижний регистр."""
    if not s:
        return ""
    t = str(s).strip().lower().replace("ё", "е")
    t = re.sub(r"[\s\-_.,·]+", "", t)
    return t


def city_text_to_hashtag_key(name: str) -> str:
    """
    Название города от пользователя → ключ как у хештега в канале (без #).
    «Москва» → москва, «Санкт-Петербург» → санктпетербург — то же, что #москва / #санктпетербург.
    """
    return normalize_city_key(name)


# Подписи для ответа пользователю (ключ = normalize_city_key)
KNOWN_CITY_LABELS: dict[str, str] = {
    "санктпетербург": "Санкт-Петербург",
    "москва": "Москва",
    "казань": "Казань",
    "екатеринбург": "Екатеринбург",
    "нижнийновгород": "Нижний Новгород",
    "новосибирск": "Новосибирск",
    "ростовнадону": "Ростов-на-Дону",
    "самара": "Самара",
    "краснодар": "Краснодар",
    "уфа": "Уфа",
    "воронеж": "Воронеж",
    "пермь": "Пермь",
    "волгоград": "Волгоград",
    "красноярск": "Красноярск",
    "саратов": "Саратов",
    "тюмень": "Тюмень",
    "тольятти": "Тольятти",
    "барнаул": "Барнаул",
    "омск": "Омск",
    "челябинск": "Челябинск",
}

# Синонимы ввода → канонический ключ в базе
CITY_ALIASES: dict[str, str] = {
    "спб": "санктпетербург",
    "питер": "санктпетербург",
    "петербург": "санктпетербург",
    "мск": "москва",
}


def city_display_name(city_key: str) -> str:
    k = normalize_city_key(city_key)
    return KNOWN_CITY_LABELS.get(k, city_key.title())


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_key TEXT NOT NULL,
                started_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                notified INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS known_admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                added_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cities (
                city TEXT PRIMARY KEY COLLATE NOCASE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                step TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await db.commit()

async def upsert_user(user_id: int, username: str, step: str):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT step FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET username = ?, step = ?, updated_at = ? WHERE user_id = ?",
                (username or "", step, now, user_id)
            )
        else:
            await db.execute(
                "INSERT INTO users (user_id, username, step, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, username or "", step, now, now)
            )
        await db.commit()

async def get_statistics() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0] if cursor else 0
        
        cursor = await db.execute("SELECT step, COUNT(*) FROM users GROUP BY step")
        rows = await cursor.fetchall()
        steps_counts = {r[0]: r[1] for r in rows}
        
        cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM subscriptions")
        buyers = (await cursor.fetchone())[0] if cursor else 0

        return {
            "total_users": total_users,
            "steps": steps_counts,
            "buyers": buyers
        }



async def save_admin(user_id: int, username: str = ""):
    now = datetime.datetime.now(datetime.timezone.utc)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO known_admins (user_id, username, added_at) "
            "VALUES (?, ?, ?)",
            (user_id, username, now.isoformat()),
        )
        await db.commit()


async def get_all_admin_ids() -> set[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM known_admins")
        rows = await cursor.fetchall()
        return {row[0] for row in rows}


async def add_subscription(user_id: int, product_key: str, days: int = 30):
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(days=days)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET is_active = 0 "
            "WHERE user_id = ? AND product_key = ? AND is_active = 1",
            (user_id, product_key),
        )
        await db.execute(
            "INSERT INTO subscriptions (user_id, product_key, started_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, product_key, now.isoformat(), expires.isoformat()),
        )
        await db.commit()


async def get_expiring_soon(hours: int = 24):
    """Подписки, которые истекают в ближайшие N часов и ещё не уведомлены."""
    now = datetime.datetime.now(datetime.timezone.utc)
    threshold = now + datetime.timedelta(hours=hours)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM subscriptions "
            "WHERE is_active = 1 AND notified = 0 AND expires_at <= ?",
            (threshold.isoformat(),),
        )
        return await cursor.fetchall()


async def mark_notified(sub_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET notified = 1 WHERE id = ?", (sub_id,)
        )
        await db.commit()


async def get_expired():
    """Подписки, которые уже истекли."""
    now = datetime.datetime.now(datetime.timezone.utc)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM subscriptions "
            "WHERE is_active = 1 AND expires_at <= ?",
            (now.isoformat(),),
        )
        return await cursor.fetchall()


async def deactivate_subscription(sub_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET is_active = 0 WHERE id = ?", (sub_id,)
        )
        await db.commit()


async def add_city(city: str):
    key = normalize_city_key(city)
    if not key:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO cities (city) VALUES (?)",
            (key,),
        )
        await db.commit()


async def get_all_cities() -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT city FROM cities ORDER BY city")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def find_city(query: str) -> str | None:
    """
    Есть ли в базе город: сравниваем ключ из текста пользователя с ключами хештегов из канала.
    Возвращает запись из БД при совпадении, иначе None → ответ «нет в базе».
    """
    qk = city_text_to_hashtag_key(query)
    if not qk:
        return None

    cities = await get_all_cities()

    for c in cities:
        if normalize_city_key(c) == qk:
            return c

    if qk in CITY_ALIASES:
        target = CITY_ALIASES[qk]
        for c in cities:
            if normalize_city_key(c) == target:
                return c

    if len(qk) >= 5:
        for c in cities:
            cn = normalize_city_key(c)
            if qk in cn:
                return c

    if len(qk) >= 8:
        for c in cities:
            cn = normalize_city_key(c)
            if len(cn) >= 5 and cn in qk:
                return c

    q_loose = query.strip().lower().replace("ё", "е")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT city FROM cities WHERE city LIKE ?", (f"%{q_loose}%",)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def has_active_subscription(user_id: int, product_key: str) -> bool:
    now = datetime.datetime.now(datetime.timezone.utc)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM subscriptions "
            "WHERE user_id = ? AND product_key = ? AND is_active = 1 AND expires_at > ?",
            (user_id, product_key, now.isoformat()),
        )
        row = await cursor.fetchone()
        return row[0] > 0
