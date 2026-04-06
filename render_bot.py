from __future__ import annotations

import os

from services.bootstrap import bootstrap_runtime, bootstrap_state

bootstrap_runtime()
bootstrap_state()

from main import run_bot
from services.cache_manager import safe_cleaner_worker


if __name__ == "__main__":
    os.environ.setdefault("RUN_MODE", "bot")
    safe_cleaner_worker.start()
    run_bot()
