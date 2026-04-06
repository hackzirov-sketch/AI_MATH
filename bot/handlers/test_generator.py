"""
bot/handlers/test_generator.py — HANDLER

Faoliyati:
- Userdan ma'lumot yig'iladi
- Validatsiya qiladi
- Service ga yuboradi
- Natijani userga beradi

👉 Hech qanday "AI generation" yoki "PDF logic" bu yerda yo'q
"""

import asyncio
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from services.test_builder import TestBuilder, TestRequest, test_builder

test_router = Router()

BTN_CANCEL = "Bekor qilish"
BTN_SKIP = "O'tkazib yuborish"
BTN_SUGGEST = "Mavzu tavsiya qilish"

DIFFICULTIES = ["oson", "o'rta", "qiyin"]


class TestGeneratorStates(StatesGroup):
    waiting_for_grade = State()
    waiting_for_difficulty = State()
    waiting_for_count = State()
    waiting_for_subject = State()
    waiting_for_topic = State()
    generating = State()


def get_cancel_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text=BTN_CANCEL))
    return builder.as_markup(resize_keyboard=True)


def get_difficulty_keyboard():
    builder = ReplyKeyboardBuilder()
    for d in DIFFICULTIES:
        builder.add(types.KeyboardButton(text=d.capitalize()))
    builder.add(types.KeyboardButton(text=BTN_CANCEL))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_skip_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text=BTN_SKIP))
    builder.add(types.KeyboardButton(text=BTN_CANCEL))
    return builder.as_markup(resize_keyboard=True)


@test_router.message(Command("test"))
async def cmd_test_start(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    
    await message.answer(
        "📚 <b>AI Test Generator</b>\n\n"
        "Test yaratish uchun ketma-ket ma'lumotlar kiriting.\n\n"
        "1️⃣ <b>Sinf raqamini</b> kiriting (1-11):"
    )
    await state.set_state(TestGeneratorStates.waiting_for_grade)


@test_router.message(TestGeneratorStates.waiting_for_grade)
async def process_grade(message: Message, state: FSMContext):
    """Sinf raqamini qabul qilish"""
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
    
    try:
        text = message.text.strip()
        text = text.replace("-sinf", "").replace("sinf", "").strip()
        grade = int(text)
        if grade < 1 or grade > 11:
            await message.answer("Xato! Sinf 1 dan 11 gacha bo'lishi kerak. Qayta kiriting:")
            return
        
        await state.update_data(grade=grade)
        
        difficulty_text = "\n".join([f"• {d.capitalize()}" for d in DIFFICULTIES])
        await message.answer(
            f"✅ {grade}-sinf tanlandi.\n\n"
            f"2️⃣ <b>Qiyinlik darajasini</b> tanlang:\n{difficulty_text}",
            reply_markup=get_difficulty_keyboard()
        )
        await state.set_state(TestGeneratorStates.waiting_for_difficulty)
        
    except ValueError:
        await message.answer("Xato! Raqam kiriting (1-11):")


@test_router.message(TestGeneratorStates.waiting_for_difficulty)
async def process_difficulty(message: Message, state: FSMContext):
    """Qiyinlik darajasini qabul qilish"""
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
    
    difficulty = message.text.strip().lower()
    valid_diffs = [d.lower() for d in DIFFICULTIES]
    
    if difficulty not in valid_diffs:
        await message.answer(
            "Xato! Quyidagilardan birini tanlang:",
            reply_markup=get_difficulty_keyboard()
        )
        return
    
    await state.update_data(difficulty=difficulty)
    
    await message.answer(
        f"✅ Qiyinlik: <b>{difficulty.capitalize()}</b>\n\n"
        f"3️⃣ <b>Savollar sonini</b> kiriting (5-50):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TestGeneratorStates.waiting_for_count)


@test_router.message(TestGeneratorStates.waiting_for_count)
async def process_count(message: Message, state: FSMContext):
    """Savollar sonini qabul qilish"""
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
    
    try:
        count = int(message.text.strip())
        if count < 5 or count > 50:
            await message.answer("Xato! Savollar soni 5 dan 50 gacha bo'lishi kerak. Qayta kiriting:")
            return
        
        await state.update_data(count=count)
        
        await message.answer(
            f"✅ Savollar soni: <b>{count} ta</b>\n\n"
            f"4️⃣ <b>Fan nomini</b> kiriting:\n"
            f"(masalan: matematika, algebra, geometriya, IQ, prezident maktabi...)",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(TestGeneratorStates.waiting_for_subject)
        
    except ValueError:
        await message.answer("Xato! Raqam kiriting (5-50):")


@test_router.message(TestGeneratorStates.waiting_for_subject)
async def process_subject(message: Message, state: FSMContext):
    """Fan nomini qabul qilish"""
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
    
    subject = message.text.strip()
    if not subject:
        await message.answer("Xato! Fan nomini kiriting:")
        return
    
    await state.update_data(subject=subject)
    
    topics = test_builder.suggest_topics(subject)
    topics_text = ", ".join(topics[:8]) if topics else "avtomatik tanlanadi"
    
    await message.answer(
        f"✅ Fan: <b>{subject.capitalize()}</b>\n\n"
        f"5️⃣ <b>Mavzu</b> (ixtiyoriy):\n"
        f"Tavsiya etilgan: {topics_text}\n\n"
        f"Agar mavzu kiritmasangiz, avtomatik tanlanadi.",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(TestGeneratorStates.waiting_for_topic)


@test_router.message(TestGeneratorStates.waiting_for_topic)
async def process_topic(message: Message, state: FSMContext):
    """Mavzuni qabul qilish (ixtiyoriy)"""
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
    
    topic = None
    if message.text != BTN_SKIP:
        topic = message.text.strip()
    
    data = await state.update_data(topic=topic)
    await state.set_state(TestGeneratorStates.generating)
    
    grade = data['grade']
    difficulty = data['difficulty']
    count = data['count']
    subject = data['subject']
    
    await message.answer(
        f"⏳ Test yaratilmoqda...\n\n"
        f"📚 {grade}-sinf | {difficulty.capitalize()} | {count} ta savol\n"
        f"📖 Fan: {subject.capitalize()}" + (f"\n📌 Mavzu: {topic}" if topic else "")
    )
    
    await _generate_test(message, state, data)


async def _generate_test(message: Message, state: FSMContext, data: dict):
    """Test generatsiya qilish - Orchestrator ga topshiriladi"""
    
    grade = data['grade']
    difficulty = data['difficulty']
    count = data['count']
    subject = data['subject']
    
    request = TestRequest(
        grade=data['grade'],
        difficulty=data['difficulty'],
        question_count=data['count'],
        subject=data['subject'],
        topic=data.get('topic')
    )
    
    response = test_builder.build_test(request)
    
    if not response.success:
        await message.answer(
            f"❌ Xatolik yuz berdi: {response.error_message}"
        )
        await state.clear()
        return
    
    if response.test_pdf_path:
        try:
            with open(response.test_pdf_path, 'rb') as f:
                test_file = types.BufferedInputFile(
                    f.read(),
                    filename=f"test_{grade}sinf_{subject}.pdf"
                )
            
            await message.answer_document(
                test_file,
                caption=f"✅ <b>{grade}-sinf {subject.capitalize()} testi</b>\n"
                        f"📊 {count} ta savol | {difficulty.capitalize()} daraja"
            )
            
            await asyncio.sleep(2)
            
            if response.answers_pdf_path:
                with open(response.answers_pdf_path, 'rb') as f:
                    answers_file = types.BufferedInputFile(
                        f.read(),
                        filename=f"javoblar_{grade}sinf_{subject}.pdf"
                    )
                
                await message.answer_document(
                    answers_file,
                    caption="📝 <b>Javoblar ro'yxati</b>"
                )
            
            validation = response.validation_result
            if validation and validation.duplicate_count > 0:
                await message.answer(
                    f"⚠️ {validation.duplicate_count} ta takroriy savol olib tashlandi."
                )
            
            await message.answer(
                "✅ Test muvaffaqiyatli yaratildi!\n\n"
                "Yangi test yaratish uchun /test buyrug'ini yuboring."
            )
            
        except Exception as e:
            await message.answer(f"❌ PDF yuborishda xatolik: {str(e)}")
    else:
        await message.answer("❌ PDF fayl yaratilmadi.")
    
    await state.clear()


@test_router.message(F.text == BTN_CANCEL)
async def cancel_handler(message: Message, state: FSMContext):
    """Bekor qilish"""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("Bekor qilindi.")


def register_test_handlers(dp):
    """Handlerlarni ro'yxatdan o'tkazish"""
    dp.include_router(test_router)
