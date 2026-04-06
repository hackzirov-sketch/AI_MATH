from __future__ import annotations

from services.bootstrap import bootstrap_runtime, bootstrap_state

bootstrap_runtime()
bootstrap_state()

from web.app import create_app

app = create_app()
