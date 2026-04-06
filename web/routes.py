"""
web/routes.py
"""

from datetime import datetime

from flask import flash, jsonify, redirect, render_template, request, url_for

from database.models import ApiKey, AutomationState, Log, Quiz, get_session
from services.settings_store import get_setting_int, get_setting_value, upsert_setting


def _clean_int_field(form, name: str, default: int, min_value: int, max_value: int) -> str:
    raw_value = (form.get(name, str(default)) or "").strip()
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} son bo'lishi kerak") from exc
    parsed = max(min_value, min(max_value, parsed))
    return str(parsed)


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
            api_keys = session.query(ApiKey).all()
        finally:
            session.close()

        return render_template(
            "settings.html",
            api_keys=api_keys,
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
