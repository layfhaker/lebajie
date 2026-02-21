import asyncio
import logging
import os
from datetime import date

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from handlers import router
from database import init_db, get_all_objects, get_object_by_id, get_calendar_data_for_api

# Настройки логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === HTTP API ===

def add_cors_headers(response):
    """Добавить CORS-заголовки"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


async def handle_objects(request):
    """GET /api/objects — список всех объектов бронирования"""
    objects = get_all_objects()
    result = []
    for obj in objects:
        result.append({
            "id": obj["id"],
            "name": obj["name"],
            "category": obj["category"],
            "capacity": obj["capacity"],
            "price_weekday": obj["price_weekday"],
            "price_weekend": obj["price_weekend"],
            "description": obj["description"],
        })
    resp = web.json_response(result)
    return add_cors_headers(resp)


async def handle_calendar(request):
    """GET /api/calendar/{object_id}?month=YYYY-MM — календарь объекта"""
    try:
        object_id = int(request.match_info['object_id'])
    except (ValueError, KeyError):
        resp = web.json_response({"error": "Invalid object_id"}, status=400)
        return add_cors_headers(resp)

    obj = get_object_by_id(object_id)
    if not obj:
        resp = web.json_response({"error": "Object not found"}, status=404)
        return add_cors_headers(resp)

    month_param = request.query.get('month')
    if month_param:
        try:
            parts = month_param.split('-')
            year, month = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            resp = web.json_response({"error": "Invalid month format. Use YYYY-MM"}, status=400)
            return add_cors_headers(resp)
    else:
        today = date.today()
        year, month = today.year, today.month

    data = get_calendar_data_for_api(object_id, year, month)
    resp = web.json_response(data)
    return add_cors_headers(resp)


async def handle_options(request):
    """CORS preflight"""
    resp = web.Response()
    return add_cors_headers(resp)


async def start_api():
    """Запуск HTTP API сервера"""
    port_str = os.getenv("PORT", "8080")
    try:
        port = int(port_str)
    except ValueError:
        logger.warning("Некорректный PORT=%s, используется 8080", port_str)
        port = 8080

    app = web.Application()
    app.router.add_get('/api/objects', handle_objects)
    app.router.add_get('/api/calendar/{object_id}', handle_calendar)
    app.router.add_route('OPTIONS', '/api/objects', handle_options)
    app.router.add_route('OPTIONS', '/api/calendar/{object_id}', handle_options)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info("🌐 HTTP API запущен на порту %s", port)


async def main():
    # Проверка токена
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("⛔ Укажите BOT_TOKEN в файле config.py!")
        logger.error("   Получите токен у @BotFather в Telegram")
        return

    # Инициализация БД
    init_db()
    logger.info("✅ База данных инициализирована")

    # Создаем бота и диспетчер
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Подключаем роутеры
    dp.include_router(router)

    # Запуск API в фоне
    await start_api()

    # Запуск бота
    logger.info("🚀 Бот запущен...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
