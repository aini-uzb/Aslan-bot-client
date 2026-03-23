# Второй бот → таблица `cities` (Doctor Aslan ничего менять не нужно)

## Условие

Оба бота должны использовать **один и тот же файл** `bot.db` от Doctor Aslan  
(полный путь, например `C:\Users\samad\Desktop\бот\bot.db`).

## Что сделать

1. Скопируйте файл **`city_writer.py`** в папку второго бота (рядом с `main.py` или в пакет).
2. Установите переменную окружения **`SHARED_CITIES_DB`** — абсолютный путь к `bot.db` первого бота.  
   В PowerShell перед запуском:
   ```powershell
   $env:SHARED_CITIES_DB = "C:\Users\samad\Desktop\бот\bot.db"
   ```
   Или пропишите в `.env` второго бота (если используете `python-dotenv`):
   ```
   SHARED_CITIES_DB=C:\Users\samad\Desktop\бот\bot.db
   ```
3. Во втором боте в обработчике постов канала вызывайте `await save_hashtags_from_text(message.text)`  
   (и при необходимости для подписей к фото — `message.caption`).

Нормализация **такая же**, как в `database.py` Doctor Aslan (ключ без `#`, нижний регистр, без пробелов/дефисов).

## Если боты на разных серверах

Один файл `bot.db` на сетевой диск — слабый вариант. Лучше общая БД (PostgreSQL) и тогда уже нужна доработка Doctor Aslan под чтение оттуда.
