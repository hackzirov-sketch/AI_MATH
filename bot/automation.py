"""
bot/automation.py

Tuzatishlar:
- Barcha DB operatsiyalar sinxron yordamchi funksiyalarga ajratildi
- asyncio.to_thread orqali event loop bloklanmaydi
- datetime.utcnow() ga standartlashtirildi (now() bilan aralashma yo'q)
- F-string ichida backslash xatosi tuzatildi
- Quiz topilmasa callback_query.answer() chaqiriladi (spinner qolmaydi)
- Session leak yo'q: har bir sinxron funksiyada try/finally ishlatildi
"""

import asyncio
import html
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Router, types
from aiogram.enums import PollType
from aiogram.exceptions import TelegramBadRequest

from database.models import (
    AudiencePoll,
    AutomationState,
    QuizTypePoll,
    get_session,
)
from services.settings_store import get_setting_int, get_setting_value

automation_router = Router()
logger = logging.getLogger(__name__)

DEFAULT_AGE_POLL_WAIT_MINUTES = 3
DEFAULT_TYPE_POLL_WAIT_MINUTES = 3
DEFAULT_IDLE_HOURS = 6
DEFAULT_BATCH_COUNT = 10
DEFAULT_DURATION_MINUTES = 30


async def _safe_callback_answer(
    callback_query: types.CallbackQuery,
    text: str,
    show_alert: bool = False,
) -> None:
    try:
        await callback_query.answer(text, show_alert=show_alert)
    except TelegramBadRequest as exc:
        message = str(exc).lower()
        if "query is too old" in message or "query id is invalid" in message or "response timeout expired" in message:
            logger.info("Eskirgan callback javobi o'tkazildi: %s", exc)
            return
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Sinxron DB yordamchi funksiyalari
# Bular to'g'ridan-to'g'ri chaqirilmaydi — asyncio.to_thread orqali ishlatiladi
# ─────────────────────────────────────────────────────────────────────────────


def get_target_channel() -> str | None:
    """Kanalning Telegram ID/username sini DB dan qaytaradi."""
    return get_setting_value("channel_id")


def _sync_get_setting_int(
    key: str, default: int, min_value: int, max_value: int
) -> int:
    return get_setting_int(key, default, min_value, max_value)


def _sync_get_generation_settings() -> dict:
    return {
        "age_poll_wait": _sync_get_setting_int(
            "age_poll_wait_minutes",
            DEFAULT_AGE_POLL_WAIT_MINUTES,
            1,
            30,
        ),
        "type_poll_wait": _sync_get_setting_int(
            "type_poll_wait_minutes",
            DEFAULT_TYPE_POLL_WAIT_MINUTES,
            1,
            30,
        ),
        "idle_hours": _sync_get_setting_int(
            "cycle_idle_hours", DEFAULT_IDLE_HOURS, 1, 24
        ),
        "quiz_batch_count": _sync_get_setting_int(
            "quiz_batch_count", DEFAULT_BATCH_COUNT, 1, 30
        ),
        "quiz_duration_minutes": _sync_get_setting_int(
            "quiz_duration_minutes",
            DEFAULT_DURATION_MINUTES,
            5,
            180,
        ),
    }


def _sync_has_open_polls() -> bool:
    session = get_session()
    try:
        age_open = session.query(AudiencePoll).filter_by(is_closed=False).first()
        type_open = session.query(QuizTypePoll).filter_by(is_closed=False).first()
        return bool(age_open or type_open)
    finally:
        session.close()


def _sync_get_quiz_for_appeal(quiz_id: int) -> dict | None:
    from database.models import Quiz

    session = get_session()
    try:
        quiz = session.query(Quiz).filter_by(id=quiz_id).first()
        if not quiz:
            return None
        return {
            "id": quiz.id,
            "topic": quiz.topic or "Aralash",
            "quiz_type": quiz.quiz_type,
            "age_group": quiz.age_group,
            "question_text": quiz.question_text,
            "chat_id": quiz.chat_id,
            "message_id": quiz.message_id,
        }
    finally:
        session.close()


def _sync_expire_quizzes() -> list[tuple]:
    """
    Vaqti o'tgan faol quizlarni is_active=False qiladi.
    Qaytaradi: [(chat_id, message_id), ...] — markup o'chirish kerak bo'lganlar.
    """
    from database.models import Quiz

    session = get_session()
    try:
        now_utc = datetime.utcnow()
        active = session.query(Quiz).filter(Quiz.is_active == True).all()
        expired = []
        for q in active:
            duration = (
                q.duration_minutes if getattr(q, "duration_minutes", None) else 30
            )
            if q.created_at and q.created_at <= now_utc - timedelta(minutes=duration):
                q.is_active = False
                if q.chat_id and q.message_id:
                    expired.append((q.chat_id, q.message_id))
        session.commit()
        return expired
    except Exception as e:
        session.rollback()
        logger.warning("_sync_expire_quizzes xatosi: %s", e)
        return []
    finally:
        session.close()


def _sync_get_pending_action() -> str | None:
    """
    Avtomatsiya navbatdagi qadamini tekshiradi.
    Qaytaradi: qadam nomi yoki None (hech narsa qilish shart emas).
    """
    session = get_session()
    try:
        state = session.query(AutomationState).first()
        if (
            state
            and state.is_active
            and state.next_run
            and datetime.utcnow() >= state.next_run
        ):
            return state.current_step
        return None
    finally:
        session.close()


def _sync_set_next_run_minutes(minutes: int) -> None:
    """next_run ni hozirdan 'minutes' daqiqa keyinga belgilaydi."""
    session = get_session()
    try:
        state = session.query(AutomationState).first()
        if state:
            state.next_run = datetime.utcnow() + timedelta(minutes=minutes)
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def _sync_save_audience_poll(poll_id: str, message_id: int) -> None:
    """AudiencePoll yozuvini saqlaydi va holatni WAITING_AGE_POLL ga o'tkazadi."""
    session = get_session()
    try:
        wait_minutes = _sync_get_setting_int(
            "age_poll_wait_minutes",
            DEFAULT_AGE_POLL_WAIT_MINUTES,
            1,
            30,
        )
        session.add(AudiencePoll(poll_id=poll_id, message_id=message_id))
        state = session.query(AutomationState).first()
        if not state:
            state = AutomationState(is_active=True)
            session.add(state)
        state.current_step = "WAITING_AGE_POLL"
        state.next_run = datetime.utcnow() + timedelta(minutes=wait_minutes)
        session.commit()
    except Exception as exc:
        session.rollback()
        raise RuntimeError("Audience poll saqlanmadi") from exc
    finally:
        session.close()


def _sync_get_open_audience_poll() -> dict | None:
    """Ochiq (yopilmagan) so'nggi AudiencePoll ni dict sifatida qaytaradi."""
    session = get_session()
    try:
        poll = (
            session.query(AudiencePoll)
            .filter_by(is_closed=False)
            .order_by(AudiencePoll.id.desc())
            .first()
        )
        if poll:
            return {"id": poll.id, "message_id": poll.message_id}
        return None
    finally:
        session.close()


def _sync_close_age_poll_save_type_poll(
    age_poll_id: int,
    winning_age: str,
    type_poll_id: str,
    type_msg_id: int,
) -> None:
    """
    Yosh pollini yopadi, QuizTypePoll ni saqlaydi,
    holatni WAITING_TYPE_POLL ga o'tkazadi.
    """
    session = get_session()
    try:
        wait_minutes = _sync_get_setting_int(
            "type_poll_wait_minutes",
            DEFAULT_TYPE_POLL_WAIT_MINUTES,
            1,
            30,
        )
        age_poll = session.query(AudiencePoll).filter_by(id=age_poll_id).first()
        if age_poll:
            age_poll.is_closed = True
            age_poll.winning_age_group = winning_age
        session.add(
            QuizTypePoll(
                poll_id=type_poll_id,
                message_id=type_msg_id,
                target_age_group=winning_age,
            )
        )
        state = session.query(AutomationState).first()
        if state:
            state.current_step = "WAITING_TYPE_POLL"
            state.next_run = datetime.utcnow() + timedelta(minutes=wait_minutes)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def _sync_get_open_type_poll() -> dict | None:
    """Ochiq QuizTypePoll ni dict sifatida qaytaradi."""
    session = get_session()
    try:
        poll = (
            session.query(QuizTypePoll)
            .filter_by(is_closed=False)
            .order_by(QuizTypePoll.id.desc())
            .first()
        )
        if poll:
            return {
                "id": poll.id,
                "message_id": poll.message_id,
                "target_age_group": poll.target_age_group,
            }
        return None
    finally:
        session.close()


def _sync_close_type_poll_set_idle(type_poll_id: int, winning_type: str) -> str:
    """
    Tur pollini yopadi, IDLE holatiga o'tadi (keyingi sikl 4 soatdan keyin).
    Qaytaradi: winning_age (quiz generatsiyasi uchun kerak).
    """
    session = get_session()
    try:
        idle_hours = _sync_get_setting_int(
            "cycle_idle_hours",
            DEFAULT_IDLE_HOURS,
            1,
            24,
        )
        type_poll = session.query(QuizTypePoll).filter_by(id=type_poll_id).first()
        winning_age = "O'rta (Standard)"
        if type_poll:
            type_poll.is_closed = True
            type_poll.winning_quiz_type = winning_type
            winning_age = type_poll.target_age_group or winning_age
        state = session.query(AutomationState).first()
        if state:
            state.current_step = "IDLE"
            state.next_run = datetime.utcnow() + timedelta(hours=idle_hours)
        session.commit()
        return winning_age
    except Exception:
        session.rollback()
        return "O'rta (Standard)"
    finally:
        session.close()


def _sync_process_quiz_answer(
    user_id: int,
    username: str,
    full_name: str,
    quiz_id: int,
    chosen_idx: int,
) -> dict:
    """
    Quiz javobini DB da qayta ishlaydi.
    Qaytaradi: natijani ifodalovchi dict.
    Mumkin kalidlar:
      already_answered, quiz_not_found, quiz_inactive  — xato holatlari
      is_correct, points, score, rank_title, display_name,
      correct_letter, explanation               — muvaffaqiyatli holat
    """
    from database.models import Quiz, QuizResult, User

    session = get_session()
    try:
        # Foydalanuvchini topish yoki yaratish
        usr = session.query(User).filter_by(telegram_id=user_id).first()
        if not usr:
            usr = User(
                telegram_id=user_id,
                username=username,
                display_name=full_name,
            )
            session.add(usr)
            session.flush()

        # Takroriy javobni tekshirish
        if session.query(QuizResult).filter_by(user_id=usr.id, quiz_id=quiz_id).first():
            return {"already_answered": True}

        # Quizni topish
        quiz = session.query(Quiz).filter_by(id=quiz_id).first()
        if not quiz:
            return {"quiz_not_found": True}

        # Vaqti tugaganini tekshirish
        if not getattr(quiz, "is_active", True):
            return {"quiz_inactive": True}

        # Javobni hisoblash
        is_correct = quiz.correct_option_index == chosen_idx
        points = 10 if is_correct else 0

        if is_correct:
            usr.score += points
            usr.correct_answers += 1
        else:
            usr.incorrect_answers += 1

        # Unvonni yangilash
        score = usr.score
        if score > 1000:
            usr.rank_title = "🏆 Matematika Qiroli"
        elif score > 500:
            usr.rank_title = "👑 Eng Zukkosi (Daho)"
        elif score > 200:
            usr.rank_title = "🦸‍♂️ Matematik Titan"
        elif score > 100:
            usr.rank_title = "🌟 Algebra Ustasi"
        elif score > 50:
            usr.rank_title = "🚀 Yosh Olim"
        elif score > 20:
            usr.rank_title = "💡 Boshqotirma Bilg'ichi"
        elif not usr.rank_title:
            usr.rank_title = "Tirishqoq O'quvchi"

        session.add(
            QuizResult(
                user_id=usr.id,
                quiz_id=quiz_id,
                chosen_option_index=chosen_idx,
                is_correct=is_correct,
                points_earned=points,
            )
        )
        session.commit()

        letters = ["A", "B", "C", "D"]
        correct_letter = (
            letters[quiz.correct_option_index] if quiz.correct_option_index < 4 else "A"
        )

        return {
            "is_correct": is_correct,
            "points": points,
            "score": usr.score,
            "rank_title": usr.rank_title,
            "display_name": usr.display_name or full_name,
            "correct_letter": correct_letter,
            "explanation": quiz.explanation or "",
        }

    except Exception as e:
        session.rollback()
        raise RuntimeError(f"DB xatosi: {e}") from e
    finally:
        session.close()


# ─────────────────────────────────────────────────────────────────────────────
# Asosiy async funksiyalar
# ─────────────────────────────────────────────────────────────────────────────


async def automation_background_task(bot: Bot) -> None:
    """
    Har 15 soniyada tizim holatini tekshiradi.
    Barcha DB operatsiyalar asyncio.to_thread orqali — event loop bloklanmaydi.
    """
    while True:
        try:
            # 1. Vaqti o'tgan quizlarni sinxron tekshirish (thread ichida)
            expired_list: list[tuple] = await asyncio.to_thread(_sync_expire_quizzes)

            # 2. Vaqti o'tgan quizlar inline markup ini o'chirish (async Telegram API)
            for raw_chat_id, message_id in expired_list:
                try:
                    chat_id = raw_chat_id
                    if not (
                        str(chat_id).startswith("-100") or str(chat_id).startswith("@")
                    ):
                        try:
                            chat_id = int(chat_id)
                        except (ValueError, TypeError):
                            pass
                    await bot.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=message_id,
                        reply_markup=None,
                    )
                except Exception:
                    pass  # Allaqachon o'chirilgan yoki xato — davom etamiz

            # 3. Keyingi qadamni aniqlash (thread ichida)
            step: str | None = await asyncio.to_thread(_sync_get_pending_action)

            # 4. Kerakli qadamni bajarish
            if step == "WAITING_AGE_POLL":
                await _process_age_poll_step(bot)
            elif step == "WAITING_TYPE_POLL":
                await _process_type_poll_step(bot)
            elif step in ("IDLE", "STARTING_NEW_CYCLE"):
                success = await send_age_poll(bot)
                if not success:
                    # Kanal topilmadi — 1 daqiqadan keyin qayta urinib ko'rish
                    await asyncio.to_thread(_sync_set_next_run_minutes, 1)

        except Exception as e:
            logger.exception("Avtomatlashtirish fon xatosi: %s", e)

        await asyncio.sleep(15)


async def send_age_poll(bot: Bot) -> bool:
    """
    1-qadam: Qiyinlik darajasi so'rovnomasini kanalga yuboradi.
    Qaytaradi: True — muvaffaqiyatli, False — kanal topilmadi.
    """
    channel_id = await asyncio.to_thread(get_target_channel)
    if not channel_id:
        return False
    has_open_polls = await asyncio.to_thread(_sync_has_open_polls)
    if has_open_polls:
        return True

    msg = await bot.send_poll(
        chat_id=channel_id,
        question="O'quv soati! Keyingi quiz qaysi QIYINLIK darajasida bo'lsin?",
        options=[
            "Oson (Boshlang'ich)",
            "O'rta (Standard)",
            "Qiyin (Murakkab)",
            "Akademik (Olimpiada)",
        ],
        is_anonymous=True,
        type=PollType.REGULAR,
        allows_multiple_answers=False,
    )

    try:
        await asyncio.to_thread(_sync_save_audience_poll, msg.poll.id, msg.message_id)
    except Exception as exc:
        logger.exception("Audience poll holatini saqlash xatosi: %s", exc)
        try:
            await bot.stop_poll(chat_id=channel_id, message_id=msg.message_id)
        except Exception:
            pass
        return False
    return True


async def _process_age_poll_step(bot: Bot) -> None:
    """
    2-qadam: Qiyinlik pollini yopib, fan turi so'rovnomasini yuboradi.
    """
    channel_id = await asyncio.to_thread(get_target_channel)
    poll_entry = await asyncio.to_thread(_sync_get_open_audience_poll)

    if not channel_id:
        return

    winning_age = "O'rta (Standard)"

    if poll_entry:
        try:
            poll_msg = await bot.stop_poll(
                chat_id=channel_id, message_id=poll_entry["message_id"]
            )
            if poll_msg.options:
                winner = max(poll_msg.options, key=lambda o: o.voter_count)
                if winner.voter_count > 0:
                    winning_age = winner.text
        except Exception as e:
            logger.warning("Poll stop xatosi (Qiyinlik): %s", e)

    msg = await bot.send_poll(
        chat_id=channel_id,
        question=f"Qiyinlik: {winning_age}.\nQaysi sohaga e'tibor qaratamiz?",
        options=[
            "Algebra / Matematika",
            "Geometriya",
            "Boshqotirma",
            "Mantiqiy fikrlash",
            "IQ / Tanqidiy fikrlash",
            "Prezident maktabi",
        ],
        is_anonymous=True,
        type=PollType.REGULAR,
        allows_multiple_answers=False,
    )

    if poll_entry:
        await asyncio.to_thread(
            _sync_close_age_poll_save_type_poll,
            poll_entry["id"],
            winning_age,
            msg.poll.id,
            msg.message_id,
        )


async def _process_type_poll_step(bot: Bot) -> None:
    """
    3-qadam: Fan turi pollini yopib, quiz generatsiyasini boshlaydi.
    """
    channel_id = await asyncio.to_thread(get_target_channel)
    type_poll = await asyncio.to_thread(_sync_get_open_type_poll)

    winning_type = "Algebra / Matematika"

    if type_poll and channel_id:
        try:
            poll_msg = await bot.stop_poll(
                chat_id=channel_id, message_id=type_poll["message_id"]
            )
            if poll_msg.options:
                winner = max(poll_msg.options, key=lambda o: o.voter_count)
                if winner.voter_count > 0:
                    winning_type = winner.text
        except Exception:
            pass

    winning_age = "O'rta (Standard)"
    if type_poll:
        winning_age = await asyncio.to_thread(
            _sync_close_type_poll_set_idle, type_poll["id"], winning_type
        )

    if channel_id:
        try:
            from services.ai_generator import trigger_quiz_generation

            runtime = await asyncio.to_thread(_sync_get_generation_settings)

            asyncio.create_task(
                trigger_quiz_generation(
                    bot,
                    channel_id,
                    winning_age,
                    winning_type,
                    count=runtime["quiz_batch_count"],
                    duration_minutes=runtime["quiz_duration_minutes"],
                )
            )
        except ImportError:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Aiogram handler lari
# ─────────────────────────────────────────────────────────────────────────────


@automation_router.poll()
async def poll_handler(poll: types.Poll) -> None:
    """Telegram poll yangilanishlarini qabul qiladi (hozircha faqat log)."""
    pass


@automation_router.callback_query(lambda c: c.data and c.data.startswith("ans_"))
async def process_quiz_answer(callback_query: types.CallbackQuery) -> None:
    """Foydalanuvchi quiz variantini tanlagan vaqtda ishga tushadi."""

    parts = callback_query.data.split("_")
    if len(parts) != 3:
        await _safe_callback_answer(callback_query, "⚠️ Noto'g'ri ma'lumot formati.", show_alert=True)
        return

    try:
        quiz_id = int(parts[1])
        chosen_idx = int(parts[2])
    except ValueError:
        await _safe_callback_answer(callback_query, "⚠️ Xato format.", show_alert=True)
        return

    user = callback_query.from_user

    # DB ni alohida thread da qayta ishlash — event loop bloklanmaydi
    try:
        result = await asyncio.to_thread(
            _sync_process_quiz_answer,
            user.id,
            user.username or "",
            user.full_name,
            quiz_id,
            chosen_idx,
        )
    except Exception as e:
        logger.exception("process_quiz_answer DB xatosi: %s", e)
        await _safe_callback_answer(callback_query, "⚠️ Server xatosi, qayta urining!", show_alert=True)
        return

    # Xato holatlari — foydalanuvchiga xabar berish (spinner qolmasin)
    if result.get("already_answered"):
        await _safe_callback_answer(
            callback_query,
            "⚠️ Siz allaqachon javob bergansiz!", show_alert=True
        )
        return

    if result.get("quiz_not_found"):
        await _safe_callback_answer(callback_query, "⚠️ Quiz topilmadi.", show_alert=True)
        return

    if result.get("quiz_inactive"):
        await _safe_callback_answer(
            callback_query,
            "⏱ Vaqti tugadi — javob qabul qilinmaydi!", show_alert=True
        )
        return

    is_correct = result["is_correct"]
    points = result["points"]
    display_name = result["display_name"]
    correct_letter = result["correct_letter"]
    explanation = result["explanation"]

    # AI orqali ixtiyoriy tabrik/dalda xabari
    ai_msg = ""
    try:
        from services.ai_generator import run_ai_title_generation
        from services.key_manager import execute_with_rotation

        ai_result, ai_err = await asyncio.to_thread(
            execute_with_rotation,
            run_ai_title_generation,
            result["score"],
            result["rank_title"],
            display_name,
            is_correct,
            ai_role="title_gen",
        )
        if not ai_err and ai_result:
            ai_msg = str(ai_result)[:150]
    except Exception:
        pass  # AI xatosi — oddiy xabar bilan davom etamiz

    # F-string ichida apostrof muammosi yo'q bo'lishi uchun avvaldan belgilaymiz
    if is_correct:
        fallback = f"Barakalla, {display_name}!"
        msg = (
            f"✅ {ai_msg if ai_msg else fallback}\n"
            f"(+{points} ball). Umumiy: {result['score']} ball."
        )
    else:
        fallback = f"Xato! To'g'ri javob: {correct_letter}"
        msg = f"❌ {ai_msg if ai_msg else fallback}\nIzoh: {explanation[:50]}..."

    await _safe_callback_answer(callback_query, msg[:200], show_alert=True)


@automation_router.callback_query(lambda c: c.data and c.data.startswith("appeal_"))
async def process_quiz_appeal(callback_query: types.CallbackQuery) -> None:
    parts = callback_query.data.split("_")
    if len(parts) != 2:
        await _safe_callback_answer(callback_query, "⚠️ Apelatsiya ma'lumoti xato.", show_alert=True)
        return

    try:
        quiz_id = int(parts[1])
    except ValueError:
        await _safe_callback_answer(callback_query, "⚠️ Quiz ID noto'g'ri.", show_alert=True)
        return

    teacher_setting = await asyncio.to_thread(get_setting_value, "teacher_username")
    if not teacher_setting:
        await _safe_callback_answer(callback_query, "⚠️ O'qituvchi hali sozlanmagan.", show_alert=True)
        return

    from aiogram.enums import ParseMode
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from services.ai_generator import (
        _build_telegram_message_link,
        _normalize_teacher_chat_id,
        _split_teacher_targets,
    )

    teacher_targets = _split_teacher_targets(teacher_setting)
    teacher_chat_id = _normalize_teacher_chat_id(teacher_targets[0]) if teacher_targets else None
    if not teacher_chat_id or isinstance(teacher_chat_id, str):
        await _safe_callback_answer(
            callback_query,
            "⚠️ O'qituvchi uchun Telegram ID saqlang. Username bilan avtomatik yuborish kafolatlanmaydi.",
            show_alert=True,
        )
        return

    quiz_payload = await asyncio.to_thread(_sync_get_quiz_for_appeal, quiz_id)
    if not quiz_payload:
        await _safe_callback_answer(callback_query, "⚠️ Quiz topilmadi.", show_alert=True)
        return

    post_link = _build_telegram_message_link(quiz_payload.get("chat_id"), int(quiz_payload.get("message_id") or 0))
    if not post_link:
        await _safe_callback_answer(callback_query, "⚠️ Quiz posti linki topilmadi.", show_alert=True)
        return

    user = callback_query.from_user
    user_name = user.full_name or user.username or str(user.id)
    topic = html.escape(str(quiz_payload.get("topic") or "Aralash"))
    quiz_type = html.escape(str(quiz_payload.get("quiz_type") or "Quiz"))
    age_group = html.escape(str(quiz_payload.get("age_group") or "-"))
    question_preview = html.escape(str(quiz_payload.get("question_text") or "").strip()[:280])

    teacher_text = (
        "Assalomu aleykum ustoz shu savolni tushuntirib bera olsaizmi iltimos.\n\n"
        f"👤 <b>Foydalanuvchi:</b> {html.escape(user_name)}\n"
        f"🆔 <b>Quiz ID:</b> <code>{quiz_payload['id']}</code>\n"
        f"📘 <b>Mavzu:</b> {topic}\n"
        f"🎯 <b>Tur:</b> {quiz_type}\n"
        f"👥 <b>Yosh guruhi:</b> {age_group}\n\n"
        f"❓ <b>Savol:</b>\n{question_preview}\n\n"
        f"🔗 <b>Quiz posti:</b> {html.escape(post_link)}"
    )

    teacher_builder = InlineKeyboardBuilder()
    teacher_builder.button(text="🔗 Quiz postini ochish", url=post_link)
    teacher_builder.adjust(1)

    try:
        await callback_query.bot.send_message(
            chat_id=teacher_chat_id,
            text=teacher_text,
            parse_mode=ParseMode.HTML,
            reply_markup=teacher_builder.as_markup(),
            disable_web_page_preview=True,
        )
        await _safe_callback_answer(callback_query, "✅ O'qituvchiga apelatsiya yuborildi.", show_alert=True)
    except Exception as exc:
        logger.warning("Apelatsiya yuborilmadi: quiz_id=%s reason=%s", quiz_id, exc)
        await _safe_callback_answer(
            callback_query,
            "⚠️ O'qituvchiga xabar yuborilmadi. Ustoz botni ochgan va ID bilan saqlangan bo'lishi kerak.",
            show_alert=True,
        )
