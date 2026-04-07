from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    import httpx
except Exception:
    httpx = None

import requests

from database.models import DailyMathContent, get_session
from services.key_manager import execute_with_rotation
from services.settings_store import get_setting_int, get_setting_value

logger = logging.getLogger(__name__)

try:
    APP_TIMEZONE = ZoneInfo(os.getenv("APP_TIMEZONE", "Asia/Tashkent"))
except ZoneInfoNotFoundError:
    APP_TIMEZONE = timezone(timedelta(hours=5))
DEFAULT_SEND_HOUR = 9
DEFAULT_SEND_MINUTE = 0
WIKIMEDIA_USER_AGENT = os.getenv(
    "WIKIMEDIA_USER_AGENT",
    "AI_MATH/1.0 (educational mathematics bot; contact: admin@example.com)",
)
MATH_BIRTHDAY_KEYWORDS = (
    "mathematician",
    "statistician",
    "logician",
    "astronomer",
    "cryptographer",
    "computer scientist",
    "mathematics",
    "mathematical",
)
ENGLISH_HINT_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "astronomer",
    "became",
    "born",
    "called",
    "commonly",
    "doctor",
    "died",
    "from",
    "historian",
    "influential",
    "is",
    "jewish",
    "known",
    "mathematician",
    "mathematics",
    "middle",
    "of",
    "philosopher",
    "physician",
    "proposed",
    "rabbi",
    "referred",
    "scholar",
    "scientist",
    "teacher",
    "the",
    "theorem",
    "torah",
    "was",
    "widely",
}
UZBEK_HINT_WORDS = {
    "astronom",
    "bo'lgan",
    "edi",
    "ekan",
    "haqida",
    "hisoblanadi",
    "kim",
    "matematika",
    "matematik",
    "muhim",
    "olim",
    "sana",
    "shifokor",
    "tavallud",
    "vafot",
    "va",
    "yilda",
}
DISCOVERY_TOPICS = [
    {"topic": "Pifagor teoremasi", "emoji": "📐", "label": "geometrik kashfiyot"},
    {"topic": "Fibonacci ketma-ketligi", "emoji": "🌿", "label": "tabiatdagi matematika"},
    {"topic": "Tub sonlar", "emoji": "🔢", "label": "sonlar nazariyasi"},
    {"topic": "Eyler formulasi", "emoji": "✨", "label": "go'zal formula"},
    {"topic": "Paskal uchburchagi", "emoji": "🔺", "label": "kombinatorik tuzilma"},
    {"topic": "Fraktal geometriya", "emoji": "🌀", "label": "zamonaviy geometriya"},
    {"topic": "Ehtimollar nazariyasi", "emoji": "🎲", "label": "amaliy matematika"},
    {"topic": "Analitik geometriya", "emoji": "📏", "label": "matematik burilish"},
]
FALLBACK_LONG_FACTS = [
    {
        "title": "Nol sonining kuchi",
        "content_type": "fact",
        "text": (
            "🔢 <b>Bugungi matematika ma'lumoti: Nol sonining kuchi</b>\n\n"
            "📚 Nol shunchaki 'hech narsa' emas. U sonlar sistemasini joy qiymati bilan ishlatishga imkon bergan eng buyuk g'oyalardan biridir. "
            "Masalan, 105 sonidagi nol bo'lmasa, 15 va 105 orasidagi farqni aniq yozib bo'lmas edi.\n\n"
            "🌍 Nol g'oyasi Hindiston matematiklari tomonidan rivojlantirilgan va keyinchalik butun dunyo hisoblash tizimiga kirib borgan. "
            "Bugungi kompyuterlar ham aslida 0 va 1 ga tayangan holda ishlaydi.\n\n"
            "💡 Demak, nol bo'lmaganida zamonaviy matematika, algoritmlar va raqamli texnologiyalar hozirgi darajaga chiqmagan bo'lardi."
        ),
    },
    {
        "title": "Gaussning tez yig'indisi",
        "content_type": "fact",
        "text": (
            "🧠 <b>Bugungi matematika ma'lumoti: Gaussning tez fikrlashi</b>\n\n"
            "📘 Rivoyatga ko'ra, yosh Karl Fridrix Gaussga 1 dan 100 gacha bo'lgan sonlarni qo'shish topshirilganida, u buni juda tez bajargan. "
            "U 1+100, 2+99, 3+98 kabi juftlarni ko'rib, har bir juft 101 ga teng ekanini payqagan.\n\n"
            "➕ Bunday juftlar 50 ta bo'lgani uchun javob 50 × 101 = 5050 bo'ladi. "
            "Bu usul oddiy misolda naqshni ko'rish matematikada qanchalik muhim ekanini ko'rsatadi.\n\n"
            "✨ Shu g'oya keyinchalik arifmetik progressiya formulalarini tushunishga yo'l ochadi va o'quvchilarda matematik tafakkurni kuchaytiradi."
        ),
    },
]
_daily_send_lock = asyncio.Lock()


class _LazyKnowledgeRetriever:
    def retrieve(self, *args, **kwargs):
        from services.knowledge_retriever import knowledge_retriever as _knowledge_retriever

        return _knowledge_retriever.retrieve(*args, **kwargs)


knowledge_retriever = _LazyKnowledgeRetriever()


@dataclass
class DailyContentMessage:
    text: str
    content_type: str
    title: str


def get_local_now(now: Optional[datetime] = None) -> datetime:
    if now is None:
        return datetime.now(APP_TIMEZONE)
    if now.tzinfo is None:
        return now.replace(tzinfo=APP_TIMEZONE)
    return now.astimezone(APP_TIMEZONE)


def get_today_date_str(now: Optional[datetime] = None) -> str:
    return get_local_now(now).strftime("%Y-%m-%d")


def _format_human_date(now: Optional[datetime] = None) -> str:
    current = get_local_now(now)
    month_names = [
        "",
        "yanvar",
        "fevral",
        "mart",
        "aprel",
        "may",
        "iyun",
        "iyul",
        "avgust",
        "sentabr",
        "oktabr",
        "noyabr",
        "dekabr",
    ]
    return f"{current.day}-{month_names[current.month]}"


def _escape(value: str) -> str:
    return html.escape(str(value or ""), quote=False)


def _trim_message(text: str, limit: int = 3800) -> str:
    normalized = str(text or "").strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _pick_daily_topic(now: Optional[datetime] = None) -> dict[str, str]:
    current = get_local_now(now)
    index = current.toordinal() % len(DISCOVERY_TOPICS)
    return DISCOVERY_TOPICS[index]


def _format_sources(urls: Iterable[str]) -> str:
    unique_urls: list[str] = []
    for url in urls:
        normalized = str(url or "").strip()
        if not normalized or normalized in unique_urls:
            continue
        unique_urls.append(normalized)
        if len(unique_urls) == 2:
            break
    if not unique_urls:
        return ""
    lines = ["\n🔗 <b>Manbalar:</b>"]
    for index, url in enumerate(unique_urls, start=1):
        lines.append(f"{index}. <a href=\"{_escape(url)}\">{_escape(url)}</a>")
    return "\n".join(lines)


def _get_schedule_value(setting_key: str, env_key: str, default: int, min_value: int, max_value: int) -> int:
    value = get_setting_int(setting_key, default, min_value, max_value)
    raw_env = os.getenv(env_key, "").strip()
    if not raw_env:
        return value
    try:
        env_value = int(raw_env)
    except ValueError:
        return value
    return max(min_value, min(max_value, env_value))


def _pick_math_relevant_fact(candidates: Iterable[str], title: str, base_text: str = "") -> str:
    weighted_terms = (
        ("mathematician", 10),
        ("mathematics", 8),
        ("geometry", 7),
        ("algebra", 7),
        ("theorem", 7),
        ("court mathematician", 9),
        ("academy", 5),
        ("astronomy", 4),
    )
    normalized_title = title.lower()
    normalized_base = base_text.lower()
    scored: list[tuple[int, str]] = []
    for candidate in candidates:
        text = str(candidate or "").strip()
        lowered = text.lower()
        if not text or lowered in normalized_base:
            continue
        score = 0
        if normalized_title and normalized_title in lowered:
            score += 2
        for term, weight in weighted_terms:
            if term in lowered:
                score += weight
        if score == 0 and not scored:
            score = 1
        scored.append((score, text))
    if not scored:
        return ""
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def _is_low_quality_content(text: str) -> bool:
    lowered = str(text or "").strip().lower()
    if not lowered:
        return True
    bad_fragments = (
        "required part of this site",
        "couldn’t load",
        "couldn't load",
        "browser settings",
        "ad blockers",
        "different browser",
        "please check your",
        "connection, disable",
    )
    if any(fragment in lowered for fragment in bad_fragments):
        return True
    if len(lowered) < 60 and lowered[-1:] not in {".", "!", "?", ":", ";"}:
        return True
    return False


def _pick_best_content_piece(candidates: Iterable[str], min_length: int = 40, exclude_text: str = "") -> str:
    excluded = str(exclude_text or "").strip().lower()
    fallback = ""
    for candidate in candidates:
        text = str(candidate or "").strip()
        if len(text) < min_length:
            continue
        lowered = text.lower()
        if excluded and lowered == excluded:
            continue
        if fallback == "":
            fallback = text
        if not _is_low_quality_content(text):
            return text
    return fallback


def _looks_english(text: str) -> bool:
    lowered = str(text or "").lower().strip()
    if not lowered:
        return False
    normalized = re.sub(r"[^a-z' ]+", " ", lowered)
    tokens = [token for token in normalized.split() if len(token) >= 2]
    if not tokens:
        return False
    english_hits = sum(1 for token in tokens if token in ENGLISH_HINT_WORDS)
    uzbek_hits = sum(1 for token in tokens if token in UZBEK_HINT_WORDS)
    phrase_hits = sum(
        1
        for phrase in (
            "commonly known as",
            "widely acknowledged",
            "was a",
            "was an",
            "born in",
            "died in",
            "and is",
            "one of the",
        )
        if phrase in lowered
    )
    return english_hits + phrase_hits >= 3 and english_hits + phrase_hits > uzbek_hits


def run_ai_daily_content_localization(
    api_key: str,
    service: str,
    title: str,
    intro: str,
    extract: str,
    importance: str,
) -> dict[str, str]:
    prompt = (
        "Quyidagi matematik ma'lumotni aniq va sodda o'zbek tiliga aylantir. "
        "Ma'lumot qo'shma, fakt o'ylab topma, ism va sanalarni o'zgartirma. "
        "JSON formatda javob ber: "
        '{"intro_uz":"...","extract_uz":"...","importance_uz":"..."}.\n\n'
        f"TITLE: {title}\n"
        f"INTRO: {intro}\n"
        f"EXTRACT: {extract}\n"
        f"IMPORTANCE: {importance}\n"
    )
    messages = [
        {
            "role": "system",
            "content": "Siz ishonchli o'zbekcha ilmiy muharrirsiz. Faqat toza JSON qaytaring.",
        },
        {"role": "user", "content": prompt},
    ]
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"messages": messages, "temperature": 0.2, "max_tokens": 350}

    if service == "openrouter":
        url = "https://openrouter.ai/api/v1/chat/completions"
        payload["model"] = "meta-llama/llama-3.3-70b-instruct"
        headers["HTTP-Referer"] = "https://aimath.bot"
    elif service == "cerebras":
        url = "https://api.cerebras.ai/v1/chat/completions"
        payload["model"] = "llama3.3-70b"
    elif service == "sambanova":
        url = "https://api.sambanova.ai/v1/chat/completions"
        payload["model"] = "Meta-Llama-3.3-70B-Instruct"
    else:
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload["model"] = "llama-3.3-70b-versatile"

    response = requests.post(url, headers=headers, json=payload, timeout=25)
    if response.status_code != 200:
        if response.status_code == 429:
            raise Exception(f"RateLimitExhausted: {response.text}")
        raise Exception(f"API Error ({service}): {response.text}")

    content = response.json()["choices"][0]["message"]["content"].strip()
    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    raw_json = match.group(0) if match else content
    data = json.loads(raw_json)
    return {
        "intro_uz": str(data.get("intro_uz", "")).strip(),
        "extract_uz": str(data.get("extract_uz", "")).strip(),
        "importance_uz": str(data.get("importance_uz", "")).strip(),
    }


async def _localize_content_sections(
    title: str,
    intro: str,
    extract: str,
    importance: str,
    force: bool = False,
) -> tuple[str, str, str]:
    parts = tuple(part for part in (intro, extract, importance) if str(part or "").strip())
    if not force and not any(_looks_english(part) for part in parts):
        return intro, extract, importance
    try:
        localized, error = await asyncio.to_thread(
            execute_with_rotation,
            run_ai_daily_content_localization,
            title,
            intro,
            extract,
            importance,
            ai_role="title_gen",
        )
        if error or not localized:
            return intro, extract, importance
        return (
            str(localized.get("intro_uz") or intro).strip(),
            str(localized.get("extract_uz") or extract).strip(),
            str(localized.get("importance_uz") or importance).strip(),
        )
    except Exception as exc:
        logger.warning("Daily content localization xatosi: %s", exc)
        return intro, extract, importance


async def _localize_single_block(title: str, text: str, force: bool = False) -> str:
    raw_text = str(text or "").strip()
    if not raw_text:
        return ""
    _, localized_text, _ = await _localize_content_sections(
        title=title,
        intro="",
        extract=raw_text,
        importance="",
        force=force,
    )
    return str(localized_text or raw_text).strip()


def _sync_has_sent_today(date_str: str) -> bool:
    session = get_session()
    try:
        existing = (
            session.query(DailyMathContent)
            .filter_by(is_sent=True, scheduled_time=date_str)
            .first()
        )
        return existing is not None
    finally:
        session.close()


def _sync_save_sent_content(content_text: str, content_type: str, scheduled_time: str) -> int:
    session = get_session()
    try:
        record = DailyMathContent(
            content_text=content_text,
            content_type=content_type,
            is_sent=True,
            scheduled_time=scheduled_time,
            sent_at=datetime.utcnow(),
        )
        session.add(record)
        session.commit()
        return int(record.id)
    finally:
        session.close()


async def _fetch_json(url: str) -> Optional[dict]:
    if httpx is None:
        return None
    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": WIKIMEDIA_USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        logger.warning("Daily content JSON fetch xatosi: %s", exc)
        return None


async def _fetch_today_births(now: Optional[datetime] = None) -> list[dict]:
    current = get_local_now(now)
    url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/births/{current.month:02d}/{current.day:02d}"
    payload = await _fetch_json(url)
    if not payload:
        return []
    return list(payload.get("births") or [])


async def _fetch_wikipedia_summary(title: str) -> Optional[dict]:
    normalized = str(title or "").strip().replace(" ", "_")
    if not normalized:
        return None
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{normalized}"
    return await _fetch_json(url)


def _is_math_birthday(entry: dict) -> bool:
    text = str(entry.get("text", "")).lower()
    pages = entry.get("pages") or []
    page_title = ""
    if pages:
        page_title = str((pages[0] or {}).get("title", "")).replace("_", " ").lower()
    combined = f"{text} {page_title}"
    return any(keyword in combined for keyword in MATH_BIRTHDAY_KEYWORDS)


def _birthday_score(entry: dict) -> int:
    text = str(entry.get("text", "")).lower()
    score = 0
    if "mathematician" in text or "mathematics" in text:
        score += 10
    if "statistician" in text or "logician" in text:
        score += 8
    if "cryptographer" in text or "computer scientist" in text:
        score += 6
    if "astronomer" in text:
        score += 3
    if "physicist" in text:
        score += 2
    return score


async def _build_birthday_content(now: Optional[datetime] = None) -> Optional[DailyContentMessage]:
    birthdays = [entry for entry in await _fetch_today_births(now) if _is_math_birthday(entry)]
    birthdays.sort(key=_birthday_score, reverse=True)
    for entry in birthdays:
        pages = entry.get("pages") or []
        page = (pages[0] or {}) if pages else {}
        title = str(page.get("title", "")).replace("_", " ").strip()
        if not title:
            continue

        summary = await _fetch_wikipedia_summary(title)
        extract = str((summary or {}).get("extract", "")).strip()
        page_url = (
            (summary or {}).get("content_urls", {})
            .get("desktop", {})
            .get("page")
            or str(page.get("content_urls", {}).get("desktop", {}).get("page", "")).strip()
        )
        if len(extract) < 80:
            continue

        retrieval = await asyncio.to_thread(
            knowledge_retriever.retrieve,
            title,
            "mathematics",
            None,
            2,
        )
        extra_fact = _pick_math_relevant_fact(
            retrieval.structured.important_facts
            + retrieval.structured.rules
            + retrieval.structured.definitions,
            title=title,
            base_text=extract,
        )
        intro_uz, extract_uz, extra_fact_uz = await _localize_content_sections(
            title=title,
            intro=str(entry.get("text", "")).strip(),
            extract=extract,
            importance=extra_fact,
            force=True,
        )
        if _looks_english(intro_uz) or _looks_english(extract_uz):
            continue
        if extra_fact_uz and _looks_english(extra_fact_uz):
            extra_fact_uz = ""

        example_text = ""
        if retrieval.structured.examples:
            example_text = await _localize_single_block(
                title=title,
                text=retrieval.structured.examples[0],
                force=True,
            )
            if _looks_english(example_text):
                example_text = ""

        event_date = _format_human_date(now)
        message_parts = [
            f"🎉 <b>Bugungi matematik tavallud</b>",
            "",
            f"👤 <b>{_escape(title)}</b>",
            f"🗓 <b>Sana:</b> {event_date}",
            f"📌 <b>Qisqacha:</b> {_escape(intro_uz)}",
            "",
            f"📚 <b>Kim edi?</b>\n{_escape(extract_uz)}",
        ]
        if extra_fact_uz:
            message_parts.append(f"\n✨ <b>Nega muhim?</b>\n{_escape(extra_fact_uz)}")
        if example_text:
            message_parts.append(f"\n💡 <b>Qiziqarli eslatma:</b>\n{_escape(example_text)}")
        message_parts.append(_format_sources([page_url] + [source.url for source in retrieval.sources]))
        return DailyContentMessage(
            text=_trim_message("\n".join(part for part in message_parts if part is not None)),
            content_type="birthday",
            title=title,
        )
    return None


async def _build_topic_content(now: Optional[datetime] = None) -> Optional[DailyContentMessage]:
    topic_info = _pick_daily_topic(now)
    retrieval = await asyncio.to_thread(
        knowledge_retriever.retrieve,
        topic_info["topic"],
        "mathematics",
        None,
        3,
    )
    if not retrieval.content or retrieval.confidence < 0.45:
        return None

    definition = _pick_best_content_piece(
        retrieval.structured.definitions
        + retrieval.structured.rules
        + retrieval.structured.important_facts,
        min_length=40,
    )

    formula = ""
    for candidate in retrieval.structured.formulas:
        if len(candidate) >= 5:
            formula = candidate.strip()
            break

    insight = _pick_best_content_piece(
        retrieval.structured.rules + retrieval.structured.important_facts,
        min_length=30,
        exclude_text=definition,
    )

    example = _pick_best_content_piece(retrieval.structured.examples, min_length=30)

    if not definition:
        definition = retrieval.content[:400].strip()
    if not insight:
        insight = retrieval.content[400:800].strip()
    _, definition_uz, insight_uz = await _localize_content_sections(
        title=topic_info["topic"],
        intro=topic_info["label"],
        extract=definition,
        importance=insight,
        force=True,
    )
    if _looks_english(definition_uz) or (insight_uz and _looks_english(insight_uz)):
        return None
    example_uz = example
    if example:
        example_uz = await _localize_single_block(
            title=topic_info["topic"],
            text=example,
            force=True,
        )
        if _looks_english(example_uz):
            example_uz = ""

    message_parts = [
        f"{topic_info['emoji']} <b>Bugungi matematika ma'lumoti</b>",
        "",
        f"📘 <b>Mavzu:</b> {_escape(topic_info['topic'])}",
        f"🧭 <b>Yo'nalish:</b> {_escape(topic_info['label'])}",
        "",
        f"📚 <b>Asosiy tushuncha:</b>\n{_escape(definition_uz)}",
    ]
    if formula:
        message_parts.append(f"\n🧮 <b>Muhim formula:</b>\n{_escape(formula)}")
    if insight_uz:
        message_parts.append(f"\n✨ <b>Nega muhim?</b>\n{_escape(insight_uz)}")
    if example_uz:
        message_parts.append(f"\n💡 <b>Misol yoki qo'llanish:</b>\n{_escape(example_uz)}")
    message_parts.append(_format_sources([source.url for source in retrieval.sources]))

    text = _trim_message("\n".join(part for part in message_parts if part))
    if len(text) < 350:
        return None
    return DailyContentMessage(
        text=text,
        content_type="discovery",
        title=topic_info["topic"],
    )


def _build_fallback_content(now: Optional[datetime] = None) -> DailyContentMessage:
    item = FALLBACK_LONG_FACTS[get_local_now(now).toordinal() % len(FALLBACK_LONG_FACTS)]
    return DailyContentMessage(
        text=item["text"],
        content_type=item["content_type"],
        title=item["title"],
    )


async def get_daily_math_content(now: Optional[datetime] = None) -> DailyContentMessage:
    birthday_content = await _build_birthday_content(now)
    if birthday_content:
        return birthday_content

    topic_content = await _build_topic_content(now)
    if topic_content:
        return topic_content

    return _build_fallback_content(now)


async def check_and_send_daily_content(bot, channel_id: str, force: bool = False, now: Optional[datetime] = None) -> bool:
    async with _daily_send_lock:
        date_str = get_today_date_str(now)
        if not force:
            already_sent = await asyncio.to_thread(_sync_has_sent_today, date_str)
            if already_sent:
                logger.info("Bugungi kundalik matematika posti allaqachon yuborilgan")
                return False

        content = await get_daily_math_content(now)
        if not content or not content.text:
            logger.warning("Kunlik matematika posti tayyorlanmadi")
            return False

        try:
            await bot.send_message(
                chat_id=channel_id,
                text=content.text,
                disable_web_page_preview=False,
            )
            await asyncio.to_thread(
                _sync_save_sent_content,
                content.text,
                content.content_type,
                date_str,
            )
            logger.info("Kunlik matematika posti yuborildi: %s", content.title)
            return True
        except Exception as exc:
            logger.error("Kunlik matematika posti yuborish xatosi: %s", exc)
            return False


def should_send_now(now: Optional[datetime] = None) -> bool:
    current = get_local_now(now)
    target_hour = _get_schedule_value("daily_content_hour", "DAILY_CONTENT_HOUR", DEFAULT_SEND_HOUR, 0, 23)
    target_minute = _get_schedule_value("daily_content_minute", "DAILY_CONTENT_MINUTE", DEFAULT_SEND_MINUTE, 0, 59)
    scheduled = current.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    return current >= scheduled


async def run_daily_scheduled_task(bot) -> None:
    while True:
        try:
            if should_send_now():
                channel_id = await asyncio.to_thread(get_setting_value, "channel_id")
                if channel_id:
                    await check_and_send_daily_content(bot, channel_id)
        except Exception as exc:
            logger.error("Kunlik matematika kontenti xatosi: %s", exc)
        await asyncio.sleep(15 * 60)
