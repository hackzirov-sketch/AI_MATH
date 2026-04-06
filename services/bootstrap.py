from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

from services.observability_runtime import configure_observability
from services.runtime import configure_async_runtime


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"

_runtime_bootstrapped = False
_state_bootstrapped = False


def bootstrap_runtime() -> None:
    global _runtime_bootstrapped
    if _runtime_bootstrapped:
        return

    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(
                LOG_FILE,
                maxBytes=1_000_000,
                backupCount=5,
                encoding="utf-8",
            ),
        ],
        force=True,
    )

    configure_async_runtime()
    load_dotenv()
    configure_observability(logging.INFO)
    _configure_sentry()
    _runtime_bootstrapped = True


def bootstrap_state() -> None:
    global _state_bootstrapped
    if _state_bootstrapped:
        return

    from database.models import init_db
    from services.cache_manager import cache_manager

    init_db()
    cache_manager.ensure_directories()
    _state_bootstrapped = True


def _configure_sentry() -> None:
    logger = logging.getLogger(__name__)
    sentry_dsn = os.getenv("SENTRY_DSN", "").strip()
    if not sentry_dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=0.2,
            environment=os.getenv("ENVIRONMENT", "production"),
        )
        logger.info("Sentry monitoring ulandi.")
    except ImportError:
        logger.warning("sentry-sdk o'rnatilmagan. pip install sentry-sdk")
