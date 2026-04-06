"""
web/routes.py
"""

import os
from datetime import datetime

from flask import flash, jsonify, redirect, render_template, request, url_for

from database.models import ApiKey, AutomationState, Log, Quiz, User, get_session
from services.settings_store import get_setting_int, get_setting_value, upsert_setting


def _clean_int_field(form, name: str, default: int, min_value: int, max_value: int) -> str:
    raw_value = (form.get(name, str(default)) or "").strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} son bo'lishi kerak") from exc
    parsed = max(min_value, min(max_value, parsed))
    return str(parsed)


def _split_csv(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in str(raw_value).split(",") if item.strip()]


def _unique_items(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _normalize_telegram_id(raw_value: str | None) -> str:
    cleaned = (raw_value or "").strip()
    if not cleaned:
        raise ValueError("Telegram ID bo'sh bo'lishi mumkin emas")
    if cleaned.startswith("@"):
        raise ValueError("Admin qo'shish uchun username emas, Telegram ID kiriting")
    if not cleaned.isdigit():
        raise ValueError("Telegram ID faqat raqamlardan iborat bo'lishi kerak")
    normalized = str(int(cleaned))
    if not normalized:
        raise ValueError("Telegram ID noto'g'ri")
    return normalized


def _get_env_admin_ids() -> list[str]:
    return _split_csv(os.getenv("ADMIN_IDS", ""))


def _get_db_admin_ids() -> list[str]:
    return _split_csv(get_setting_value("admin_ids", "") or "")


def _save_admin_ids(admin_ids: list[str]) -> None:
    upsert_setting(
        "admin_ids",
        ",".join(_unique_items(admin_ids)),
        description="Admin Telegram ID ro'yxati",
    )


def _get_user_map(session, telegram_ids: list[str]) -> dict[str, User]:
    numeric_ids = [int(telegram_id) for telegram_id in telegram_ids if telegram_id.isdigit()]
    if not numeric_ids:
        return {}
    users = session.query(User).filter(User.telegram_id.in_(numeric_ids)).all()
    return {str(user.telegram_id): user for user in users}


def _build_admin_panel_data(session) -> dict[str, object]:
    env_admin_ids = _get_env_admin_ids()
    db_admin_ids = _get_db_admin_ids()
    effective_admin_ids = _unique_items(env_admin_ids + db_admin_ids)
    user_map = _get_user_map(session, effective_admin_ids)
    admin_rows = []

    for admin_id in effective_admin_ids:
        user = user_map.get(admin_id)
        source_parts = []
        if admin_id in env_admin_ids:
            source_parts.append("ENV")
        if admin_id in db_admin_ids:
            source_parts.append("DB")
        admin_rows.append(
            {
                "telegram_id": admin_id,
                "username": user.username if user and user.username else "",
                "display_name": user.display_name if user and user.display_name else "",
                "last_activity": user.last_activity if user else None,
                "is_env": admin_id in env_admin_ids,
                "is_db": admin_id in db_admin_ids,
                "can_remove": admin_id in db_admin_ids,
                "remove_keeps_env_access": admin_id in env_admin_ids and admin_id in db_admin_ids,
                "source_label": " + ".join(source_parts) if source_parts else "DB",
            }
        )

    recent_users = (
        session.query(User)
        .order_by(User.last_activity.desc(), User.created_at.desc())
        .limit(25)
        .all()
    )
    recent_user_rows = [
        {
            "telegram_id": str(user.telegram_id),
            "username": user.username or "",
            "display_name": user.display_name or "",
            "score": user.score,
            "last_activity": user.last_activity,
            "is_admin": str(user.telegram_id) in effective_admin_ids,
        }
        for user in recent_users
    ]

    return {
        "env_admin_ids": env_admin_ids,
        "db_admin_ids": db_admin_ids,
        "effective_admin_count": len(effective_admin_ids),
        "admin_rows": admin_rows,
        "recent_users": recent_user_rows,
    }


def setup_routes(app):
    @app.route("/health")
    def health():
        """Deployment monitoring uchun health check endpoint."""
        try:
            session = get_session()
            try:
                total_quizzes = session.query(Quiz).count()
                total_keys = session.query(ApiKey).filter_by(is_active=True).count()
            finally:
                session.close()

            return jsonify(
                {
                    "status": "ok",
                    "db": "connected",
                    "active_ai_keys": total_keys,
                    "total_quizzes": total_quizzes,
                }
            ), 200
        except Exception as exc:
            return jsonify({"status": "error", "detail": str(exc)}), 500

    @app.route("/")
    def index():
        session = get_session()
        try:
            total_quizzes = session.query(Quiz).count()
            logs = session.query(Log).order_by(Log.created_at.desc()).limit(15).all()
        finally:
            session.close()
        return render_template("index.html", total_quizzes=total_quizzes, logs=logs)

    @app.route("/settings")
    def settings():
        session = get_session()
        try:
            api_keys = session.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
            admin_panel_data = _build_admin_panel_data(session)
        finally:
            session.close()

        return render_template(
            "settings.html",
            api_keys=api_keys,
            **admin_panel_data,
            bot_token=get_setting_value("bot_token", "") or "",
            channel_id=get_setting_value("channel_id", "") or "",
            teacher_username=get_setting_value("teacher_username", "") or "Saydullaxojayev_AAA",
            age_poll_wait_minutes=get_setting_int("age_poll_wait_minutes", 3, 1, 30),
            type_poll_wait_minutes=get_setting_int("type_poll_wait_minutes", 3, 1, 30),
            cycle_idle_hours=get_setting_int("cycle_idle_hours", 6, 1, 24),
            quiz_batch_count=get_setting_int("quiz_batch_count", 10, 1, 30),
            quiz_duration_minutes=get_setting_int("quiz_duration_minutes", 30, 5, 180),
        )

    @app.route("/settings/save", methods=["POST"])
    def save_settings():
        try:
            upsert_setting("bot_token", request.form.get("bot_token", "").strip())
            upsert_setting("channel_id", request.form.get("channel_id", "").strip())
            upsert_setting("teacher_username", request.form.get("teacher_username", "").strip())
            upsert_setting(
                "age_poll_wait_minutes",
                _clean_int_field(request.form, "age_poll_wait_minutes", 3, 1, 30),
            )
            upsert_setting(
                "type_poll_wait_minutes",
                _clean_int_field(request.form, "type_poll_wait_minutes", 3, 1, 30),
            )
            upsert_setting(
                "cycle_idle_hours",
                _clean_int_field(request.form, "cycle_idle_hours", 6, 1, 24),
            )
            upsert_setting(
                "quiz_batch_count",
                _clean_int_field(request.form, "quiz_batch_count", 10, 1, 30),
            )
            upsert_setting(
                "quiz_duration_minutes",
                _clean_int_field(request.form, "quiz_duration_minutes", 30, 5, 180),
            )
        except Exception as exc:
            flash(f"Xatolik: {exc}", "danger")
            return redirect(url_for("settings"))

        flash("Sozlamalar saqlandi.", "success")
        return redirect(url_for("settings"))

    @app.route("/settings/admin/add", methods=["POST"])
    def add_admin():
        raw_admin_id = request.form.get("admin_telegram_id", "")
        try:
            admin_id = _normalize_telegram_id(raw_admin_id)
            env_admin_ids = _get_env_admin_ids()
            db_admin_ids = _get_db_admin_ids()
            if admin_id in db_admin_ids:
                flash("Bu Telegram ID allaqachon adminlar bazasida bor.", "warning")
            else:
                _save_admin_ids(db_admin_ids + [admin_id])
                if admin_id in env_admin_ids:
                    flash("Admin ID bazaga saqlandi. U allaqachon ENV orqali faol edi.", "info")
                else:
                    flash("Yangi admin qo'shildi.", "success")
        except Exception as exc:
            flash(f"Xatolik: {exc}", "danger")
        return redirect(url_for("settings"))

    @app.route("/settings/admin/remove/<admin_id>", methods=["POST"])
    def remove_admin(admin_id):
        try:
            normalized_admin_id = _normalize_telegram_id(admin_id)
            env_admin_ids = _get_env_admin_ids()
            db_admin_ids = _get_db_admin_ids()
            if normalized_admin_id not in db_admin_ids:
                if normalized_admin_id in env_admin_ids:
                    flash(
                        "Bu admin ENV orqali berilgan. Uni serverdagi ADMIN_IDS dan olib tashlash kerak.",
                        "warning",
                    )
                else:
                    flash("Admin topilmadi.", "warning")
            else:
                updated_admin_ids = [
                    current_admin_id
                    for current_admin_id in db_admin_ids
                    if current_admin_id != normalized_admin_id
                ]
                _save_admin_ids(updated_admin_ids)
                if normalized_admin_id in env_admin_ids:
                    flash(
                        "Admin DB ro'yxatidan olib tashlandi, lekin ENV sabab hali ham faol.",
                        "info",
                    )
                else:
                    flash("Admin ro'yxatdan olib tashlandi.", "success")
        except Exception as exc:
            flash(f"Xatolik: {exc}", "danger")
        return redirect(url_for("settings"))

    @app.route("/add_key", methods=["POST"])
    def add_key():
        new_key = request.form.get("api_key", "").strip()
        service = request.form.get("service", "groq").strip()

        if not new_key:
            flash("API kalit bo'sh bo'lishi mumkin emas.", "warning")
            return redirect(url_for("settings"))

        session = get_session()
        try:
            exists = session.query(ApiKey).filter_by(api_key=new_key).first()
            if exists:
                flash("Bu kalit allaqachon mavjud.", "warning")
            else:
                session.add(ApiKey(service=service, api_key=new_key, is_active=True))
                session.commit()
                flash("Yangi API kalit qo'shildi.", "success")
        except Exception as exc:
            session.rollback()
            flash(f"Xatolik: {exc}", "danger")
        finally:
            session.close()

        return redirect(url_for("settings"))

    @app.route("/delete_key/<int:key_id>", methods=["POST"])
    def delete_key(key_id):
        session = get_session()
        try:
            api_key = session.query(ApiKey).filter_by(id=key_id).first()
            if api_key:
                session.delete(api_key)
                session.commit()
                flash("API kalit o'chirildi.", "success")
            else:
                flash("Kalit topilmadi.", "warning")
        except Exception as exc:
            session.rollback()
            flash(f"Xatolik: {exc}", "danger")
        finally:
            session.close()

        return redirect(url_for("settings"))

    @app.route("/toggle_key/<int:key_id>")
    def toggle_key(key_id):
        session = get_session()
        try:
            api_key = session.query(ApiKey).filter_by(id=key_id).first()
            if api_key:
                api_key.is_active = not api_key.is_active
                session.commit()
                status = "YONIQ" if api_key.is_active else "O'CHIQ"
                flash(f"Kalit holati {status} ga o'zgardi.", "info")
            else:
                flash("Kalit topilmadi.", "warning")
        except Exception as exc:
            session.rollback()
            flash(f"Xatolik: {exc}", "danger")
        finally:
            session.close()

        return redirect(url_for("settings"))

    @app.route("/manual_trigger")
    def manual_trigger():
        """Avtomatlashtirish siklini qo'lda boshlaydi."""
        session = get_session()
        try:
            state = session.query(AutomationState).first()
            if not state:
                flash(
                    "Avtomatlashtirish hali sozlanmagan. Botda /avto_boshlash buyrug'ini bering.",
                    "warning",
                )
            elif not state.is_active:
                flash(
                    "Avtomatlashtirish o'chiq. Avval botda /avto_boshlash buyrug'ini bering.",
                    "warning",
                )
            else:
                state.current_step = "STARTING_NEW_CYCLE"
                state.next_run = datetime.utcnow()
                session.add(
                    Log(
                        level="INFO",
                        module="FLASK",
                        message="Yangi avtomatlashtirish sikli veb panel orqali qo'lda boshlandi.",
                    )
                )
                session.commit()
                flash(
                    "Yangi sikl boshlandi. Bot 15 soniya ichida so'rovnoma yuboradi.",
                    "success",
                )
        except Exception as exc:
            session.rollback()
            flash(f"Xatolik: {exc}", "danger")
        finally:
            session.close()

        return redirect(url_for("index"))
