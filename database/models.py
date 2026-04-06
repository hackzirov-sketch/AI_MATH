"""
database/models.py
"""

import os
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()


class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(String(200), nullable=True)
    description = Column(String(200), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True)
    service = Column(String(50), nullable=False, default="groq")  # ← 'gemini' → 'groq'
    api_key = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    display_name = Column(String(100), nullable=True)
    score = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    incorrect_answers = Column(Integer, default=0)
    rank_title = Column(String(100), default="Yangi boshlovchi")
    detected_age_group = Column(String(20), nullable=True)
    last_activity = Column(DateTime, default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, default=func.now())
    quiz_results = relationship("QuizResult", back_populates="user")


class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True)
    topic = Column(String(100), nullable=True)
    quiz_type = Column(String(50), nullable=False)
    age_group = Column(String(50), nullable=False)
    difficulty = Column(String(50), nullable=False)
    question_text = Column(Text, nullable=False)
    option_a = Column(String(100), nullable=False)
    option_b = Column(String(100), nullable=False)
    option_c = Column(String(100), nullable=False)
    option_d = Column(String(100), nullable=False)
    correct_option_index = Column(Integer, nullable=False)
    explanation = Column(Text, nullable=True)
    image_path = Column(String(255), nullable=True)
    message_id = Column(Integer, nullable=True)
    chat_id = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    poll_id = Column(String(100), nullable=True)
    duration_minutes = Column(Integer, default=30)
    created_at = Column(DateTime, default=func.now())
    results = relationship("QuizResult", back_populates="quiz")


class QuizResult(Base):
    __tablename__ = "quiz_results"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False, index=True)
    chosen_option_index = Column(Integer, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    points_earned = Column(Integer, default=0)
    answered_at = Column(DateTime, default=func.now())
    user = relationship("User", back_populates="quiz_results")
    quiz = relationship("Quiz", back_populates="results")


class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    level = Column(String(20), nullable=False)
    module = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())


class AudiencePoll(Base):
    __tablename__ = "audience_polls"
    id = Column(Integer, primary_key=True)
    poll_id = Column(String(100), nullable=False, unique=True)
    message_id = Column(Integer, nullable=False)
    winning_age_group = Column(String(50), nullable=True)
    is_closed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())


class QuizTypePoll(Base):
    __tablename__ = "quiz_type_polls"
    id = Column(Integer, primary_key=True)
    poll_id = Column(String(100), nullable=False, unique=True)
    message_id = Column(Integer, nullable=False)
    target_age_group = Column(String(50), nullable=False)
    winning_quiz_type = Column(String(50), nullable=True)
    is_closed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())


class AutomationState(Base):
    __tablename__ = "automation_state"
    id = Column(Integer, primary_key=True)
    is_active = Column(Boolean, default=False)
    current_step = Column(String(50), nullable=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)


class DailyMathContent(Base):
    __tablename__ = "daily_math_content"
    id = Column(Integer, primary_key=True)
    content_text = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=False)
    is_sent = Column(Boolean, default=False)
    scheduled_time = Column(String(20), nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())


# ── Singleton Engine va Session Factory ───────────────
_engine = None
_Session = None


def _normalize_database_url(db_url: str) -> str:
    normalized = (db_url or "").strip()
    if not normalized:
        return normalized
    try:
        import psycopg  # noqa: F401

        driver_prefix = "postgresql+psycopg://"
    except Exception:
        driver_prefix = "postgresql://"
    if normalized.startswith("postgres://"):
        return normalized.replace("postgres://", driver_prefix, 1)
    if normalized.startswith("postgresql://"):
        return normalized.replace("postgresql://", driver_prefix, 1)
    return normalized


def get_engine():
    global _engine
    if _engine is None:  # ← Har safar yangi engine emas!
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            _engine = create_engine(
                _normalize_database_url(db_url),
                echo=False,
                pool_pre_ping=True,
                pool_recycle=300,
            )
        else:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "database.db",
            )
            _engine = create_engine(
                f"sqlite:///{db_path}?check_same_thread=False", echo=False
            )
    return _engine


def init_db():
    Base.metadata.create_all(get_engine())


def get_session():
    global _Session
    if _Session is None:
        _Session = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False
        )
    return _Session()
