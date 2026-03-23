import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_USERNAMES = [
    x.strip().lower()
    for x in os.getenv("ADMIN_USERNAMES", "").split(",")
    if x.strip()
]

ADMIN_IDS_FIXED = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip() and x.strip() != "0"
]

# Юзернеймы для блока «Помощь» (без @). Если пусто — берём ADMIN_USERNAMES
_help_raw = os.getenv("HELP_CONTACT_USERNAMES", "").strip()
HELP_CONTACT_USERNAMES = [
    x.strip().lower()
    for x in _help_raw.split(",")
    if x.strip()
] or list(ADMIN_USERNAMES)

FREE_LESSON_LINK = os.getenv("FREE_LESSON_LINK", "")
FREE_LESSON_FILE_ID = os.getenv("FREE_LESSON_FILE_ID", "")
START_PHOTO_FILE_ID = os.getenv("START_PHOTO_FILE_ID", "")

CARD_NUMBER = os.getenv("CARD_NUMBER", "")
CARD_HOLDER = os.getenv("CARD_HOLDER", "")
CARD_BANK = os.getenv("CARD_BANK", "")

PRODUCTS = {
    "channel_30": {
        "name": "Закрытый канал — 30 дней",
        "emoji": "🔐",
        "price": 1500,
        "days": 30,
        "group": "channel",
        "invite_link": os.getenv("CHANNEL_INVITE_LINK", ""),
        "chat_id": int(os.getenv("CHANNEL_ID", "0") or "0"),
    },
    "channel_90": {
        "name": "Закрытый канал — 90 дней",
        "emoji": "🔐",
        "price": 3500,
        "days": 90,
        "group": "channel",
        "invite_link": os.getenv("CHANNEL_INVITE_LINK", ""),
        "chat_id": int(os.getenv("CHANNEL_ID", "0") or "0"),
    },
    "base_30": {
        "name": "База врачей — 30 дней",
        "emoji": "📋",
        "price": 500,
        "days": 30,
        "group": "base",
        "invite_link": os.getenv("BASE_INVITE_LINK", ""),
        "chat_id": int(os.getenv("BASE_CHANNEL_ID", "0") or "0"),
    },
    "base_90": {
        "name": "База врачей — 90 дней",
        "emoji": "📋",
        "price": 1000,
        "days": 90,
        "group": "base",
        "invite_link": os.getenv("BASE_INVITE_LINK", ""),
        "chat_id": int(os.getenv("BASE_CHANNEL_ID", "0") or "0"),
    },
}
