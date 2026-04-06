"""
bot/handlers/user.py

Foydalanuvchi uchun ochiq buyruqlar:
  /start
  /mening_natijam
  /haftalik_reyting
  /umumiy_reyting
"""

import asyncio
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func

from database.models import QuizResult, User, get_session

user_router = Router()


def _get_or_create_user(telegram_id: int, username: str, full_name: str) -> User:
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                display_name=full_name,
            )
            session.add(user)
            session.commit()
        return user
    finally:
        session.close()


def _progress_bar(correct: int, total: int, length: int = 10) -> str:
    """Oddiy progress bar, masalan: ████████░░ 80%"""
    if total == 0:
        return "░" * length + " 0%"
    filled = round(correct / total * length)
    pct = round(correct / total * 100)
    return "█" * filled + "░" * (length - filled) + f" {pct}%"


def _rank_emoji(rank: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")


def _build_start_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Mening natijam", callback_data="cmd_my_stats")
    builder.button(text="📅 Haftalik reyting", callback_data="cmd_weekly_ranking")
    builder.button(text="🏆 Umumiy reyting", callback_data="cmd_all_time_ranking")
    builder.adjust(2, 1)
    return builder.as_markup()


@user_router.message(CommandStart())
async def cmd_user_start(message: Message) -> None:
    """Yangi foydalanuvchini bazaga qo'shadi va start xabarini yuboradi."""
    user = await asyncio.to_thread(
        _get_or_create_user,
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name,
    )
    name = user.display_name or message.from_user.full_name

    await message.answer(
            f"👋 Assalomu alaykum, <b>{name}</b>!\n\n"
            "🧠 <b>AI Math Quiz</b> ga xush kelibsiz.\n\n"
            "Bu yerda siz matematik savollarga javob berib ball to'playsiz, "
            "natijangizni kuzatasiz va reytingda yuqoriga ko'tarilasiz.\n\n"
            "Quyidagi tugmalardan birini tanlang:",
            reply_markup=_build_start_keyboard(),
        )


def _sync_my_stats(telegram_id: int, username: str, full_name: str) -> dict:
    session = get_session()
    try:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                display_name=full_name,
            )
            session.add(user)
            session.commit()

        total = user.correct_answers + user.incorrect_answers
        pct = round(user.correct_answers / total * 100) if total > 0 else 0

        week_ago = datetime.utcnow() - timedelta(days=7)
        weekly_pts = (
            session.query(func.sum(QuizResult.points_earned))
            .filter(
                QuizResult.user_id == user.id,
                QuizResult.answered_at >= week_ago,
            )
            .scalar()
            or 0
        )

        rank_row = (
            session.query(func.count(User.id)).filter(User.score > user.score).scalar() or 0
        )
        rank_pos = rank_row + 1

        last_results = (
            session.query(QuizResult)
            .filter_by(user_id=user.id)
            .order_by(QuizResult.answered_at.desc())
            .limit(5)
            .all()
        )
        last_icons = "".join("✅" if result.is_correct else "❌" for result in reversed(last_results))

        return {
            "name": user.display_name or full_name,
            "score": user.score,
            "rank_title": user.rank_title or "Yangi boshlovchi",
            "correct": user.correct_answers,
            "incorrect": user.incorrect_answers,
            "total": total,
            "pct": pct,
            "weekly_pts": weekly_pts,
            "rank_pos": rank_pos,
            "last_icons": last_icons or "—",
            "progress": _progress_bar(user.correct_answers, total),
        }
    finally:
        session.close()


@user_router.message(Command("mening_natijam"))
async def cmd_my_stats(message: Message) -> None:
    await send_my_stats(message)


@user_router.callback_query(lambda callback: callback.data == "cmd_my_stats")
async def cb_my_stats(callback_query: CallbackQuery) -> None:
    await send_my_stats(callback_query.message, callback_query.from_user)
    await callback_query.answer()


async def send_my_stats(message: Message, user=None) -> None:
    tg_user = user or message.from_user
    data = await asyncio.to_thread(
        _sync_my_stats,
        tg_user.id,
        tg_user.username or "",
        tg_user.full_name,
    )

    text = (
        f"📊 <b>{data['name']} — shaxsiy statistika</b>\n"
        f"{'─' * 30}\n\n"
        f"🏅 <b>Unvon:</b> {data['rank_title']}\n"
        f"⭐ <b>Umumiy ball:</b> <b>{data['score']}</b>\n"
        f"📆 <b>Haftalik ball:</b> {data['weekly_pts']}\n"
        f"🌍 <b>Reyting o'rni:</b> #{data['rank_pos']}\n\n"
        f"✅ To'g'ri: {data['correct']} | ❌ Xato: {data['incorrect']}\n"
        f"📈 Aniqlik: {data['progress']}\n\n"
        f"🕓 So'nggi javoblar: {data['last_icons']}\n\n"
        "💡 Yangi savollarga javob berib natijangizni yaxshilang."
    )
    await message.answer(text)


def _sync_weekly_top(limit: int = 10) -> list[dict]:
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
            .limit(limit)
            .all()
        )

        result = []
        for user, weekly_score, answers in rows:
            result.append(
                {
                    "name": user.display_name or user.username or f"User#{user.telegram_id}",
                    "score": int(weekly_score or 0),
                    "answers": int(answers or 0),
                    "rank_title": user.rank_title or "—",
                }
            )
        return result
    finally:
        session.close()


@user_router.message(Command("haftalik_reyting"))
async def cmd_weekly_ranking(message: Message) -> None:
    await send_weekly_ranking(message)


@user_router.callback_query(lambda callback: callback.data == "cmd_weekly_ranking")
async def cb_weekly_ranking(callback_query: CallbackQuery) -> None:
    await send_weekly_ranking(callback_query.message)
    await callback_query.answer()


async def send_weekly_ranking(message: Message) -> None:
    rows = await asyncio.to_thread(_sync_weekly_top, 10)

    if not rows:
        await message.answer("📆 Bu hafta hali hech kim javob bermagan.\nBirinchi bo'ling!")
        return

    lines = ["📅 <b>Haftalik reyting (oxirgi 7 kun)</b>\n"]
    for index, row in enumerate(rows, start=1):
        lines.append(
            f"{_rank_emoji(index)} <b>{row['name']}</b> — "
            f"{row['score']} ball ({row['answers']} javob)\n"
            f"   <i>{row['rank_title']}</i>"
        )

    await message.answer("\n".join(lines))


def _sync_all_time_top(limit: int = 10) -> list[dict]:
    session = get_session()
    try:
        users = (
            session.query(User)
            .filter(User.score > 0)
            .order_by(User.score.desc())
            .limit(limit)
            .all()
        )
        result = []
        for user in users:
            total = user.correct_answers + user.incorrect_answers
            pct = round(user.correct_answers / total * 100) if total > 0 else 0
            result.append(
                {
                    "name": user.display_name or user.username or f"User#{user.telegram_id}",
                    "score": user.score,
                    "correct": user.correct_answers,
                    "pct": pct,
                    "rank_title": user.rank_title or "—",
                }
            )
        return result
    finally:
        session.close()


@user_router.message(Command("umumiy_reyting"))
async def cmd_all_time_ranking(message: Message) -> None:
    await send_all_time_ranking(message)


@user_router.callback_query(lambda callback: callback.data == "cmd_all_time_ranking")
async def cb_all_time_ranking(callback_query: CallbackQuery) -> None:
    await send_all_time_ranking(callback_query.message)
    await callback_query.answer()


async def send_all_time_ranking(message: Message) -> None:
    rows = await asyncio.to_thread(_sync_all_time_top, 10)

    if not rows:
        await message.answer("😕 Hali hech kim ball to'plamagan.\nBirinchi bo'lish uchun javob bering.")
        return

    lines = ["🏆 <b>Barcha vaqt reytingi (Top 10)</b>\n"]
    for index, row in enumerate(rows, start=1):
        lines.append(
            f"{_rank_emoji(index)} <b>{row['name']}</b> — "
            f"{row['score']} ball ✅{row['correct']} ({row['pct']}%)\n"
            f"   <i>{row['rank_title']}</i>"
        )

    await message.answer("\n".join(lines))
