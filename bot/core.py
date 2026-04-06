import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

# logging.basicConfig main.py da sozlangan — bu yerda ikki marta chaqirilmaydi
logger = logging.getLogger(__name__)


def get_proxy():
    try:
        from services.settings_store import get_setting_value

        db_proxy = get_setting_value("proxy_url")
        if db_proxy:
            return db_proxy
    except Exception:
        pass
    return os.getenv("PROXY_URL")


def get_bot_token():
    # Baza yoxud .env dan tokenni o'qish imkoni
    try:
        from services.settings_store import get_setting_value

        db_token = get_setting_value("bot_token")
        if db_token and ":" in db_token:
            return db_token
    except Exception:
        pass

    # Endi soxta token yo'q! Agar token topilmasa None qaytadi.
    return os.getenv("BOT_TOKEN")


def setup_bot():
    """Bot va Dispatcher'ni sozlash hamda routerlarni ulash"""
    token = get_bot_token()

    if not token or ":" not in token:
        raise ValueError("Token_Not_Found")

    proxy = get_proxy()
    session = None
    if proxy:
        logger.info(f"Botga proxy o'rnatilmoqda: {proxy}")
        session = AiohttpSession(proxy=proxy)

    bot = Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Handlers ulanadi
    from .automation import automation_background_task, automation_router
    from .handlers.admin import admin_router
    from .handlers.custom_quiz import custom_quiz_router
    from .handlers.user import user_router
    from .handlers.test_generator import test_router
    from services.daily_math_content import run_daily_scheduled_task

    dp.include_router(test_router)
    dp.include_router(custom_quiz_router)
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(automation_router)

    # DP startup orqali background State-Machine task ishga tushadi
    @dp.startup()
    async def on_startup(dispatcher, bot):
        import asyncio

        asyncio.create_task(automation_background_task(bot))
        asyncio.create_task(run_daily_scheduled_task(bot))

    return bot, dp
