from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Awaitable


logger = logging.getLogger(__name__)


def configure_async_runtime() -> str:
    try:
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logger.info("Async runtime configured: uvloop")
        return "uvloop"
    except Exception:
        logger.info("Async runtime configured: default asyncio")
        return "asyncio"


def run_async_blocking(awaitable: Awaitable[Any]) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(awaitable)
        except BaseException as exc:
            error["value"] = exc

    thread = threading.Thread(target=_runner, daemon=True, name="ai_math_async_runner")
    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]
    return result.get("value")
