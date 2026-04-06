"""
bot/handlers/admin.py

Admin buyruqlari va boshqaruv tugmalari.
"""

import asyncio
import os
from datetime import datetime, timedelta

from aiogram import F, Router, types
from aiogram.enums import PollType
from aiogram.filters import Command, CommandStart, Filter, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy import func

from database.models import (
    ApiKey,
    AudiencePoll,
    AutomationState,
    Quiz,
    QuizTypePoll,
    User,
    get_session,
)
from services.settings_store import get_setting_int, get_setting_value, upsert_setting

admin_router = Router()

BTN_QUIZ = "Tezkor quiz"
BTN_CUSTOM_QUIZ = "Maxsus quiz"
BTN_AGE_POLL = "Qiyinlik so'rovi"
BTN_TYPE_POLL = "Fan so'rovi"
BTN_STATS = "Statistika"
BTN_RANKING = "Reyting"
BTN_TOP10 = "Top 10"
BTN_WEEKLY = "Haftalik reyting"
BTN_SETTINGS = "Sozlamalar"
BTN_HELP = "Yordam"
BTN_SET_CHANNEL = "Kanal sozlash"
BTN_SET_TEACHER = "Ustoz sozlash"
BTN_TEST_AI = "AI test"
BTN_AI_TEST_GEN = "AI Test Generator"
BTN_KIDS = "Boshlang'ich"
BTN_MID = "O'rta"
BTN_ACADEMIC = "Akademik"
BTN_GEOMETRY = "Geometriya"
BTN_PUZZLE = "Boshqotirma"
BTN_LOGIC = "Mantiq"
BTN_IQ = "IQ / Tanqidiy"
BTN_PRESIDENT = "Prezident maktabi"
BTN_AUTO_START = "Avto start"
BTN_AUTO_STOP = "Avto stop"
BTN_CANCEL = "Bekor qilish"
BTN_SEND_CONTENT = "Ma'lumot yuborish"

DEFAULT_AGE = "10-13 yosh"
DEFAULT_TYPE = "Algebra / Matematika"


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


def _get_admin_ids() -> list[str]:
    env_ids = _split_csv(os.getenv("ADMIN_IDS", ""))
    db_ids = _split_csv(get_setting_value("admin_ids", ""))
    return _unique_items(env_ids + db_ids)


class IsAdmin(Filter):
    async def __call__(self, message: types.Message) -> bool:
        return str(message.from_user.id) in _get_admin_ids()


def is_admin(user_id: int) -> bool:
    """Sinxron joylar uchun admin tekshiruvi."""
    return str(user_id) in _get_admin_ids()


def _save_setting(key: str, value: str, description: str | None = None) -> None:
    upsert_setting(key, value, description=description)


def _get_default_settings() -> dict[str, str]:
    return {
        "channel_id": get_setting_value("channel_id", "") or "",
        "teacher_username": get_setting_value("teacher_username", "")
        or "Saydullaxojayev_AAA",
        "default_age_group": get_setting_value("default_age_group", DEFAULT_AGE)
        or DEFAULT_AGE,
        "default_quiz_type": get_setting_value("default_quiz_type", DEFAULT_TYPE)
        or DEFAULT_TYPE,
    }


def _get_runtime_settings() -> dict[str, int]:
    return {
        "age_poll_wait": get_setting_int("age_poll_wait_minutes", 3, 1, 30),
        "type_poll_wait": get_setting_int("type_poll_wait_minutes", 3, 1, 30),
        "cycle_idle_hours": get_setting_int("cycle_idle_hours", 6, 1, 24),
        "quiz_batch_count": get_setting_int("quiz_batch_count", 10, 1, 30),
        "quiz_duration_minutes": get_setting_int("quiz_duration_minutes", 30, 5, 180),
    }


def get_admin_keyboard():
    """Admin uchun ixcham va tushunarli menyu."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        types.KeyboardButton(text=BTN_QUIZ),
        types.KeyboardButton(text=BTN_CUSTOM_QUIZ),
    )
    builder.row(
        types.KeyboardButton(text=BTN_AGE_POLL),
        types.KeyboardButton(text=BTN_TYPE_POLL),
    )
    builder.row(
        types.KeyboardButton(text=BTN_STATS),
        types.KeyboardButton(text=BTN_RANKING),
    )
    builder.row(
        types.KeyboardButton(text=BTN_TOP10),
        types.KeyboardButton(text=BTN_WEEKLY),
    )
    builder.row(
        types.KeyboardButton(text=BTN_KIDS),
        types.KeyboardButton(text=BTN_MID),
        types.KeyboardButton(text=BTN_ACADEMIC),
    )
    builder.row(
        types.KeyboardButton(text=BTN_GEOMETRY),
        types.KeyboardButton(text=BTN_PUZZLE),
        types.KeyboardButton(text=BTN_LOGIC),
    )
    builder.row(
        types.KeyboardButton(text=BTN_IQ),
        types.KeyboardButton(text=BTN_PRESIDENT),
    )
    builder.row(
        types.KeyboardButton(text=BTN_SETTINGS),
        types.KeyboardButton(text=BTN_HELP),
    )
    builder.row(
        types.KeyboardButton(text=BTN_SET_CHANNEL),
        types.KeyboardButton(text=BTN_SET_TEACHER),
    )
    builder.row(
        types.KeyboardButton(text=BTN_TEST_AI),
        types.KeyboardButton(text=BTN_AI_TEST_GEN),
    )
    builder.row(
        types.KeyboardButton(text=BTN_AUTO_START),
        types.KeyboardButton(text=BTN_AUTO_STOP),
    )
    builder.row(
        types.KeyboardButton(text=BTN_SEND_CONTENT),
    )
    builder.row(types.KeyboardButton(text=BTN_CANCEL))
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Bo'limni tanlang",
    )


@admin_router.message(Command("cancel"), IsAdmin())
@admin_router.message(F.text == BTN_CANCEL, IsAdmin())
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Joriy amal bekor qilindi.", reply_markup=get_admin_keyboard())


@admin_router.message(CommandStart(), IsAdmin())
async def cmd_start(message: types.Message):
    await message.answer(
        "Assalomu alaykum, admin.\nKerakli bo'limni menyudan tanlang.",
        reply_markup=get_admin_keyboard(),
    )


@admin_router.message(Command("yordam"), IsAdmin())
@admin_router.message(F.text == BTN_HELP, IsAdmin())
async def cmd_help(message: types.Message):
    await message.answer(
        "<b>Admin menyusi</b>\n\n"
        f"{BTN_QUIZ} yoki /quiz - 1 ta tezkor quiz yuborish\n"
        f"{BTN_CUSTOM_QUIZ} yoki /custom_quiz - parametrli quiz yaratish\n"
        f"{BTN_AGE_POLL} yoki /qiyinlik_poll - qiyinlik bo'yicha so'rov\n"
        f"{BTN_TYPE_POLL} yoki /tur_poll - fan bo'yicha so'rov\n"
        f"{BTN_STATS} yoki /statistika - tizim statistikasi\n"
        f"{BTN_RANKING} yoki /reyting - umumiy reyting\n"
        f"{BTN_TOP10} yoki /top10 - eng yaxshi 10 talik\n"
        f"{BTN_WEEKLY} yoki /haftalik_reyting - haftalik reyting\n\n"
        "<b>Standart parametrlar</b>\n"
        f"{BTN_KIDS} / {BTN_MID} / {BTN_ACADEMIC} - yosh guruhi\n"
        f"{BTN_GEOMETRY} / {BTN_PUZZLE} / {BTN_LOGIC} / {BTN_IQ} / {BTN_PRESIDENT} - fan turi\n\n"
        f"<b>Sozlash</b>\n"
        f"{BTN_SET_CHANNEL} yoki /kanal_ornat @kanal\n"
        f"{BTN_SET_TEACHER} yoki /oqituvchi_ornat @username\n"
        f"{BTN_TEST_AI} yoki /test_ai - AI sinovi\n"
        f"/kalitlarni_tiklash - Barcha AI kalitlarini faollashtirish\n"
        f"{BTN_AUTO_START} yoki /avto_boshlash - avtomatlashtirishni yoqish\n"
        f"{BTN_AUTO_STOP} yoki /avto_tugatish - avtomatlashtirishni to'xtatish\n"
        f"/iq yoki /prezident - standart mantiqiy yo'nalish tanlash",
        reply_markup=get_admin_keyboard(),
    )


@admin_router.message(Command("kanal_ornat"), IsAdmin())
@admin_router.message(F.text == BTN_SET_CHANNEL, IsAdmin())
async def cmd_set_channel(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) == 1 or message.text == BTN_SET_CHANNEL:
        await message.answer(
            "Kanalni ulash uchun quyidagicha yuboring:\n<code>/kanal_ornat @kanal_nomi</code>"
        )
        return

    channel_id = parts[1].strip()
    _save_setting("channel_id", channel_id, "Quiz yuboriladigan kanal")
    await message.answer(f"Kanal saqlandi: <code>{channel_id}</code>")


@admin_router.message(Command("admin_ornat"), IsAdmin())
async def cmd_set_admin(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) == 1:
        await message.answer("Namuna: <code>/admin_ornat 123456789</code>")
        return

    new_id = parts[1].strip()
    if not new_id.isdigit():
        await message.answer("Admin ID faqat raqamlardan iborat bo'lishi kerak.")
        return

    ids = _get_admin_ids()
    if new_id not in ids:
        ids.append(new_id)
        _save_setting("admin_ids", ",".join(ids), "Admin Telegram ID ro'yxati")

    await message.answer(f"{new_id} admin ro'yxatiga qo'shildi.")


@admin_router.message(Command("oqituvchi_ornat"), IsAdmin())
@admin_router.message(F.text == BTN_SET_TEACHER, IsAdmin())
async def cmd_set_teacher(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) == 1 or message.text == BTN_SET_TEACHER:
        await message.answer(
            "Ustozni saqlash uchun quyidagicha yuboring:\n"
            "<code>/oqituvchi_ornat telegram_id_yoki_username</code>\n\n"
            "Eng ishonchli variant: <b>telegram ID</b>."
        )
        return

    teacher_username = parts[1].strip()
    _save_setting("teacher_username", teacher_username, "O'qituvchi username yoki ID")
    await message.answer(f"Ustoz saqlandi: <code>{teacher_username}</code>")


@admin_router.message(Command("sozlamalar"), IsAdmin())
@admin_router.message(F.text == BTN_SETTINGS, IsAdmin())
async def cmd_settings(message: types.Message):
    session = get_session()
    try:
        state = session.query(AutomationState).first()
        active_keys = session.query(ApiKey).filter_by(is_active=True).count()
        total_keys = session.query(ApiKey).count()
    finally:
        session.close()

    defaults = _get_default_settings()
    runtime = _get_runtime_settings()
    auto_status = "Yoniq" if (state and state.is_active) else "O'chiq"
    step = (state.current_step if state else None) or "-"
    next_run = (
        state.next_run.strftime("%Y-%m-%d %H:%M:%S")
        if state and state.next_run
        else "Belgilanmagan"
    )

    await message.answer(
        "<b>Joriy sozlamalar</b>\n\n"
        f"Kanal: <code>{defaults['channel_id'] or 'Belgilanmagan'}</code>\n"
        f"Ustoz: <code>{defaults['teacher_username'] or 'Belgilanmagan'}</code>\n"
        f"Standart yosh guruhi: <b>{defaults['default_age_group']}</b>\n"
        f"Standart fan turi: <b>{defaults['default_quiz_type']}</b>\n"
        f"Avto holat: <b>{auto_status}</b>\n"
        f"Qadam: <code>{step}</code>\n"
        f"Keyingi ishga tushish: <code>{next_run}</code>\n"
        f"AI kalitlar: <b>{active_keys}/{total_keys}</b> faol\n\n"
        "<b>Sikl sozlamalari</b>\n"
        f"Qiyinlik poll kutishi: {runtime['age_poll_wait']} daqiqa\n"
        f"Fan poll kutishi: {runtime['type_poll_wait']} daqiqa\n"
        f"Sikllar oralig'i: {runtime['cycle_idle_hours']} soat\n"
        f"Bir siklda quiz soni: {runtime['quiz_batch_count']} ta\n"
        f"Quiz davomiyligi: {runtime['quiz_duration_minutes']} daqiqa"
    )


@admin_router.message(Command("quiz"), IsAdmin())
@admin_router.message(F.text == BTN_QUIZ, IsAdmin())
async def cmd_manual_quiz(message: types.Message):
    await message.answer("Quiz generatsiyasi boshlandi...")
    defaults = _get_default_settings()

    try:
        from bot.automation import get_target_channel
        from services.ai_generator import trigger_quiz_generation

        channel_id = get_target_channel() or message.chat.id
        asyncio.create_task(
            trigger_quiz_generation(
                message.bot,
                channel_id,
                defaults["default_age_group"],
                defaults["default_quiz_type"],
                count=1,
            )
        )
        await message.answer(
            "Yuborish navbatga qo'yildi.\n"
            f"Yosh guruhi: <b>{defaults['default_age_group']}</b>\n"
            f"Fan: <b>{defaults['default_quiz_type']}</b>"
        )
    except Exception as exc:
        await message.answer(f"Xatolik: {exc}")


@admin_router.message(Command("qiyinlik_poll"), IsAdmin())
@admin_router.message(F.text == BTN_AGE_POLL, IsAdmin())
async def cmd_age_poll(message: types.Message):
    from bot.automation import send_age_poll

    success = await send_age_poll(message.bot)
    if success:
        await message.answer("Qiyinlik so'rovnomasi yuborildi.")
    else:
        await message.answer(
            "Kanal belgilanmagan.\nAvval <code>/kanal_ornat @kanal_nomi</code> yuboring."
        )


@admin_router.message(Command("tur_poll"), IsAdmin())
@admin_router.message(F.text == BTN_TYPE_POLL, IsAdmin())
async def cmd_type_poll(message: types.Message):
    from bot.automation import get_target_channel

    channel_id = get_target_channel()
    if not channel_id:
        await message.answer(
            "Kanal belgilanmagan.\nAvval <code>/kanal_ornat @kanal_nomi</code> yuboring."
        )
        return

    session = get_session()
    try:
        last_poll = (
            session.query(AudiencePoll)
            .filter(AudiencePoll.winning_age_group.isnot(None))
            .order_by(AudiencePoll.id.desc())
            .first()
        )
        winning_age = last_poll.winning_age_group if last_poll else "O'rta"
    finally:
        session.close()

    msg = await message.bot.send_poll(
        chat_id=channel_id,
        question=f"Qiyinlik: {winning_age}\nQaysi yo'nalish bo'yicha quiz tayyorlaymiz?",
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

    session = get_session()
    try:
        session.add(
            QuizTypePoll(
                poll_id=msg.poll.id,
                message_id=msg.message_id,
                target_age_group=winning_age,
            )
        )
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

    await message.answer(
        f"Fan turi so'rovnomasi yuborildi. Qiyinlik: <b>{winning_age}</b>"
    )


@admin_router.message(Command("auditoriya_quiz"), IsAdmin())
async def cmd_audience_quiz(message: types.Message):
    await message.answer(
        "Maxsus parametrli quiz uchun /custom_quiz dan foydalaning.\n"
        "Standart /quiz uchun pastdagi yosh guruhi va fan tugmalaridan foydalanishingiz mumkin."
    )


@admin_router.message(Command("bolalar"), IsAdmin())
@admin_router.message(F.text == BTN_KIDS, IsAdmin())
async def cmd_level_kids(message: types.Message):
    _save_setting("default_age_group", "6-9 yosh", "Standart yosh guruhi")
    await message.answer("Standart yosh guruhi: <b>6-9 yosh</b>")


@admin_router.message(Command("orta"), IsAdmin())
@admin_router.message(F.text == BTN_MID, IsAdmin())
async def cmd_level_mid(message: types.Message):
    _save_setting("default_age_group", "10-13 yosh", "Standart yosh guruhi")
    await message.answer("Standart yosh guruhi: <b>10-13 yosh</b>")


@admin_router.message(Command("akademik"), IsAdmin())
@admin_router.message(F.text == BTN_ACADEMIC, IsAdmin())
async def cmd_level_academic(message: types.Message):
    _save_setting("default_age_group", "14+ yosh", "Standart yosh guruhi")
    await message.answer("Standart yosh guruhi: <b>14+ yosh (Akademik)</b>")


@admin_router.message(Command("geometriya"), IsAdmin())
@admin_router.message(F.text == BTN_GEOMETRY, IsAdmin())
async def cmd_type_geometry(message: types.Message):
    _save_setting("default_quiz_type", "Geometriya", "Standart quiz turi")
    await message.answer("Standart fan turi: <b>Geometriya</b>")


@admin_router.message(Command("boshqotirma"), IsAdmin())
@admin_router.message(F.text == BTN_PUZZLE, IsAdmin())
async def cmd_type_puzzle(message: types.Message):
    _save_setting("default_quiz_type", "Boshqotirma", "Standart quiz turi")
    await message.answer("Standart fan turi: <b>Boshqotirma</b>")


@admin_router.message(Command("mantiq"), IsAdmin())
@admin_router.message(F.text == BTN_LOGIC, IsAdmin())
async def cmd_type_logic(message: types.Message):
    _save_setting("default_quiz_type", "Mantiqiy fikrlash", "Standart quiz turi")
    await message.answer("Standart fan turi: <b>Mantiqiy fikrlash</b>")


@admin_router.message(Command("iq"), IsAdmin())
@admin_router.message(F.text == BTN_IQ, IsAdmin())
async def cmd_type_iq(message: types.Message):
    _save_setting("default_quiz_type", "IQ / Tanqidiy fikrlash", "Standart quiz turi")
    await message.answer("Standart fan turi: <b>IQ / Tanqidiy fikrlash</b>")


@admin_router.message(Command("prezident"), IsAdmin())
@admin_router.message(F.text == BTN_PRESIDENT, IsAdmin())
async def cmd_type_president(message: types.Message):
    _save_setting("default_quiz_type", "Prezident maktabi", "Standart quiz turi")
    await message.answer("Standart fan turi: <b>Prezident maktabi</b>")


@admin_router.message(Command("haftalik_reyting"), IsAdmin())
@admin_router.message(F.text == BTN_WEEKLY, IsAdmin())
async def cmd_admin_weekly(message: types.Message):
    from database.models import QuizResult

    session = get_session()
    try:
        week_ago = datetime.utcnow() - timedelta(days=7)
        rows = (
            session.query(
                User,
                func.sum(QuizResult.points_earned).label("weekly_score"),
                func.count(QuizResult.id).label("answers"),
            )
            .join(QuizResult, QuizResult.user_id == User.id)
            .filter(QuizResult.answered_at >= week_ago)
            .group_by(User.id)
            .order_by(func.sum(QuizResult.points_earned).desc())
            .limit(20)
            .all()
        )
    finally:
        session.close()

    if not rows:
        await message.answer("Bu hafta hali hech kim javob bermagan.")
        return

    medals = ["1-o'rin", "2-o'rin", "3-o'rin"]
    text = "<b>Haftalik reyting - Top 20</b>\n\n"
    for index, (user, weekly_score, answers) in enumerate(rows):
        medal = medals[index] if index < 3 else f"{index + 1}-o'rin"
        name = user.display_name or user.username or f"User#{user.telegram_id}"
        text += (
            f"{medal}: <b>{name}</b> - {int(weekly_score or 0)} ball "
            f"({int(answers or 0)} javob) | Jami: {user.score}\n"
        )

    await message.answer(text)


@admin_router.message(Command("reyting"), IsAdmin())
@admin_router.message(F.text == BTN_RANKING, IsAdmin())
async def cmd_ranking(message: types.Message):
    session = get_session()
    try:
        users = session.query(User).order_by(User.score.desc()).limit(20).all()
    finally:
        session.close()

    if not users:
        await message.answer("Hozircha reyting yo'q.")
        return

    text = "<b>Umumiy reyting - Top 20</b>\n\n"
    for index, user in enumerate(users, start=1):
        name = user.display_name or user.username or f"User#{user.telegram_id}"
        total = user.correct_answers + user.incorrect_answers
        pct = round(user.correct_answers / total * 100) if total > 0 else 0
        text += (
            f"{index}. {name} - <b>{user.score}</b> ball | "
            f"to'g'ri {user.correct_answers}, xato {user.incorrect_answers} ({pct}%)\n"
        )

    await message.answer(text)


@admin_router.message(Command("top10"), IsAdmin())
@admin_router.message(F.text == BTN_TOP10, IsAdmin())
async def cmd_top10(message: types.Message):
    session = get_session()
    try:
        top_users = session.query(User).order_by(User.score.desc()).limit(10).all()
    finally:
        session.close()

    if not top_users:
        await message.answer("Hozircha hech kim ball to'plamagan.")
        return

    text = "<b>Top 10 o'quvchilar</b>\n\n"
    for index, user in enumerate(top_users, start=1):
        name = user.display_name or user.username or f"User#{user.telegram_id}"
        text += (
            f"{index}. <b>{name}</b> - {user.score} ball <i>({user.rank_title})</i>\n"
        )

    await message.answer(text)


@admin_router.message(Command("statistika"), IsAdmin())
@admin_router.message(F.text == BTN_STATS, IsAdmin())
async def cmd_stats(message: types.Message):
    session = get_session()
    try:
        total_quizzes = session.query(Quiz).count()
        active_quizzes = session.query(Quiz).filter_by(is_active=True).count()
        total_users = session.query(User).count()
        state = session.query(AutomationState).first()
        active_keys = session.query(ApiKey).filter_by(is_active=True).count()
        total_keys = session.query(ApiKey).count()
    finally:
        session.close()

    auto_status = "Yoniq" if (state and state.is_active) else "O'chiq"
    channel_val = get_setting_value("channel_id", "") or "Belgilanmagan"
    defaults = _get_default_settings()

    await message.answer(
        "<b>Tizim statistikasi</b>\n\n"
        f"Jami quizlar: <b>{total_quizzes}</b>\n"
        f"Faol quizlar: <b>{active_quizzes}</b>\n"
        f"Foydalanuvchilar: <b>{total_users}</b>\n"
        f"Kanal: <code>{channel_val}</code>\n"
        f"Standart yosh: <b>{defaults['default_age_group']}</b>\n"
        f"Standart fan: <b>{defaults['default_quiz_type']}</b>\n"
        f"Avtomatlashtirish: <b>{auto_status}</b>\n"
        f"AI kalitlar: <b>{active_keys}/{total_keys}</b> faol"
    )


@admin_router.message(F.text == BTN_AI_TEST_GEN, IsAdmin())
async def cmd_ai_test_gen(message: types.Message):
    await message.answer(
        "📚 <b>AI Test Generator</b>\n\n"
        "Test yaratish uchun /test buyrug'ini yuboring yoki pastdagi tugmani bosing.\n\n"
        "Bu funksiya orqali:\n"
        "• Istalgan sinf uchun test yaratish\n"
        "• Qiyinlik darajasini tanlash\n"
        "• Savollar sonini belgilash\n"
        "• PDF formatda yuklab olish"
    )


BTN_START_TEST = "✅ Test yaratish"


@admin_router.message(F.text == BTN_AI_TEST_GEN)
async def cmd_ai_test_gen_user(message: types.Message, state: FSMContext):
    from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

    await state.clear()

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="1-sinf"),
                KeyboardButton(text="2-sinf"),
                KeyboardButton(text="3-sinf"),
            ],
            [
                KeyboardButton(text="4-sinf"),
                KeyboardButton(text="5-sinf"),
                KeyboardButton(text="6-sinf"),
            ],
            [
                KeyboardButton(text="7-sinf"),
                KeyboardButton(text="8-sinf"),
                KeyboardButton(text="9-sinf"),
            ],
            [KeyboardButton(text="10-sinf"), KeyboardButton(text="11-sinf")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(
        "📚 <b>AI Test Generator</b>\n\n"
        "1️⃣ <b>Sinfni tanlang</b> yoki raqam kiriting (1-11):",
        reply_markup=keyboard,
    )

    from bot.handlers.test_generator import TestGeneratorStates

    await state.set_state(TestGeneratorStates.waiting_for_grade)


@admin_router.message(Command("test_ai"), IsAdmin())
@admin_router.message(F.text == BTN_TEST_AI, IsAdmin())
async def cmd_test_ai(message: types.Message):
    await message.answer("AI sinovdan o'tkazilmoqda...")
    from services.ai_generator import run_ai_generation
    from services.key_manager import execute_with_rotation

    result, error = await asyncio.to_thread(
        execute_with_rotation,
        run_ai_generation,
        "10-13 yosh",
        "Algebra / Matematika",
        "test_001",
    )
    if error:
        await message.answer(f"AI xatoligi:\n{error}")
    else:
        await message.answer(
            "AI muvaffaqiyatli ishladi.\n\n"
            f"Savol: {str(result.get('question', '-'))[:200]}"
        )


@admin_router.message(Command("avto_boshlash"), IsAdmin())
@admin_router.message(F.text == BTN_AUTO_START, IsAdmin())
async def cmd_auto_start(message: types.Message):
    session = get_session()
    try:
        state = session.query(AutomationState).first()
        if not state:
            state = AutomationState(
                is_active=True,
                current_step="STARTING_NEW_CYCLE",
                next_run=datetime.utcnow(),
            )
            session.add(state)
        else:
            state.is_active = True
            state.current_step = "STARTING_NEW_CYCLE"
            state.next_run = datetime.utcnow()
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

    await message.answer("Avtomatlashtirish faollashtirildi.")


@admin_router.message(Command("kalitlarni_tiklash"), IsAdmin())
async def cmd_reset_keys(message: types.Message):
    session = get_session()
    try:
        updated = session.query(ApiKey).update({"is_active": True})
        session.commit()
        await message.answer(
            f"Barcha {updated} ta AI kalitlari faollashtirildi (is_active=True)."
        )
    except Exception as e:
        session.rollback()
        await message.answer(f"Xatolik: {e}")
    finally:
        session.close()


@admin_router.message(Command("avto_tugatish"), IsAdmin())
@admin_router.message(F.text == BTN_AUTO_STOP, IsAdmin())
async def cmd_auto_stop(message: types.Message):
    session = get_session()
    try:
        state = session.query(AutomationState).first()
        if state:
            state.is_active = False
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

    await message.answer("Avtomatlashtirish to'xtatildi.")


@admin_router.message(Command("malumot_yuborish"), IsAdmin())
@admin_router.message(F.text == BTN_SEND_CONTENT, IsAdmin())
async def cmd_send_content(message: types.Message):
    from services.daily_math_content import check_and_send_daily_content
    from services.settings_store import get_setting_value

    channel_id = get_setting_value("channel_id")
    if not channel_id:
        await message.answer("⚠️ Kanal ID si topilmadi. Avval kanalni sozlang.")
        return

    bot = message.bot
    success = await check_and_send_daily_content(bot, channel_id, force=True)
    if success:
        await message.answer("✅ Ma'lumot kanalga muvaffaqiyatli yuborildi!")
    else:
        await message.answer("❌ Ma'lumot yuborishda xatolik bo'ldi.")


@admin_router.message(Command("self_report"), IsAdmin())
async def cmd_self_report(message: types.Message):
    from services.self_improvement.engine import self_improvement_engine

    summary = self_improvement_engine.refresh_runtime_report(limit=150)
    top_proposal = summary.get("top_proposal") or {}
    weakest = summary.get("weakest_target") or "topilmadi"
    proposal_target = top_proposal.get("target", "taklif yo'q")
    confidence = float(top_proposal.get("confidence", 0.0) or 0.0)
    coverage_gaps = summary.get("coverage_gaps") or []
    gaps_text = ", ".join(str(item) for item in coverage_gaps[:3]) if coverage_gaps else "yo'q"

    await message.answer(
        "<b>Self-improvement hisoboti</b>\n\n"
        f"Eventlar: <b>{summary.get('event_count', 0)}</b>\n"
        f"Eng zaif yo'nalish: <b>{weakest}</b>\n"
        f"Top proposal: <b>{proposal_target}</b>\n"
        f"Ishonch: <b>{confidence:.2f}</b>\n"
        f"Coverage gap: <b>{gaps_text}</b>\n\n"
        "Batafsil fayl: <code>data/self_improvement/latest_runtime_report.json</code>",
        parse_mode="HTML",
    )


@admin_router.message(IsAdmin(), StateFilter(None))
async def admin_menu_fallback(message: types.Message):
    if message.text and message.text.startswith("/"):
        return
    await message.answer(
        "Bu bo'lim uchun tayyor tugmalardan birini tanlang yoki /yordam ni yuboring.",
        reply_markup=get_admin_keyboard(),
    )
