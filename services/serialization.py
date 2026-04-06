from __future__ import annotations

import json
from typing import Any

try:
    import orjson
except Exception:
    orjson = None


def dumps(payload: Any) -> bytes:
    if orjson is not None:
        return orjson.dumps(payload)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def loads(raw: bytes | bytearray | memoryview | str) -> Any:
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if orjson is not None:
        return orjson.loads(raw)
    return json.loads(bytes(raw).decode("utf-8"))
