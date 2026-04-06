"""
main.py

Lokal birlashgan rejim:
    python main.py

Render web xizmatida:
    gunicorn render_web:app --bind 0.0.0.0:$PORT --workers 2 --timeout 180
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time

from services.bootstrap import bootstrap_runtime, bootstrap_state

bootstrap_runtime()
bootstrap_state()

logger = logging.getLogger(__name__)

from bot.core import setup_bot
from services.cache_manager import cache_manager, safe_cleaner_worker
from services.settings_store import get_setting_value
from web.app import create_app


def _get_db_token() -> str | None:
    try:
        token = get_setting_value("bot_token")
        if token and ":" in token:
            return token
    except Exception:
        pass
    return os.getenv("BOT_TOKEN")


def _cleanup_temp_files(max_age_seconds: int = 86400) -> None:
    reports = {
        name: cache_manager.cleanup_directory(name, ttl_seconds=max_age_seconds)
        for name in cache_manager.policies
    }
    deleted = sum(report.deleted_files for report in reports.values())
    reclaimed_bytes = sum(report.reclaimed_bytes for report in reports.values())
    if deleted:
        logger.info(
            "trace=%s",
            {
                "event": "startup_cache_cleanup",
                "deleted_files": deleted,
                "reclaimed_bytes": reclaimed_bytes,
            },
        )


def _cleanup_loop() -> None:
    while True:
        time.sleep(6 * 3600)
        try:
            _cleanup_temp_files()
        except Exception as exc:
            logger.warning("Temp tozalash xatosi: %s", exc)


class _TokenChanged(Exception):
    pass


def run_bot() -> None:
    while True:
        try:
            bot, dp = setup_bot()
            current_token = _get_db_token() or ""
            logger.info("Telegram boti (polling) ulandi.")

            async def _run_with_token_watch():
                token_changed = asyncio.Event()

                async def _watch():
                    nonlocal current_token
                    while True:
                        await asyncio.sleep(30)
                        new_token = _get_db_token() or ""
                        if new_token and new_token != current_token:
                            logger.info("Token o'zgardi, bot qayta ulanmoqda...")
                            current_token = new_token
                            token_changed.set()
                            await dp.stop_polling()
                            return

                watch_task = asyncio.create_task(_watch())
                try:
                    try:
                        await bot.delete_webhook(drop_pending_updates=False)
                    except Exception as exc:
                        logger.warning("Webhook tozalash bajarilmadi: %s", exc)
                    await dp.start_polling(bot)
                finally:
                    watch_task.cancel()
                    try:
                        await bot.session.close()
                    except Exception:
                        pass
                if token_changed.is_set():
                    raise _TokenChanged("Token changed")

            asyncio.run(_run_with_token_watch())

        except _TokenChanged:
            logger.info("Yangi token bilan qayta ulanish...")
            time.sleep(2)
            continue
        except ValueError as exc:
            if "Token_Not_Found" in str(exc):
                logger.warning("Token topilmadi. 15 soniya kutilmoqda...")
            else:
                logger.error("Qiymat xatosi: %s", exc)
            time.sleep(15)
        except Exception as exc:
            logger.error("Bot xatosi: %s. Qayta ulanish...", exc)
            time.sleep(15)


WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
WEB_PORT = int(os.environ.get("PORT", 5000))


def run_bot_webhook() -> None:
    async def _start():
        try:
            from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
            from aiohttp import web as aio_web

            bot, dp = setup_bot()
            full_url = f"{WEBHOOK_URL.rstrip('/')}{WEBHOOK_PATH}"
            logger.info("Webhook sozlanmoqda: %s", full_url)

            await bot.set_webhook(
                url=full_url,
                secret_token=WEBHOOK_SECRET or None,
                drop_pending_updates=True,
            )

            aio_app = aio_web.Application()
            handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
                secret_token=WEBHOOK_SECRET or None,
            )
            handler.register(aio_app, path=WEBHOOK_PATH)
            setup_application(aio_app, dp, bot=bot)

            runner = aio_web.AppRunner(aio_app)
            await runner.setup()
            site = aio_web.TCPSite(runner, "0.0.0.0", WEB_PORT)
            await site.start()
            logger.info("Webhook server ishga tushdi: port %s", WEB_PORT)

            try:
                while True:
                    await asyncio.sleep(3600)
            finally:
                await runner.cleanup()
        except ImportError:
            logger.error("aiohttp o'rnatilmagan. pip install aiohttp")
        except Exception as exc:
            logger.error("Webhook xatosi: %s", exc)
            raise

    asyncio.run(_start())


def run_flask() -> None:
    app = create_app()
    logger.info("Flask admin paneli: http://0.0.0.0:%s", WEB_PORT)
    app.run(host="0.0.0.0", port=WEB_PORT, debug=False, use_reloader=False)


_started = False
_start_lock = threading.Lock()


def start_background_tasks(mode: str | None = None) -> None:
    global _started
    with _start_lock:
        if _started:
            return

        selected_mode = (mode or os.getenv("RUN_MODE", "combined")).strip().lower()
        logger.info("Background xizmatlarni boshlash: %s", selected_mode)
        cache_manager.ensure_directories()
        _cleanup_temp_files()
        safe_cleaner_worker.start()

        cleanup_thread = threading.Thread(
            target=_cleanup_loop,
            daemon=True,
            name="CacheCleanupThread",
        )
        cleanup_thread.start()

        if selected_mode == "web":
            _started = True
            return

        if selected_mode == "webhook":
            bot_thread = threading.Thread(
                target=run_bot_webhook,
                daemon=True,
                name="WebhookBotThread",
            )
        else:
            bot_thread = threading.Thread(
                target=run_bot,
                daemon=True,
                name="PollingBotThread",
            )

        bot_thread.start()
        _started = True


app = create_app()


if __name__ == "__main__":
    start_background_tasks(mode=os.getenv("RUN_MODE", "combined"))
    logger.info("Ilova ishga tushmoqda: http://0.0.0.0:%s", WEB_PORT)
    app.run(host="0.0.0.0", port=WEB_PORT, debug=False, use_reloader=False)
