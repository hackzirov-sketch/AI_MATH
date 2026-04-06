"""
services/key_manager.py
Groq (LLaMA) API kalitlarini saqlash, kvota tugaganda xavfsiz (rotation)
navbat bilan boshqasiga o'tkazish tizimi.
"""

from sqlalchemy.sql import func

from database.models import ApiKey, Log, get_session


def log_key_error(key_id, error_message):
    session = get_session()
    try:
        key = session.query(ApiKey).filter_by(id=key_id).first()
        if key:
            # Faqat qayta tiklab bo'lmaydigan xatolarda (401, 403) kalitni o'chiramiz.
            # 429 (Rate Limit) xatosi vaqtinchalik bo'lgani uchun uni o'chirmaymiz.
            if any(code in error_message for code in ("401", "403")) or "invalid" in error_message.lower():
                key.is_active = False

            # Loglarga yozamiz
            log = Log(
                level="ERROR",
                module="AI_KEY",
                message=f"Key {key_id} error: {error_message}",
            )
            session.add(log)
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def increment_key_usage(key_id):
    session = get_session()
    try:
        key = session.query(ApiKey).filter_by(id=key_id).first()
        if key:
            key.usage_count += 1
            key.last_used = func.now()
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def execute_with_rotation(prompt_func, *args, **kwargs):
    """
    Kiritilgan prompt xizmatini bajaradi.
    Ai_role yordamida prioritet ushlanadi.
    Xato bo'lsa (istalgan turdagi) keyingi kalitga o'tadi (rotation).
    """
    ai_role = kwargs.pop("ai_role", "quiz_gen")

    session = get_session()
    try:
        all_active = (
            session.query(ApiKey)
            .filter_by(is_active=True)
            .order_by(ApiKey.usage_count)
            .all()
        )
        # Keyinroq ishlatish uchun faqat kerakli ma'lumotlarni olamiz
        key_records = [
            {"id": k.id, "api_key": k.api_key, "service": k.service} for k in all_active
        ]
    finally:
        session.close()

    if not key_records:
        return None, "Bitta ham faol AI kaliti topilmadi."

    # Rolga qarab saralash (Priority Sorting)
    if ai_role == "image_gen":
        sorted_keys = [k for k in key_records if k["service"] == "huggingface"] + [
            k for k in key_records if k["service"] != "huggingface"
        ]
    elif ai_role == "title_gen":
        priority = ["openrouter", "groq"]
        sorted_keys = [k for k in key_records if k["service"] in priority] + [
            k for k in key_records if k["service"] not in priority
        ]
    else:  # quiz_gen
        fast_ones = ["cerebras", "sambanova", "groq"]
        sorted_keys = [k for k in key_records if k["service"] in fast_ones] + [
            k for k in key_records if k["service"] not in fast_ones
        ]

    last_error = "Barcha kalitlar ishlamadi yoki limit tugadi."

    for key_record in sorted_keys:
        api_key_str = key_record["api_key"]
        service = key_record["service"]
        key_id = key_record["id"]

        try:
            result = prompt_func(api_key_str, service, *args, **kwargs)
            increment_key_usage(key_id)
            return result, None

        except Exception as e:
            last_error = str(e)
            log_key_error(key_id, last_error)
            # Har qanday xatolikda keyingi kalitga o'tamiz (to'liq rotation)
            continue

    return None, last_error
