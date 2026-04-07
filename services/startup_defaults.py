from __future__ import annotations

import os
import re

from database.models import ApiKey, get_session
from services.settings_store import get_setting_value, upsert_setting


def _split_values(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    parts = re.split(r"[\r\n,;]+", str(raw_value))
    return [part.strip() for part in parts if part.strip()]


def _get_env_value(*keys: str) -> str:
    for key in keys:
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def _seed_setting(env_value: str, setting_key: str, description: str) -> None:
    if not env_value:
        return
    upsert_setting(setting_key, env_value, description=description)


def _seed_admin_ids(env_value: str) -> None:
    if not env_value:
        return
    existing_values = _split_values(get_setting_value("admin_ids", "") or "")
    merged_values = []
    seen: set[str] = set()
    for value in _split_values(env_value) + existing_values:
        if value in seen:
            continue
        seen.add(value)
        merged_values.append(value)
    upsert_setting(
        "admin_ids",
        ",".join(merged_values),
        description="Admin Telegram ID ro'yxati",
    )


def _seed_api_keys() -> None:
    service_env_map = {
        "openrouter": ("OPENROUTER_API_KEYS", "OPENROUTER_API_KEY"),
        "cerebras": ("CEREBRAS_API_KEYS", "CEREBRAS_API_KEY"),
        "sambanova": ("SAMBANOVA_API_KEYS", "SAMBANOVA_API_KEY"),
        "huggingface": ("HUGGINGFACE_API_KEYS", "HUGGINGFACE_API_KEY", "HF_TOKEN"),
        "groq": ("GROQ_API_KEYS", "GROQ_API_KEY"),
    }

    session = get_session()
    try:
        existing_rows = session.query(ApiKey).all()
        existing_keys = {(row.service, row.api_key): row for row in existing_rows}
        changed = False

        for service, env_names in service_env_map.items():
            raw_value = _get_env_value(*env_names)
            for api_key in _split_values(raw_value):
                row = existing_keys.get((service, api_key))
                if row is None:
                    row = ApiKey(service=service, api_key=api_key, is_active=True)
                    session.add(row)
                    existing_keys[(service, api_key)] = row
                    changed = True
                    continue
                if not row.is_active:
                    row.is_active = True
                    changed = True

        if changed:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def sync_startup_defaults() -> None:
    _seed_setting(
        _get_env_value("BOT_TOKEN"),
        "bot_token",
        "Telegram bot token",
    )
    _seed_admin_ids(_get_env_value("ADMIN_IDS"))
    _seed_setting(
        _get_env_value("TEACHER_USERNAME", "TEACHER_ID"),
        "teacher_username",
        "O'qituvchi username yoki ID",
    )
    _seed_setting(
        _get_env_value("CHANNEL_ID"),
        "channel_id",
        "Quiz yuboriladigan kanal",
    )
    _seed_api_keys()
