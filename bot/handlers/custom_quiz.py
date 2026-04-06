"""
bot/handlers/custom_quiz.py
"""

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from .admin import BTN_CUSTOM_QUIZ, IsAdmin

custom_quiz_router = Router()

LEVEL_CHOICES = {
    "Oson (Boshlang'ich)": {
        "age_group": "6-9 yosh",
        "difficulty": "oson",
        "label": "Oson (Boshlang'ich)",
    },
    "O'rta": {
        "age_group": "10-13 yosh",
        "difficulty": "o'rta",
        "label": "O'rta (Standard)",
    },
    "Qiyin": {
        "age_group": "10-13 yosh",
        "difficulty": "qiyin",
        "label": "Qiyin (Murakkab)",
    },
    "Akademik": {
        "age_group": "14+ yosh",
        "difficulty": "akademik",
        "label": "Akademik (Olimpiada)",
    },
}

TYPE_CHOICES = {
    "Algebra / Matematika": "Algebra / Matematika",
    "Geometriya": "Geometriya",
    "Boshqotirma": "Boshqotirma",
    "Mantiqiy fikrlash": "Mantiqiy fikrlash",
    "IQ / Tanqidiy fikrlash": "IQ / Tanqidiy fikrlash",
    "Prezident maktabi": "Prezident maktabi",
}


class CustomQuizState(StatesGroup):
    age_group = State()
    quiz_type = State()
    topic = State()
    duration = State()
    question_count = State()


@custom_quiz_router.message(Command("custom_quiz"), IsAdmin())
@custom_quiz_router.message(F.text == BTN_CUSTOM_QUIZ, IsAdmin())
async def start_custom_quiz(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Oson (Boshlang'ich)"),
                KeyboardButton(text="O'rta"),
            ],
            [
                KeyboardButton(text="Qiyin"),
                KeyboardButton(text="Akademik"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Qiyinlik darajasini tanlang",
    )
    await message.answer(
        "<b>Yangi custom quiz boshlandi.</b>\n\n"
        "1-qadam: qaysi qiyinlik darajasini tanlaysiz?",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await state.set_state(CustomQuizState.age_group)


@custom_quiz_router.message(CustomQuizState.age_group)
async def process_age(message: Message, state: FSMContext):
    level_profile = LEVEL_CHOICES.get(message.text)
    if not level_profile:
        await message.answer("Tayyor tugmalardan birini tanlang.")
        return

    await state.update_data(
        age_group=level_profile["age_group"],
        difficulty=level_profile["difficulty"],
        level_label=level_profile["label"],
    )
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Algebra / Matematika"),
                KeyboardButton(text="Geometriya"),
            ],
            [
                KeyboardButton(text="Boshqotirma"),
                KeyboardButton(text="Mantiqiy fikrlash"),
            ],
            [
                KeyboardButton(text="IQ / Tanqidiy fikrlash"),
                KeyboardButton(text="Prezident maktabi"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Fan turini tanlang",
    )
    await message.answer("2-qadam: qaysi fan turini tanlaysiz?", reply_markup=keyboard)
    await state.set_state(CustomQuizState.quiz_type)


@custom_quiz_router.message(CustomQuizState.quiz_type)
async def process_type(message: Message, state: FSMContext):
    quiz_type = TYPE_CHOICES.get(message.text)
    if not quiz_type:
        await message.answer("Fan turini pastdagi tugmalardan tanlang.")
        return

    await state.update_data(q_type=quiz_type)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Aralash mavzu")]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Mavzuni yozing yoki aralashni tanlang",
    )
    await message.answer(
        "3-qadam: aniq <b>mavzu</b>ni yozing yoki pastdagi tugmani tanlang.\n"
        "Masalan: <i>Kvadrat tenglama va yuzalar</i>",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await state.set_state(CustomQuizState.topic)


@custom_quiz_router.message(CustomQuizState.topic)
async def process_topic(message: Message, state: FSMContext):
    topic = (message.text or "").strip()
    if not topic:
        await message.answer("Mavzuni yozing yoki 'Aralash mavzu' tugmasini tanlang.")
        return

    await state.update_data(topic=topic)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="10"), KeyboardButton(text="15")],
            [KeyboardButton(text="30"), KeyboardButton(text="60")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Quiz muddati",
    )
    await message.answer("4-qadam: har bir quiz necha daqiqa ochiq tursin?", reply_markup=keyboard)
    await state.set_state(CustomQuizState.duration)


@custom_quiz_router.message(CustomQuizState.duration)
async def process_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text)
    except ValueError:
        await message.answer("Faqat raqam kiriting. Masalan: 30")
        return

    if duration < 1 or duration > 120:
        await message.answer("Muddat 1 dan 120 daqiqagacha bo'lishi kerak.")
        return

    await state.update_data(dur=duration)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="5"), KeyboardButton(text="10")],
            [KeyboardButton(text="15"), KeyboardButton(text="30")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Quizlar soni",
    )
    await message.answer("5-qadam: jami nechta quiz generatsiya qilinsin?", reply_markup=keyboard)
    await state.set_state(CustomQuizState.question_count)


@custom_quiz_router.message(CustomQuizState.question_count)
async def process_count(message: Message, state: FSMContext):
    try:
        question_count = int(message.text)
    except ValueError:
        await message.answer("Iltimos, raqam kiriting. Masalan: 5")
        return

    if question_count < 1 or question_count > 50:
        await message.answer("Quiz soni 1 dan 50 gacha bo'lishi kerak.")
        return

    data = await state.get_data()
    duration = data.get("dur", 30)
    if duration < 1 or duration > 120:
        await message.answer(
            "Muddat noto'g'ri. Qaytadan boshlang: /custom_quiz",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.clear()
        return

    from bot.automation import get_target_channel

    channel_id = get_target_channel()
    if not channel_id:
        await message.answer(
            "Kanal topilmadi. Avval <code>/kanal_ornat @kanal_nomi</code> yuboring.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML",
        )
        await state.clear()
        return

    await message.answer(
        "<b>Sozlamalar qabul qilindi.</b>\n\n"
        f"Kanal: <code>{channel_id}</code>\n"
        f"Daraja: {data.get('level_label')}\n"
        f"Profil: {data.get('age_group')}\n"
        f"Fan: {data.get('q_type')}\n"
        f"Mavzu: {data.get('topic')}\n"
        f"Miqdor: {question_count} ta\n"
        f"Muddat: {duration} daqiqa\n\n"
        "AI quizlarni ketma-ket tayyorlashni boshlaydi.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )

    from services.ai_generator import trigger_quiz_generation

    asyncio.create_task(
        trigger_quiz_generation(
            bot=message.bot,
            chat_id=channel_id,
            age_group=data.get("age_group"),
            quiz_type=data.get("q_type"),
            count=question_count,
            duration_minutes=duration,
            custom_topic=data.get("topic") if data.get("topic") != "Aralash mavzu" else None,
            difficulty=data.get("difficulty"),
        )
    )
    await state.clear()
