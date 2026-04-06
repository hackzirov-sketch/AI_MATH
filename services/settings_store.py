"""
services/settings_store.py

DB dagi settings bilan ishlash uchun kichik helperlar.
"""

from database.models import Setting, get_session


def get_setting_value(key: str, default: str | None = None) -> str | None:
    session = get_session()
    try:
        row = session.query(Setting).filter_by(key=key).first()
        if row and row.value not in (None, ""):
            return str(row.value)
        return default
    finally:
        session.close()


def get_setting_int(key: str, default: int, min_value: int | None = None, max_value: int | None = None) -> int:
    raw = get_setting_value(key)
    if raw is None:
        return default
    try:
        value = int(str(raw).strip())
    except ValueError:
        return default
    if min_value is not None:
        value = max(min_value, value)
    if max_value is not None:
        value = min(max_value, value)
    return value


def upsert_setting(key: str, value: str, description: str | None = None) -> None:
    session = get_session()
    try:
        setting = session.query(Setting).filter_by(key=key).first()
        if not setting:
            setting = Setting(key=key)
            session.add(setting)
        setting.value = value
        if description is not None:
            setting.description = description
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
