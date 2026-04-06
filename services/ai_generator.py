"""
services/ai_generator.py

3 QATLAMLI SHAKL KAFOLATI:
  1. Python sent_count % N asosida shakl tanlaydi  (har doim navbatma-navbat)
  2. AI ga MAJBURAN "faqat shu shaklni ishlat" deb beriladi
  3. AI e'tiborsiz qoldirsa â€” Python response ni override qiladi

Prompt optimizatsiya:
  - System message: inglizcha, qisqa (~60 token)
  - User prompt: ~180 token (avval 600+ edi)
  - max_tokens: 700 (avval 1024)
  - Unicode box-drawing olib tashlandi
  - Topics: 5 ta random tanlangan (hammasi emas)
"""

import asyncio
import html
import io
import json
import logging
import os
import random
import re
import uuid
import urllib.request

import requests

try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None

from .critical_thinking_bank import critical_thinking_bank
from .cache_manager import cache_manager
from .key_manager import execute_with_rotation
from .topic_context_service import topic_context_service
logger = logging.getLogger(__name__)

# â”€â”€ Mutlaq yo'llar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEMP_IMAGES_DIR = str(cache_manager.render_dir)
_TOPIC_STOPWORDS = {
    "va",
    "yoki",
    "bilan",
    "uchun",
    "ham",
    "shu",
    "shu",
    "nega",
    "qanday",
    "necha",
    "toping",
    "topiladi",
    "hisoblang",
    "bo'lsa",
    "bolsa",
    "ekan",
    "faqat",
    "mavzu",
    "savol",
    "javob",
    "soni",
    "qiymati",
    "uzunligi",
    "yig'indisi",
    "farqi",
    "uchun",
    "gacha",
    "sm",
    "cm",
    "mm",
    "dm",
    "ga",
    "ni",
    "ning",
    "lar",
    "lari",
}


def _build_telegram_message_link(chat_id, message_id: int) -> str | None:
    chat_value = str(chat_id or "").strip()
    if not chat_value or not message_id:
        return None
    if chat_value.startswith("@"):
        return f"https://t.me/{chat_value.lstrip('@')}/{message_id}"
    if chat_value.startswith("-100") and chat_value[4:].isdigit():
        return f"https://t.me/c/{chat_value[4:]}/{message_id}"
    return None


def _split_teacher_targets(raw_value: str | None) -> list[str]:
    raw = str(raw_value or "").strip()
    if not raw:
        return []
    targets = []
    for item in raw.split(","):
        value = item.strip()
        if value and value not in targets:
            targets.append(value)
    return targets


def _normalize_teacher_chat_id(raw_value: str) -> str | int | None:
    value = str(raw_value or "").strip()
    if not value:
        return None
    if value.lstrip("-").isdigit():
        try:
            return int(value)
        except ValueError:
            return value
    return value


def _looks_like_image_content(content_type: str, content: bytes) -> bool:
    ct = (content_type or "").split(";", 1)[0].strip().lower()
    has_known_signature = (
        content.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"GIF87a", b"GIF89a"))
        or (len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP")
    )
    if not ct.startswith("image/") and not has_known_signature:
        return False
    try:
        from PIL import Image

        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        return True
    except Exception:
        return has_known_signature

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Shakl navbatlari  (Python kafolatlaydi â€” AI emas)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Geometriya shakllari â€” takrorsiz, boyitilgan (20 ta)
_GEOMETRY_SHAPES = [
    "circle",
    "right_triangle",
    "rectangle",
    "trapezoid",
    "isosceles_triangle",
    "rhombus",
    "hexagon",
    "parallelogram",
    "equilateral_triangle",
    "obtuse_triangle",
    "pythagoras",
    "heron",
    "sin_cos",
    "incenter",
    "ceva",
    "varignon",
    "ptolemy",
    "rectangle",
    "circle",
    "trapezoid",
]

# Boshqotirma / Mantiqiy fikrlash shakllari â€” takrorsiz (6 ta)
_LOGIC_SHAPES = [
    "crossword",
    "labyrinth",
    "grid",
    "scale",
    "crossword",
    "grid",
]

# Algebra / Mantiq uchun koordinat va diagrammalar (8 ta)
_ALGEBRA_VISUAL_SHAPES = [
    "coordinate",
    "number_line",
    "bar_chart",
    "pie_chart",
    "clock",
    "vector",
    "homothety",
    "coordinate",
]


def _get_default_hint(shape: str) -> str:
    """
    AI hint bermaganida yoki noto'g'ri shakl berganda ishlatiladigan
    default geometry_hint qiymatlari.
    Bir xil shakl = bir xil seed â†’ deterministik, lekin ko'p variant.
    """
    rng = random.Random(shape)

    defaults: dict[str, list[str]] = {
        # â”€â”€ Uchburchaklar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        "circle": [
            "circle|radius_1=5|radius_2=x",
            "circle|radius_1=7|diameter=x",
            "circle|radius_1=3|radius_2=x",
            "circle|radius_1=x|element=12Ï€",
            "circle|radius_1=6|radius_2=x",
            "circle|radius_1=10|diameter=x",
        ],
        "right_triangle": [
            "right_triangle|bottom=8|left=6|right=x",
            "right_triangle|bottom=3|left=4|right=x",
            "right_triangle|bottom=12|left=5|right=x",
            "right_triangle|bottom=5|left=x|right=13",
            "right_triangle|bottom=9|left=x|right=15",
            "right_triangle|bottom=x|left=8|angle_a=30Â°",
            "right_triangle|bottom=6|left=x|angle_b=45Â°",
            "right_triangle|bottom=15|left=8|right=x",
        ],
        "isosceles_triangle": [
            "isosceles_triangle|bottom=6|left=8|angle_a=x",
            "isosceles_triangle|bottom=10|left=x|angle_b=40Â°",
            "isosceles_triangle|bottom=4|left=7|angle_c=x",
            "isosceles_triangle|bottom=x|left=9|angle_a=70Â°",
            "isosceles_triangle|bottom=8|left=x|angle_a=50Â°",
        ],
        "equilateral_triangle": [
            "equilateral_triangle|bottom=6|left=6|angle_a=60Â°",
            "equilateral_triangle|bottom=8|left=8|angle_a=x",
            "equilateral_triangle|bottom=x|left=9|angle_a=60Â°",
            "equilateral_triangle|bottom=10|left=x|angle_a=60Â°",
        ],
        "obtuse_triangle": [
            "obtuse_triangle|bottom=10|left=5|angle_a=x",
            "obtuse_triangle|bottom=8|left=x|angle_b=120Â°",
            "obtuse_triangle|bottom=7|left=4|angle_a=x",
            "obtuse_triangle|bottom=x|left=6|angle_a=130Â°",
        ],
        "triangle": [
            "triangle|bottom=7|left=5|angle_a=x",
            "triangle|bottom=9|left=x|angle_b=65Â°",
            "triangle|bottom=x|left=8|angle_a=55Â°",
        ],
        # â”€â”€ To'rtburchak shakllar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        "rectangle": [
            "rectangle|bottom=12|left=7|diagonal=x",
            "rectangle|bottom=8|left=5|area=x",
            "rectangle|bottom=x|left=6|diagonal=10",
            "rectangle|bottom=15|left=x|area=90",
            "rectangle|bottom=9|left=4|diagonal=x",
            "rectangle|bottom=x|left=8|area=48",
            "rectangle|bottom=14|left=x|diagonal=x",
        ],
        "trapezoid": [
            "trapezoid|bottom=10|top=6|height=x",
            "trapezoid|bottom=12|top=x|height=5",
            "trapezoid|bottom=x|top=4|height=6|left=8",
            "trapezoid|bottom=14|top=8|height=x|left=5",
            "trapezoid|bottom=9|top=x|height=4",
        ],
        "rhombus": [
            "rhombus|diagonal_1=8|diagonal_2=6|side=x",
            "rhombus|diagonal_1=10|diagonal_2=x|side=13",
            "rhombus|diagonal_1=x|diagonal_2=8|angle_a=60Â°",
            "rhombus|diagonal_1=6|diagonal_2=x|side=5",
            "rhombus|d1=12|d2=x|side=10",
        ],
        "parallelogram": [
            "parallelogram|bottom=8|left=5|angle_a=x",
            "parallelogram|bottom=x|left=6|angle_a=60Â°",
            "parallelogram|bottom=10|left=x|height=4",
            "parallelogram|bottom=7|left=4|angle_a=x",
        ],
        "hexagon": [
            "hexagon|side=4|radius=x",
            "hexagon|side=x|radius=6",
            "hexagon|side=7|radius=x",
            "hexagon|side=x|radius=8",
            "hexagon|side=5|radius=x",
        ],
        # â”€â”€ Koordinat va diagrammalar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        "coordinate": [
            "coordinate|x1=2|y1=3|x2=-1|y2=x",
            "coordinate|x1=0|y1=x|x2=4|y2=8",
            "coordinate|slope=2|intercept=x",
            "coordinate|point1=3,x|point2=-2,4",
            "coordinate|x1=x|y1=1|x2=3|y2=7",
        ],
        "number_line": [
            "number_line|start=-5|end=5|mark1=x|mark2=3",
            "number_line|start=0|end=10|point=x|mark1=4|mark2=7",
            "number_line|start=-3|end=7|mark1=-1|mark2=x|mark3=5",
            "number_line|start=-4|end=4|from=-2|to=x",
            "number_line|start=0|end=20|mark1=x|mark2=15",
        ],
        "bar_chart": [
            "bar_chart|bar1=15|bar2=22|bar3=x|bar4=18|label1=A|label2=B|label3=C|label4=D",
            "bar_chart|bar1=30|bar2=x|bar3=20|bar4=25|bar5=15|label1=Dush|label2=Sesh|label3=Chor|label4=Pay|label5=Jum",
            "bar_chart|bar1=x|bar2=40|bar3=35|bar4=50|label1=Bahor|label2=Yoz|label3=Kuz|label4=Qish",
            "bar_chart|bar1=12|bar2=18|bar3=24|bar4=x|bar5=9|label1=1|label2=2|label3=3|label4=4|label5=5",
        ],
        "pie_chart": [
            "pie_chart|slice1=30|slice2=25|slice3=x|slice4=15|label1=Matematika|label2=Fizika|label3=Kimyo|label4=Tarix",
            "pie_chart|slice1=40|slice2=x|slice3=20|slice4=10|label1=A|label2=B|label3=C|label4=D",
            "pie_chart|slice1=x|slice2=35|slice3=25|slice4=20|label1=1-sinf|label2=2-sinf|label3=3-sinf|label4=4-sinf",
            "pie_chart|slice1=45|slice2=30|slice3=x|label1=O'g'il|label2=Qiz|label3=Boshqa",
        ],
        "clock": [
            "clock|hour=3|minute=x",
            "clock|hour=x|minute=30",
            "clock|hour=7|minute=x",
            "clock|hour=x|minute=15",
            "clock|hour=11|minute=x",
            "clock|hour=x|minute=45",
        ],
        # â”€â”€ Boshqotirma / Mantiq â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        "scale": [
            "scale|left_side=5|right_side=x",
            "scale|left_side=x|right_side=7",
            "scale|left_side=8|right_side=x",
            "scale|left_side=x|right_side=12",
            "scale|left_side=9|right_side=x",
        ],
        "grid": [
            "grid|cell1=4|cell2=2|cell3=6|cell4=1|cell5=x|cell6=5|cell7=8|cell8=3|cell9=7",
            "grid|cell1=7|cell2=x|cell3=3|cell4=2|cell5=5|cell6=9|cell7=x|cell8=6|cell9=1",
            "grid|cell1=x|cell2=9|cell3=4|cell4=3|cell5=7|cell6=2|cell7=6|cell8=1|cell9=8",
            "grid|cell1=5|cell2=1|cell3=9|cell4=6|cell5=x|cell6=4|cell7=2|cell8=8|cell9=3",
        ],
        "crossword": [
            "crossword|cell1=5|cell2=x|cell3=2|cell4=8|cell5=1",
            "crossword|cell1=x|cell2=7|cell3=3|cell4=9|cell5=4",
            "crossword|cell1=6|cell2=1|cell3=x|cell4=5|cell5=7",
            "crossword|cell1=3|cell2=x|cell3=8|cell4=2|cell5=9",
        ],
        "labyrinth": [
            "labyrinth|start=1|end=8|path1=x|path2=4",
            "labyrinth|start=A|end=D|path1=3|path2=x",
            "labyrinth|start=2|end=9|path1=x|path2=6",
            "labyrinth|start=B|end=E|path1=5|path2=x",
        ],
        # â”€â”€ Kengaytirilgan Geometriya â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        "incenter": [
            "incenter|bottom=6|left=5|right=7|center_type=all",
            "incenter|bottom=8|left=6|right=10|center_type=incenter",
        ],
        "ceva": [
            "ceva|bottom=6|left=5|right=7",
            "ceva|bottom=8|left=6|right=10",
        ],
        "menelaus": [
            "menelaus|bottom=6|left=5|right=7",
            "menelaus|bottom=8|left=6|right=10",
        ],
        "stewart": [
            "stewart|side_a=8|side_b=6|side_c=7|median=4|ceva=x",
            "stewart|side_a=10|side_b=8|side_c=9|median=5|ceva=x",
        ],
        "ptolemy": [
            "ptolemy|side_a=6|side_b=5",
            "ptolemy|side_a=8|side_b=7",
        ],
        "varignon": [
            "varignon|side_a=6|side_b=5",
            "varignon|side_a=8|side_b=6",
        ],
        "homothety": [
            "homothety|scale=2",
            "homothety|scale=3",
            "homothety|scale=0.5",
        ],
        "vector": [
            "vector|ax=3|ay=2|bx=2|by=3.5",
            "vector|ax=4|ay=3|bx=2|by=4",
        ],
        "sin_cos": [
            "sin_cos|side_a=6|side_b=5|angle_c=60",
            "sin_cos|side_a=8|side_b=6|angle_c=45",
        ],
        "circumscribed": [
            "circumscribed|bottom=6|left=5",
            "circumscribed|bottom=8|left=6",
        ],
        "heron": [
            "heron|side_a=5|side_b=4|side_c=3",
            "heron|side_a=7|side_b=6|side_c=5",
        ],
        "pythagoras": [
            "pythagoras|bottom=3|left=4",
            "pythagoras|bottom=5|left=12",
            "pythagoras|bottom=6|left=8",
        ],
    }

    options = defaults.get(shape, [f"{shape}|element=x"])
    return rng.choice(options)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# AI Funksiyalari
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def run_ai_image_generation(prompt: str) -> str:
    """
    (Role: image_gen) Pollinations AI orqali rasm generatsiya qilish. 
    Bu bepul va bizning bot uchun eng barqaror servisdir.
    """
    os.makedirs(_TEMP_IMAGES_DIR, exist_ok=True)
    filename = f"img_{uuid.uuid4().hex[:8]}.jpg"
    filepath = os.path.join(_TEMP_IMAGES_DIR, filename)
    
    encoded_prompt = quote(prompt)
    # Pollinations AI URL - seed har doim yangi rasm yaratadi
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={uuid.uuid4().int % 1000}"
    
    # 2 marta urinib ko'ramiz
    for attempt in range(2):
        try:
            logger.info(f"Rasm generatsiya qilinmoqda (Pollinations AI, urinish: {attempt+1})...")
            response = requests.get(url, headers={}, timeout=35 if attempt == 0 else 50)
            content_type = response.headers.get("Content-Type", "")
            
            if (
                response.status_code == 200
                and len(response.content) > 1000
                and _looks_like_image_content(content_type, response.content)
            ):
                with open(filepath, "wb") as f:
                    f.write(response.content)
                logger.info("Rasm muvaffaqiyatli yaratildi.")
                return filepath
            elif response.status_code == 200:
                logger.error(
                    "Servis rasm bo'lmagan javob qaytardi (Content-Type: %s, Bytes: %s)",
                    content_type or "unknown",
                    len(response.content),
                )
            elif response.status_code == 429:
                logger.warning("Pollinations AI: Too Many Requests (429).")
                if attempt == 0:
                    time_to_wait = 2
                    logger.info(f"{time_to_wait} soniya kutib qayta uriniladi...")
                    import time
                    time.sleep(time_to_wait)
                    continue
            else:
                logger.error(f"Servis javobi (Status: {response.status_code})")
        except Exception as e:
            logger.error(f"Rasm yaratishda xato: {str(e)}")
            if attempt == 0:
                import time
                time.sleep(1)
                continue
    
    raise Exception("Image generation failed after retries")


# â”€â”€â”€ Statik tizim xabarlari (bir marta quriladi) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_SYSTEM_QUIZ = (
    "You are MathQuizBot â€” Uzbek math quiz generator for teachers. "
    "Return ONLY valid JSON: {question, options(4 items), correct_index(0-3), "
    "explanation(step-by-step Uzbek, ends 'Javob:...'), topic, geometry_hint}. "
    "Rules: all text in Uzbek; symbols xÂ² âˆš Ï€ (not x^2 sqrt pi); "
    "wrong options = plausible student mistakes; vary correct_index (0-3 randomly); "
    "geometry_hint MUST start with required shape name; never repeat questions; "
    "100% mathematically accurate. "
    "IMPORTANT: Focus ONLY on the topic provided. Create DIVERSE questions - vary numbers, operations, and question types within that topic. "
    "For arithmetic: use +, -, Ã—, Ã· with different numbers. "
    "For fractions: vary denominators and operations. "
    "For equations: use different variable positions (x+5=10, 2x=8, 15-x=7). "
    "NEVER repeat the same question structure. "
    "IMPORTANT: Generate UNIQUE questions - each question must have DIFFERENT numbers, DIFFERENT operations, and DIFFERENT question patterns. "
    "For example in arithmetic: 5+3, 12-4, 8Ã—2, 20Ã·4, 15+7, 30-8, 6Ã—3, 45Ã·9 - all different! "
    "For equations: x+3=7, 2x=10, 15-x=8, x-4=5 - all different patterns! "
    "For fractions: 1/2+1/4, 2/3-1/6, 3/4Ã—1/2, 5/8Ã·1/4 - vary denominators and operations!"
)

_SYSTEM_TITLE = "Siz quvnoq o'zbek tilidagi o'qituvchisiz. Faqat 1-2 qisqa gap yozing."

# â”€â”€â”€ Yosh qoidalari (compact, inglizcha â€” LLM uchun tejamkor) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_AGE_RULES: dict[str, str] = {
    "6-9": "VERY EASY: use only + and -. NO 'x' or variables. Use concrete objects (apples, balls). Numbers must be under 50. Output must be perfectly safe for 1st-2nd graders. NO symbols like âˆš, Ï€, or ^2.",
    "10-13": "MEDIUM: simple equations (x+5=10), fractions (1/2), percentages (%), basic geometry (perimeter, area of square/rectangle). NO advanced trigonometry or integrals.",
    "14-17": "HARD: quadratic equations, sin/cos, logarithms, advanced geometry, progressions. Standard high school level.",
    "18+": "ADVANCED: university level math, integrals, derivatives, limits, matrices, complex logic, olympiad problems.",
}

_AGE_DISPLAY = {
    "6-9": "Boshlang'ich (6-9 yosh)",
    "10-13": "O'rta (10-13 yosh)",
    "14-17": "Yuqori (14-17 yosh)",
    "18+": "Akademik / Olimpiada",
}

_FORBIDDEN_TOKENS_BY_AGE: dict[str, tuple[str, ...]] = {
    "6-9": (" x ", "x=", "x+", "x-", "xÂ²", "sqrt", "âˆš", "%", "sin", "cos", "tan", "log", "integral", "matritsa"),
    "10-13": ("sin", "cos", "tan", "log", "integral", "hosila", "derivative", "matrix", "matritsa", "determinant"),
    "14-17": ("integral", "double integral", "matrix inverse", "determinant 3x3"),
    "18+": (),
}

# â”€â”€â”€ Shakllar mos-yo'riqnomasi (compact) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_SHAPES_REF = (
    "GEO: right_triangle(bottom,left,right,angle_a/b/c) "
    "isosceles_triangle(bottom,left,angle_a/b/c) "
    "equilateral_triangle(bottom,angle_a) "
    "obtuse_triangle(bottom,left,angle_a/b) "
    "rectangle(bottom,left,diagonal,area) "
    "trapezoid(bottom,top,height,left) "
    "rhombus(diagonal_1,diagonal_2,side,angle_a) "
    "parallelogram(bottom,left,angle_a,height) "
    "circle(radius_1,radius_2,diameter) "
    "hexagon(side,radius) | "
    "ADVANCED: pythagoras(bottom,left) heron(side_a,side_b,side_c) "
    "sin_cos(side_a,side_b,angle_c) incenter(center_type) "
    "ceva(stevart) varignon(ptolemy) | "
    "STAT: coordinate(x1,y1,x2,y2 | slope,intercept | point1=a,b) "
    "number_line(start,end,mark1..5,point) "
    "bar_chart(bar1..7,label1..7) "
    "pie_chart(slice1..6,label1..6) "
    "clock(hour,minute) vector(ax,ay,bx,by) homothety(scale) | "
    "PUZZLE: grid(cell1..9) crossword(cell1..5) labyrinth(start,end,path1..3) scale(left_side,right_side)"
)


def _get_age_rule(age_group: str) -> str:
    return _AGE_RULES[_normalize_age_group(age_group)]


def _normalize_age_group(age_group: str) -> str:
    raw = (age_group or "").lower()
    if any(token in raw for token in ("6-9", "boshlang")):
        return "6-9"
    if any(token in raw for token in ("10-13", "orta", "standard")):
        return "10-13"
    if any(token in raw for token in ("18+", "universitet", "university")):
        return "18+"
    if any(token in raw for token in ("14-17", "14+", "olimpiada", "akademik")):
        return "14-17"
    return "10-13"


def _get_age_display(age_group: str) -> str:
    return _AGE_DISPLAY[_normalize_age_group(age_group)]


_DIFFICULTY_DISPLAY = {
    "oson": "Oson (Boshlang'ich)",
    "o'rta": "O'rta (Standard)",
    "qiyin": "Qiyin (Murakkab)",
    "akademik": "Akademik (Olimpiada)",
}

_DIFFICULTY_RULES = {
    "oson": "EASY: keep it one-step, very short, with small clean numbers and zero hidden tricks.",
    "o'rta": "MEDIUM DIFFICULTY: allow up to two simple steps, but stay direct and school-level.",
    "qiyin": "HARD DIFFICULTY: avoid trivial one-operation tasks. Use a clear 2-3 step problem or a stronger concept inside the same topic.",
    "akademik": "ACADEMIC DIFFICULTY: use advanced but school-safe reasoning, olympiad/admission flavor, and never drop to trivial arithmetic.",
}


def _normalize_difficulty_level(difficulty: str | None) -> str:
    raw = _clean_text(difficulty).lower()
    if any(token in raw for token in ("oson", "boshlang", "easy", "6-9")):
        return "oson"
    if any(token in raw for token in ("qiyin", "murakkab", "hard")):
        return "qiyin"
    if any(token in raw for token in ("akademik", "olimpiada", "advanced", "14+", "14-17", "18+")):
        return "akademik"
    if any(token in raw for token in ("o'rta", "orta", "standard", "standart", "10-13")):
        return "o'rta"
    return "o'rta"


def _get_difficulty_display(difficulty: str | None) -> str:
    return _DIFFICULTY_DISPLAY.get(_normalize_difficulty_level(difficulty), _DIFFICULTY_DISPLAY["o'rta"])


def _get_level_display(age_group: str | None, difficulty: str | None = None) -> str:
    raw = _clean_text(age_group).lower()
    if any(token in raw for token in ("qiyin", "murakkab")):
        return _DIFFICULTY_DISPLAY["qiyin"]
    if any(token in raw for token in ("akademik", "olimpiada")):
        return _DIFFICULTY_DISPLAY["akademik"]
    if any(token in raw for token in ("boshlang", "6-9", "oson")):
        return _DIFFICULTY_DISPLAY["oson"]
    if any(token in raw for token in ("o'rta", "orta", "standard", "standart")):
        return _DIFFICULTY_DISPLAY["o'rta"]
    return _get_difficulty_display(difficulty or age_group)


def _resolve_grade_for_level(age_group: str | None, difficulty: str | None) -> int:
    difficulty_key = _normalize_difficulty_level(difficulty or age_group)
    normalized_age = _normalize_age_group(age_group or difficulty_key)
    if difficulty_key == "oson":
        return 3
    if difficulty_key == "o'rta":
        return 6
    if difficulty_key == "qiyin":
        return 8
    if normalized_age == "18+":
        return 11
    return 10


def _get_difficulty_rule(difficulty: str | None, quiz_type: str) -> str:
    difficulty_key = _normalize_difficulty_level(difficulty)
    base_rule = _DIFFICULTY_RULES.get(difficulty_key, _DIFFICULTY_RULES["o'rta"])
    if quiz_type == "Geometriya" and difficulty_key in {"qiyin", "akademik"}:
        return f"{base_rule} Prefer theorem-based or multi-step geometry inside the chosen topic."
    if quiz_type == "Algebra / Matematika" and difficulty_key in {"qiyin", "akademik"}:
        return f"{base_rule} Prefer equations, fractions, ratios, percentages, or multi-step arithmetic over trivial sums."
    if quiz_type in {"IQ / Tanqidiy fikrlash", "Prezident maktabi"} and difficulty_key in {"qiyin", "akademik"}:
        return f"{base_rule} Prefer stronger inference, evidence, ordering, or analytical reasoning."
    return base_rule


def _should_use_book_payload(quiz_type: str, custom_topic: str | None, difficulty: str | None) -> bool:
    difficulty_key = _normalize_difficulty_level(difficulty)
    if quiz_type in _CRITICAL_QUIZ_TYPES:
        return False
    if custom_topic:
        return False
    return difficulty_key in {"oson", "o'rta"}


_FORCE_LOCAL_AFTER_DUPLICATES = 3
_MAX_DUPLICATE_RETRIES = 6
_MAX_SLOT_ATTEMPTS = 10


def _should_force_local_retry(slot_attempts: int, duplicate_streak: int) -> bool:
    return slot_attempts >= 4 or duplicate_streak >= _FORCE_LOCAL_AFTER_DUPLICATES


def _should_allow_duplicate(slot_attempts: int) -> bool:
    return False


def _canonical_quiz_type(quiz_type: str) -> str:
    normalized = _clean_text(quiz_type).lower()
    if normalized in {"iq", "tanqidiy fikrlash", "iq / tanqidiy fikrlash"}:
        return "IQ / Tanqidiy fikrlash"
    if normalized in {"prezident", "prizident", "prezident maktabi", "prezident maktabi iq", "president school"}:
        return "Prezident maktabi"
    if normalized == "mantiq":
        return "Mantiqiy fikrlash"
    return quiz_type


_CRITICAL_QUIZ_TYPES = {"Mantiqiy fikrlash", "IQ / Tanqidiy fikrlash", "Prezident maktabi"}
_VISUAL_QUIZ_TYPES = {"Geometriya", "Boshqotirma"}
_TOPIC_ROTATIONS = {
    "Geometriya": ["Perimetr", "Yuza", "Burchaklar", "Pifagor teoremasi", "Aylana va doira"],
    "Boshqotirma": ["Qonuniyat topish", "Ketma-ketlik", "Mantiqiy jadval", "Sonli boshqotirma", "Labirint"],
    "Mantiqiy fikrlash": ["Shartli fikrlash", "Tartib va joylashuv", "Mantiqiy xulosa", "Taqqoslash"],
    "IQ / Tanqidiy fikrlash": ["Analogiya", "Kodlash", "Mantiqiy xulosa", "Tartib va joylashuv", "Matn tahlili"],
    "Prezident maktabi": ["Tanqidiy tahlil", "Matn tahlili", "Mantiqiy xulosa", "Dalil va xulosa", "Tartib va joylashuv"],
}
_ALGEBRA_TOPIC_ROTATIONS = {
    "oson": ["Qo'shish va ayirish", "Kasrlar", "Foiz", "Tenglamalar", "Tub sonlar"],
    "o'rta": ["Tenglamalar", "Kasrlar", "Foiz", "Nisbat", "Perimetr"],
    "qiyin": ["Tenglamalar", "Kasrlar", "Foiz", "Nisbat", "Kvadrat ildiz"],
    "akademik": ["Tenglamalar", "Kasrlar", "Foiz", "Nisbat", "Kvadrat ildiz"],
}


def _pick_topics(age_group: str, n: int = 5) -> str:
    """Yoshga mos n ta mavzuni qaytaradi (hammasi emas â€” token tejash)."""
    bucket = _normalize_age_group(age_group)
    topics = _TOPICS_BY_AGE.get(bucket, _TOPICS_BY_AGE["10-13"])
    picked = random.sample(topics, min(n, len(topics)))
    return ", ".join(picked)


def _pick_topics_for_type(age_group: str, quiz_type: str, n: int = 5) -> str:
    bucket = _normalize_age_group(age_group)
    base_topics = list(_TOPICS_BY_AGE.get(bucket, _TOPICS_BY_AGE["10-13"]))

    focused_topics = {
        "Geometriya": ["Perimetr", "Yuza", "Burchaklar", "Uchburchaklar", "Aylana va doira", "Koordinata"],
        "Boshqotirma": ["Qonuniyat topish", "Ketma-ketlik", "Mantiqiy jadval", "Sonli boshqotirma", "Labirint"],
        "Mantiqiy fikrlash": ["Mantiqiy xulosa", "Taqqoslash", "Jadval tahlili", "Shartli fikrlash", "Pattern"],
        "IQ / Tanqidiy fikrlash": ["Analogiya", "Kodlash", "Mantiqiy xulosa", "Tartib va joylashuv", "Matn tahlili"],
        "Prezident maktabi": ["Tanqidiy tahlil", "Matn tahlili", "Mantiqiy xulosa", "Dalil va xulosa", "Tartib va joylashuv"],
        "Algebra / Matematika": ["Tenglama", "Foiz", "Kasr", "Nisbat", "Aralash hisob"],
    }
    type_topics = focused_topics.get(quiz_type, [])
    combined = []
    for topic in type_topics + base_topics:
        if topic not in combined:
            combined.append(topic)
    picked = random.sample(combined, min(n, len(combined)))
    return ", ".join(picked)


def _needs_visual(quiz_type: str, sent_count: int = 0) -> bool:
    if quiz_type in _VISUAL_QUIZ_TYPES:
        return True
    # Algebra/Matematika uchun rasm kerak emas
    return False


def _get_shape_pool(quiz_type: str, sent_count: int, total_count: int) -> list[str]:
    if quiz_type == "Geometriya":
        return _GEOMETRY_SHAPES.copy()
    if quiz_type == "Boshqotirma":
        return _LOGIC_SHAPES.copy()
    # Algebra/Matematika uchun shakllar kerak emas
    return []


def _pick_random_shape(shape_pool: list[str], seed: str) -> str | None:
    """Random tanlash â€” deterministic seed asosida."""
    if not shape_pool:
        return None
    rng = random.Random(seed)
    return rng.choice(shape_pool)


def _get_topic_rotation_pool(quiz_type: str, difficulty: str | None = None) -> list[str]:
    canonical_type = _canonical_quiz_type(quiz_type)
    difficulty_key = _normalize_difficulty_level(difficulty)
    if canonical_type == "Algebra / Matematika":
        return list(_ALGEBRA_TOPIC_ROTATIONS.get(difficulty_key, _ALGEBRA_TOPIC_ROTATIONS["o'rta"]))
    return list(_TOPIC_ROTATIONS.get(canonical_type, []))


def _pick_planned_topic(
    quiz_type: str,
    difficulty: str | None,
    sent_count: int,
    slot_attempts: int = 1,
    last_topic: str | None = None,
) -> str | None:
    pool = _get_topic_rotation_pool(quiz_type, difficulty)
    if not pool:
        return None
    start_idx = (max(sent_count, 0) + max(slot_attempts - 1, 0)) % len(pool)
    normalized_last = _clean_text(last_topic).lower()
    for offset in range(len(pool)):
        candidate = pool[(start_idx + offset) % len(pool)]
        if normalized_last and len(pool) > 1 and _clean_text(candidate).lower() == normalized_last:
            continue
        return candidate
    return pool[start_idx]


def _should_prefer_local_channel_generation(quiz_type: str, custom_topic: str | None = None) -> bool:
    return _canonical_quiz_type(quiz_type) == "Algebra / Matematika" and not _clean_text(custom_topic)


def _clean_text(value) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    return " ".join(text.split())


def _topic_keyword_stems(text: str) -> set[str]:
    normalized = _clean_text(text).lower()
    normalized = re.sub(r"[`'â€™Ê»Ê¼]", "", normalized)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    stems = set()
    for token in tokens:
        if len(token) < 3 or token in _TOPIC_STOPWORDS:
            continue
        stems.add(token[:5])
    return stems


def _matches_required_topic(question: str, topic: str, required_topic: str | None) -> bool:
    required = _clean_text(required_topic)
    if not required:
        return True

    required_lower = required.lower()
    actual_text = _clean_text(f"{topic} {question}").lower()
    normalized_required = re.sub(r"[`'â€™Ê»Ê¼]", "", required_lower)
    required_tokens = set(re.findall(r"[a-z0-9]+", normalized_required))

    generic_critical_tokens = {
        "iq",
        "test",
        "savol",
        "savollar",
        "mantiq",
        "mantiqiy",
        "tanqidiy",
        "fikrlash",
        "prezident",
        "prizident",
        "maktabi",
        "president",
        "critical",
        "logic",
        "analitik",
    }
    broad_critical_signals = (
        "analogiya",
        "kodlash",
        "xulosa",
        "dalil",
        "tahlil",
        "tartib",
        "shart",
        "matn",
        "ketma-ket",
        "yo'nalish",
        "qarindosh",
    )
    if required_tokens and required_tokens <= generic_critical_tokens:
        return any(signal in actual_text for signal in broad_critical_signals)
    
    topic_keywords = {
        "arifmetika": ["qo'shish", "ayirish", "kopaytirish", "bo'lish", "+,", "-,", "Ã—", "Ã·", "yig'indi", "ayirma", "ko'paytma", "bo'linma", "hisoblang", "ni toping", "amallar", "arifmetika", "sonlarni", "qo'sh", "ayir", "ko'paytir", "bo'lish", "Ã—", "Ã·", "hisoblash", "yig'indisi", "ayirmasi", "ko'paytmasi", "bo'linmasi", "ni hisoblang", "amallarni bajaring"],
        "kasrlar": ["kasr", "surat", "maxraj", "aralash", "1/2", "3/4", "kasrlarni", "kasrning", "kasrga", "kasrdan", "kasrni", "kasrga", "kasrdan"],
        "tenglamalar": ["tenglama", "x=", "x +", "x -", "2x", "x ni top", "x ning qiymati", "tenglamani yech", "tenglamani yeching", "tenglamani yeching", "x+", "x-", "2x=", "3x="],
        "perimetr": ["perimetr", "atrof", "tomonlari", "yig'indisi", "kvadratning perimetri", "to'rtburchakning perimetri", "perimetri", "perimetrini", "atrofini"],
        "yuza": ["yuza", "maydon", "yuzasi", "kvadrat yuzi", "to'rtburchak yuzi", "cmÂ²", "mÂ²", "yuzasi", "yuzasini", "yuzani"],
        "geometriya": ["burchak", "uchburchak", "to'rtburchak", "aylana", "kvadrat", "tomon", "diagonal", "geometriya", "shakl", "geometrik"],
        "foiz": ["foiz", "%", "foizini", "50%", "25%", "10%", "foiz hisoblash", "foizini toping", "foizini hisobla", "foizga"],
        "daraja": ["daraja", "2Â²", "3Â²", "ildiz", "kvadrat ildiz", "âˆš", "darajaga ko'tarish", "darajani", "ildizni"],
        "tub_sonlar": ["tub son", "murakkab", "bo'luvchi", "karrali", "tubga ajratish", "tub sonlar", "tubmi", "murakkabmi"],
        "ekub_ekuk": ["EKUB", "EKUK", "eng katta umumiy", "eng kichik umumiy", "karrali", "bo'luvchilar", "umumiy"],
        "fizika": ["tezlik", "masofa", "vaqt", "kuch", "massa", "issiqlik", "elektr", "zanjir", "F=ma", "V=S/t"],
        "analogiya": ["analogiya", ":", "bog'liq", "o'xshash"],
        "kodlash": ["kod", "harf", "A=1", "B=2", "raqam"],
        "tanqidiy": ["dalil", "xulosa", "tahlil", "eng kuchli", "qo'llab-quvvatlaydi"],
        "mantiq": ["xulosa", "shart", "demak", "tartib", "chap", "o'ng"],
        "prezident": ["xulosa", "dalil", "analogiya", "tartib", "tahlil", "matn"],
    }
    
    for topic_name, keywords in topic_keywords.items():
        if topic_name in required_lower:
            question_lower = question.lower()
            for kw in keywords:
                if kw in question_lower:
                    return True
            return False
    
    required_stems = _topic_keyword_stems(required)
    if not required_stems:
        return True

    actual_stems = _topic_keyword_stems(actual_text)
    match_count = len(required_stems & actual_stems)
    min_match = 1 if len(required_stems) == 1 else 2
    return match_count >= min(min_match, len(required_stems))


def _infer_shape_from_topic(custom_topic: str | None, quiz_type: str) -> str | None:
    topic = _clean_text(custom_topic).lower()
    if not topic:
        return None

    shape_map = (
        (("aylana", "doira", "radius", "diametr"), "circle"),
        (("to'g'ri burchak", "togri burchak", "pifagor"), "right_triangle"),
        (("uchburchak",), "isosceles_triangle"),
        (("to'rtburchak", "tortburchak", "perimetr"), "rectangle"),
        (("trapets", "trapezi"), "trapezoid"),
        (("romb",), "rhombus"),
        (("parallelo",), "parallelogram"),
        (("olti burchak", "hexagon"), "hexagon"),
        (("koordinat",), "coordinate"),
        (("son o'qi", "son oki"), "number_line"),
        (("diagram", "jadval"), "bar_chart"),
        (("soat", "vaqt"), "clock"),
        (("vektor",), "vector"),
        (("labirint",), "labyrinth"),
        (("qonuniyat", "ketma-ket", "ketmaket"), "grid"),
        (("tarozi", "tenglama tarozi"), "scale"),
    )

    for keywords, shape in shape_map:
        if any(keyword in topic for keyword in keywords):
            return shape

    if quiz_type == "Boshqotirma":
        return "grid"
    return None


def _build_visual_prompt(
    q_data: dict,
    quiz_type: str,
    required_topic: str | None = None,
) -> str:
    topic = _clean_text(required_topic) or _clean_text(q_data.get("topic")) or quiz_type
    question = _clean_text(q_data.get("question"))

    base = (
        "Create a clean educational illustration for a school math quiz. "
        f"Question context: {question}. "
        "No generic stock photo, no unrelated objects, no watermark, no logo, no decorative background text. "
        "Use a simple light background and one clear central composition."
    )

    if quiz_type in ("Boshqotirma", "Mantiqiy fikrlash"):
        templates = [
            "Style: arithmetic grid puzzle like a 5x5 or 6x6 table with plus/minus/multiply/divide symbols inside cells and result totals on the borders. Use outlined boxes, some shaded cells, and a single question-mark box to solve.",
            "Style: shape-value puzzle with circles, squares, triangles. Show equations in rows/columns with unknown indicated by '?' in one shape. Flat color shapes, no text except numbers and operators.",
            "Style: columnar arithmetic rebus with blank squares or letters standing for digits, stacked addition/multiplication, and a boxed result. Keep it on graph-paper style light grid.",
            "Style: flowchart arithmetic with nodes (circles/rectangles) connected by arrows, each arrow annotated by an operation. One node is '?'. Keep layout tidy and minimal.",
            "Style: 3x3 or 4x4 mini crossword-style math puzzle with numbers in some cells, operators between them, and a boxed question mark cell to fill.",
        ]
        idx = abs(hash(question)) % len(templates)
        return (
            f"{base} "
            "Make it a logic/brain-teaser visual; topic label not needed. "
            f"{templates[idx]}"
        )

    if quiz_type == "Geometriya":
        return (
            f"{base} Topic: {topic}. "
            "Style: precise classroom geometry visual, neat 2D educational diagram or textbook illustration. "
            "Show only the relevant mathematical object or shape implied by the topic and question. "
            "Keep labels minimal and readable."
        )

    return (
        f"{base} Topic: {topic}. "
        "Style: simple educational math illustration with only the necessary objects for the problem."
    )


def _contains_forbidden_content(text: str, age_group: str) -> bool:
    normalized = _clean_text(text).lower()
    group = _normalize_age_group(age_group)
    tokens = _FORBIDDEN_TOKENS_BY_AGE.get(group, ())
    
    for token in tokens:
        # Agar tokenda probel bo'lsa (masalan " x "), uni to'g'ridan-to'g'ri qidiramiz
        if " " in token:
            if token in f" {normalized} ":
                return True
        elif any(c in token for c in "Â²âˆšÏ€^"):
            # Maxsus belgilar uchun oddiy qidiruv (word binary belgilarga nisbatan injiq)
            if token in normalized:
                return True
        else:
            # Aks holda so'z chegarasi bilan qidiramiz (\b)
            # Bu "sin" ni "sinf" ichidan topishni oldini oladi
            pattern = rf"\b{re.escape(token)}\b"
            if re.search(pattern, normalized):
                return True
    return False


def _normalize_options(options) -> list[str]:
    if not isinstance(options, list):
        return []
    normalized = [_clean_text(item) for item in options if _clean_text(item)]
    return normalized[:4]


def _build_fallback_explanation(question: str, correct_option: str) -> str:
    return (
        f"Masalani bosqichma-bosqich tahlil qiling: {question}. "
        f"Variantlarni solishtirganda mos javob topiladi. Javob: {correct_option}"
    )


def _build_numeric_options(correct_value: int, rng: random.Random) -> tuple[list[str], int]:
    deltas = [-3, -2, -1, 1, 2, 3, 4, 5]
    rng.shuffle(deltas)
    values = [correct_value]
    for delta in deltas:
        candidate = correct_value + delta
        if candidate > 0 and candidate not in values:
            values.append(candidate)
        if len(values) == 4:
            break
    while len(values) < 4:
        candidate = correct_value + len(values) + 2
        if candidate not in values:
            values.append(candidate)
    rng.shuffle(values)
    return [str(value) for value in values], values.index(correct_value)


def _build_local_fallback_quiz(
    age_group: str,
    quiz_type: str,
    chosen_shape: str | None,
    custom_topic: str | None,
    sent_count: int,
    needs_image: bool,
    difficulty: str | None = None,
) -> dict:
    bucket = _normalize_age_group(age_group)
    difficulty_key = _normalize_difficulty_level(difficulty or age_group)
    seed = f"{bucket}|{quiz_type}|{chosen_shape}|{custom_topic}|{sent_count}"
    rng = random.Random(seed)
    topic = custom_topic or quiz_type
    hint = "null"

    if custom_topic:
        return topic_context_service.build_local_topic_question(
            topic=custom_topic,
            grade=_resolve_grade_for_level(age_group, difficulty_key),
            difficulty=difficulty_key,
            quiz_type=quiz_type,
            seed=seed,
        )

    if quiz_type == "Algebra / Matematika":
        topic_pool = _get_topic_rotation_pool(quiz_type, difficulty_key)
        selected_topic = topic_pool[sent_count % len(topic_pool)]
        return topic_context_service.build_local_topic_question(
            topic=selected_topic,
            grade=_resolve_grade_for_level(age_group, difficulty_key),
            difficulty=difficulty_key,
            quiz_type=quiz_type,
            seed=seed,
        )

    if quiz_type == "Geometriya":
        if difficulty_key in {"qiyin", "akademik"} or chosen_shape in {"right_triangle", "pythagoras"}:
            a, b, c = rng.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17)])
            question = f"Katetlari {a} sm va {b} sm bo'lgan to'g'ri burchakli uchburchakda gipotenuzani toping."
            correct = c
            topic = custom_topic or "Pifagor teoremasi"
            hint = f"right_triangle|bottom={a}|left={b}|right=x"
            options, correct_index = _build_numeric_options(correct, rng)
        elif chosen_shape == "circle":
            radius = rng.randint(2, 9)
            correct = radius * 2
            question = f"Aylana radiusi {radius} sm bo'lsa, diametri necha sm bo'ladi?"
            topic = custom_topic or "Aylana va doira"
            hint = f"circle|radius_1={radius}|diameter=x"
        elif chosen_shape == "rectangle":
            a = rng.randint(3, 10)
            b = rng.randint(2, 8)
            correct = 2 * (a + b)
            question = f"To'rtburchakning tomonlari {a} sm va {b} sm. Perimetrini toping."
            topic = custom_topic or "Perimetr"
            hint = f"rectangle|bottom={a}|left={b}|perimeter=x"
        else:
            a = rng.randint(4, 12)
            b = rng.randint(3, 10)
            correct = a + b
            question = f"To'g'ri burchakli uchburchakning katetlari {a} va {b}. Ikki katet yig'indisini toping."
            topic = custom_topic or "Uchburchaklar"
            hint = f"right_triangle|bottom={a}|left={b}|right=x"
        options, correct_index = _build_numeric_options(correct, rng)
    elif quiz_type == "Boshqotirma":
        start = rng.randint(2, 6)
        step = rng.randint(2, 5)
        seq = [start + step * i for i in range(4)]
        correct = start + step * 4
        question = (
            f"Qonuniyatni toping: {seq[0]}, {seq[1]}, {seq[2]}, {seq[3]}, x. "
            "x o'rniga qaysi son keladi?"
        )
        topic = custom_topic or "Qonuniyat topish"
        hint = _get_default_hint(chosen_shape or "grid")
        options, correct_index = _build_numeric_options(correct, rng)
    elif quiz_type == "Mantiqiy fikrlash":
        scenarios = [
            (
                "Agar chiroq yonsa, elektr bor. Elektr yo'q. Qaysi xulosa to'g'ri?",
                "Chiroq yonmaydi",
                ["Chiroq albatta yonadi", "Elektr tez orada keladi", "Hech narsa aniqlab bo'lmaydi"],
                "Shartli fikrlash",
            ),
            (
                "Ali Bekzoddan keyin turadi. Bekzod esa Dildoradan keyin turadi. Kim birinchi turadi?",
                "Dildora",
                ["Ali", "Bekzod", "Aniq emas"],
                "Tartib va joylashuv",
            ),
            (
                "Barcha ko'k papkalar yopiq. Hech bir yopiq papka stol ustida emas. Qaysi xulosa albatta to'g'ri?",
                "Hech bir ko'k papka stol ustida emas",
                ["Stol ustidagi papkalar ko'k", "Barcha papkalar yopiq", "Ko'k papkalarning hammasi stol ustida"],
                "Mantiqiy xulosa",
            ),
        ]
        question, correct, options_tail, topic = scenarios[sent_count % len(scenarios)]
        options = [correct, *options_tail]
        rng.shuffle(options)
        correct_index = options.index(correct)
    elif quiz_type == "IQ / Tanqidiy fikrlash":
        templates = [
            (
                "Analogiyani toping: Ko'z : ko'rish = quloq : ?",
                "eshitish",
                ["hid bilish", "yurish", "o'lchash"],
                "Analogiya",
            ),
            (
                "A=1, B=2, C=3 ... Z=26 bo'lsa, KITOB so'zining kodi nechaga teng?",
                "61",
                ["54", "57", "66"],
                "Kodlash",
            ),
            (
                "Nodira Malika dan oldin turadi. Malika esa Sevinchdan oldin. Kim oxirida turadi?",
                "Sevinch",
                ["Nodira", "Malika", "Aniq emas"],
                "Tartib va joylashuv",
            ),
        ]
        question, correct, options_tail, topic = templates[sent_count % len(templates)]
        topic = custom_topic or topic
        options = [correct, *options_tail]
        rng.shuffle(options)
        correct_index = options.index(correct)
    elif quiz_type == "Prezident maktabi":
        scenarios = [
            (
                "Barcha saralashdan o'tganlar ro'yxatga olingan. Aziz saralashdan o'tgan. Qaysi xulosa to'g'ri?",
                "Aziz ro'yxatga olingan",
                ["Aziz saralashdan o'tmagan", "Aziz albatta g'olib", "Aniq xulosa qilib bo'lmaydi"],
                "Mantiqiy xulosa",
            ),
            (
                "Kutubxonada jim o'qish soati joriy etilgach, bir haftada tugatilgan kitoblar soni oshdi. Bu da'voni eng kuchli qo'llab-quvvatlaydigan fakt qaysi?",
                "Jim o'qish soati boshlanganidan keyin tugatilgan kitoblar soni sezilarli ko'paygan",
                ["Kutubxonaga yangi stul keltirilgan", "Ba'zi o'quvchilar ertaroq ketgan", "Jurnal obunalari yangilangan"],
                "Tanqidiy tahlil",
            ),
            (
                "1) Barcha saralanganlar suhbatga chaqiriladi. 2) Hech bir suhbatga chaqirilmagan o'quvchi yakuniy bosqichga o'tmaydi. Qaysi xulosa albatta to'g'ri?",
                "Saralangan har bir o'quvchi yakuniy bosqichga o'tmasligi mumkin, lekin suhbatga chaqiriladi",
                ["Saralanganlarning barchasi yakuniy bosqichga o'tadi", "Suhbatga chaqirilmaganlar saralangan bo'ladi", "Yakuniy bosqichga o'tganlar saralanmagan bo'ladi"],
                "Shartli fikrlash",
            ),
        ]
        question, correct, options_tail, topic = scenarios[sent_count % len(scenarios)]
        topic = custom_topic or topic
        options = [correct, *options_tail]
        rng.shuffle(options)
        correct_index = options.index(correct)
    else:
        if difficulty_key == "oson":
            a = rng.randint(2, 9)
            b = rng.randint(1, 9)
            correct = a + b
            question = f"{a} + {b} = x. x ni toping."
            topic = custom_topic or "Qo'shish va ayirish"
            options, correct_index = _build_numeric_options(correct, rng)
        elif difficulty_key in {"qiyin", "akademik"}:
            x = rng.randint(4, 16 if difficulty_key == "qiyin" else 20)
            multiplier = rng.randint(2, 4)
            add = rng.randint(3, 11)
            total = multiplier * x + add
            correct = x
            question = f"{multiplier}x + {add} = {total}. x ni toping."
            topic = custom_topic or "Tenglamalar"
            options, correct_index = _build_numeric_options(correct, rng)
        elif bucket == "14-17":
            a = rng.randint(3, 12)
            b = rng.randint(2, 9)
            correct = a * b
            question = f"{a} ta guruhning har birida {b} tadan element bor. Jami nechta element bo'ladi?"
            topic = custom_topic or "Aralash hisob"
            options, correct_index = _build_numeric_options(correct, rng)
        else:
            a = rng.randint(10, 40)
            b = rng.randint(2, 9)
            correct = a - b
            question = f"{a} dan {b} ni ayiring. Natijani toping."
            topic = custom_topic or "Aralash hisob"
            options, correct_index = _build_numeric_options(correct, rng)
        if needs_image and chosen_shape:
            hint = _get_default_hint(chosen_shape)

    correct_option = options[correct_index]
    return {
        "question": question,
        "topic": topic,
        "options": options,
        "correct_index": correct_index,
        "explanation": _build_fallback_explanation(question, correct_option),
        "geometry_hint": hint,
    }


def _validate_quiz_payload(
    q_data: dict,
    age_group: str,
    quiz_type: str,
    needs_image: bool,
    required_topic: str | None = None,
    difficulty: str | None = None,
) -> tuple[bool, str, dict]:
    if not isinstance(q_data, dict):
        return False, "AI natijasi dict emas", {}

    question = _clean_text(q_data.get("question"))
    topic = _clean_text(q_data.get("topic")) or quiz_type
    options = _normalize_options(q_data.get("options"))
    hint = _clean_text(q_data.get("geometry_hint"))
    question_lower = question.lower()
    topic_lower = topic.lower()

    if len(question) < 12:
        return False, "Savol juda qisqa", {}
    if len(options) != 4:
        return False, "Variantlar soni 4 ta emas", {}
    if len(set(opt.lower() for opt in options)) != 4:
        return False, "Variantlar takrorlangan", {}

    try:
        correct_index = int(q_data.get("correct_index", 0))
    except Exception:
        return False, "correct_index noto'g'ri", {}
    if correct_index not in (0, 1, 2, 3):
        return False, "correct_index diapazondan tashqarida", {}

    full_text = " ".join([question, topic, *options, _clean_text(q_data.get("explanation"))])
    full_text_lower = full_text.lower()
    if _contains_forbidden_content(full_text, age_group):
        return False, "Yoshga mos bo'lmagan kontent aniqlandi", {}

    if required_topic and not _matches_required_topic(question, topic, required_topic):
        return False, "Savol foydalanuvchi kiritgan mavzuga mos emas", {}

    # Mavzuga mos kalit so'zlar tekshiruvi
    topic_keywords = {
        "arifmetika": ["qo'shish", "ayirish", "ko'paytirish", "bo'lish", "yig'indi", "ayirma", "ko'paytma", "bo'linma", "+", "-", "Ã—", "Ã·", "son"],
        "kasrlar": ["kasr", "surat", "maxraj", "aralash", "kasrlarni", "kasrga", "kasrdan", "1/2", "3/4", "/"],
        "tenglamalar": ["tenglama", "x=", "x+", "x-", "xÃ—", "xÃ·", "yeching", "toping", "tenglamani"],
        "perimetr": ["perimetr", "atrof", "tomonlar", "yig'indisi", "kvadrat", "to'rtburchak"],
        "yuza": ["yuza", "maydon", "kvadrat", "to'rtburchak", "uchburchak", "burchak"],
        "geometriya": ["uchburchak", "to'rtburchak", "aylana", "doira", "burchak", "radius", "perimetr", "yuza", "shakl", "kvadrat", "tomon"],
        "foiz": ["foiz", "foizga", "foizdan", "%", "foizini", "qismi"],
        "nisbat": ["nisbat", "proporsiya", "nisbatda", "mutanosib"],
        "analogiya": ["analogiya", ":", "bog'liq", "o'xshash"],
        "kodlash": ["kod", "harf", "A=1", "B=2", "raqami"],
        "tanqidiy": ["dalil", "xulosa", "eng kuchli", "qo'llab-quvvatlaydi", "tahlil"],
        "mantiq": ["xulosa", "shart", "demak", "tartib", "chap", "o'ng"],
        "prezident": ["xulosa", "dalil", "tahlil", "analogiya", "tartib", "shart"],
    }
    
    if required_topic:
        required_topic_lower = required_topic.lower()
        matched = False
        for key, keywords in topic_keywords.items():
            if key in required_topic_lower:
                if any(word in full_text_lower for word in keywords):
                    matched = True
                    break
        if not matched and required_topic_lower in topic_keywords:
            return False, f"Savol '{required_topic}' mavzusiga mos emas", {}

    # Geometriya uchun kalit so'zlar ro'yxatini kengaytiramiz (ayniqsa kichik yoshdagilar uchun)
    geo_keywords = (
        "uchburchak", "to'rtburchak", "aylana", "doira", "burchak", 
        "radius", "perimetr", "yuza", "shakl", "kvadrat", "tomon", 
        "kesma", "parallel", "sm", "metr", "maydon", "diametr"
    )
    if quiz_type == "Geometriya" and not any(word in question_lower for word in geo_keywords):
        return False, "Geometriya savoli yetarli darajada geometriyaga o'xshamaydi", {}

    logic_signals = (
        "qonuniyat", "ketma-ket", "toping", "mantiq", "jadval", "labirint",
        "analogiya", "dalil", "xulosa", "shart", "chap", "o'ng", "kod", "+", "-", "Ã—", "Ã·"
    )
    if quiz_type in {"Boshqotirma", "Mantiqiy fikrlash", "IQ / Tanqidiy fikrlash", "Prezident maktabi"} and not any(word in full_text_lower for word in logic_signals):
        return False, "Boshqotirma/mantiq savoli yetarli signal bermadi", {}

    if quiz_type in {"IQ / Tanqidiy fikrlash", "Prezident maktabi"}:
        word_count = len(re.findall(r"[A-Za-zÊ»Ê¼â€™'-]+", question))
        textual_options = sum(1 for opt in options if re.search(r"[A-Za-zÊ»Ê¼â€™'-]", opt))
        if word_count < 5:
            return False, "IQ/tanqidiy savol juda qisqa", {}
        if textual_options < 3:
            return False, "IQ/tanqidiy variantlar juda sodda yoki faqat sonlardan iborat", {}

    if quiz_type == "Prezident maktabi" and len(question) < 24:
        return False, "Prezident maktabi savoli juda sodda yoki qisqa", {}

    if quiz_type == "Prezident maktabi":
        president_signals = (
            "xulosa", "dalil", "tahlil", "qo'llab-quvvatlaydi",
            "albatta", "aniq", "shart", "saralash", "ro'yxat", "suhbat",
        )
        if not any(word in full_text_lower for word in president_signals):
            return False, "Prezident maktabi savoli yetarli analitik signal bermadi", {}

    difficulty_key = _normalize_difficulty_level(difficulty or age_group)
    if quiz_type == "Algebra / Matematika" and difficulty_key in {"qiyin", "akademik"}:
        hard_signals = (
            "x", "tenglama", "kasr", "foiz", "nisbat", "proporsiya", "ildiz",
            "daraja", "formula", "perimetr", "yuza", "gipotenuza", "funksiya",
        )
        raw_operation = bool(re.fullmatch(r"\d+\s*[-+*/×÷]\s*\d+\s*[=?]?", question_lower))
        if raw_operation and not any(signal in full_text_lower for signal in hard_signals):
            return False, "Savol tanlangan qiyinlikka nisbatan juda sodda", {}

    explanation = _clean_text(q_data.get("explanation"))
    if len(explanation) < 18:
        explanation = _build_fallback_explanation(question, options[correct_index])
    if "javob:" not in explanation.lower():
        explanation = f"{explanation} Javob: {options[correct_index]}"

    if needs_image and not hint:
        hint = "null"

    return True, "", {
        "question": question,
        "topic": _clean_text(required_topic) or topic,
        "options": options,
        "correct_index": correct_index,
        "explanation": explanation,
        "geometry_hint": hint or "null",
    }


def run_ai_title_generation(
    api_key: str,
    service: str,
    score: int,
    current_title: str,
    username: str,
    is_correct: bool,
) -> str:
    """(Role: title_gen) Foydalanuvchi natijasiga qarab motivatsion/kulgili 1-2 jumla."""
    result = "TO'G'RI topdi" if is_correct else "XATO ishladi"
    prompt = (
        f"{username} ({current_title}, {score} ball) {result}. "
        "Unga 1-2 gap quvnoq/motivatsion O'zbek izohi yoz."
    )

    messages = [
        {"role": "system", "content": _SYSTEM_TITLE},
        {"role": "user", "content": prompt},
    ]
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"messages": messages, "temperature": 0.85, "max_tokens": 80}

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
    else:  # groq (default)
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload["model"] = "llama-3.3-70b-versatile"

    response = requests.post(url, headers=headers, json=payload, timeout=20)
    if response.status_code != 200:
        if response.status_code == 429:
            raise Exception(f"RateLimitExhausted: {response.text}")
        raise Exception(f"API Error ({service}): {response.text}")

    resp_json = response.json()
    return resp_json["choices"][0]["message"]["content"].strip()


# Mavzu ro'yxatlari (yoshga va turga qarab AI ga beriladi)
_TOPICS_BY_AGE = {
    "6-9": [
        "Qo'shish va ayirish (1-20)",
        "Ko'paytirish jadval (2-9)",
        "Sodda geometrik shakllar (kvadrat, uchburchak, aylana)",
        "Vaqt: soat va daqiqa",
        "Uzunlik: sm va m",
        "Og'irlik: kg va g",
        "Sonlarni solishtirish (< > =)",
        "Yetishmayotgan son (x+5=8)",
        "Juft va toq sonlar",
        "Mevalarda hisob (amaliy masala)",
        "Ketma-ket sonlar (2, 4, 6, ?)",
        "Pul hisoblash (so'm)",
        "Shakllarni chizish",
        "Qo'shni sonlar",
        "Son tarkibi (7 = 3 + ?)",
        "Tartiblash (katta-kichik)",
        "Vaqt oralig'i",
        "Qo'shish va ayirish (20-100)",
        "Sodda tenglamalar",
        "Shakllarning tomonlari",
        "Misol yechish (+, -, Ã—)",
        "Bo'lish asoslari",
        "Raqamlar ketma-ketligi",
        "Eng katta va eng kichik",
        "Tog'ri va notog'ri javoblar",
    ],
    "10-13": [
        "Kasr va aralash son",
        "Kasrlarni qo'shish va ayirish",
        "Kasrlarni ko'paytirish va bo'lish",
        "Foiz hisobi (10%, 25%, 50%)",
        "Nisbat va proporsiya",
        "Oddiy tenglama (x+5=10, 2x=8)",
        "Perimetr va yuza (kvadrat, to'rtburchak)",
        "Pifagor teoremasi (3-4-5)",
        "Burchaklar yig'indisi (uchburchak)",
        "Tub va murakkab sonlar",
        "Bo'luvchilar va karralilar",
        "EKUB va EKUK",
        "Koordinatalar tekisligi",
        "Sonlarni yaxlitlash",
        "O'rtacha qiymat",
        "Daraja va ildiz",
        "Algebraik ifodalar",
        "Tenglamalar sistemasi",
        "Geometrik shakllar perimetri",
        "Aylana uzunligi va yuzi",
        "Uchburchak yuzi",
        "To'rtburchaklar turlari",
        "Masshtab",
        "Harakat masalalari",
        "Arifmetika: qo'shish, ayirish, ko'paytirish, bo'lish",
        "Sonlarni taqqoslash (katta, kichik, teng)",
        "Ketma-ketlik va qonuniyat",
        "Mantiqiy masalalar",
        "Jadval va diagrammalar",
        "Birliklarni almashtirish",
        "Vaqt masalalari (soat, daqiqa, kun)",
        "Pul masalalari",
        "Og'irlik va hajm masalalari",
        "Perimetr hisoblash",
        "Yuza hisoblash",
        "Burchak turlari (o'tkir, to'g'ri, o'tmas)",
        "Simmetriya",
        "Koordinata tizimi",
        "Sonlarni yaxlitlash",
        "O'rtacha qiymat",
        "Nisbat va foiz",
        "Tenglamalar yechish",
        "Ifodalarni soddalashtirish",
        "Fizika: tezlik, masofa, vaqt",
        "Fizika: kuch va massa",
        "Fizika: issiqlik miqdori",
        "Fizika: elektr zanjiri",
        "Algebra: algebraik ifodalar",
        "Algebra: ko'phadlar",
        "Algebra: darajalar va ildizlar",
    ],
    "14-17": [
        "Kvadrat tenglama (axÂ²+bx+c=0)",
        "Trigonometriya (sin, cos, tan)",
        "Pifagor teoremasi (murakkab)",
        "Aylana va sektorlar",
        "Ko'pburchak yuzasi",
        "Arifmetik progressiya",
        "Geometrik progressiya",
        "Logarifm va uning xossalari",
        "Ko'rsatkichli tenglama",
        "Kombinatorika (cho'ntak, jadval)",
        "Ehtimollar asoslari",
        "Burchaklarning sinus va kosinus teoremasi",
        "Vektorlar bilan ishlash",
    ],
    "18+": [
        "Aniq integral",
        "Noaniq integral",
        "Hosila (differensiallash)",
        "Limitlar",
        "Matritsalar",
        "Kompleks sonlar",
        "Vektorlar (3D)",
        "Murakab stereometriya",
        "Ehtimollar nazariyasi",
        "Matematik statistika",
        "Differensial tenglamalar",
    ],
}


def _get_topics_for_age(age_group: str) -> str:
    """Yosh guruhiga mos mavzular ro'yxatini qaytaradi."""
    for key, topics in _TOPICS_BY_AGE.items():
        if key in age_group:
            return ", ".join(topics)
    return ", ".join(_TOPICS_BY_AGE["10-13"])


def run_ai_generation(
    api_key: str,
    service: str,
    age_group: str,
    quiz_type: str,
    random_seed: str = "V-1",
    attempt_idx: int = 0,
    total_count: int = 30,
    chosen_shape: str | None = None,
    custom_topic: str | None = None,
    difficulty: str | None = None,
) -> dict:
    """
    (Role: quiz_gen) AI dan O'zbek tilidagi matematik quiz generatsiya qiladi.
    chosen_shape â€” Python tomonidan tanlangan shakl (kafolatlangan navbat).
    """
    # â”€â”€ 2-qatlam: shakl majburiy bloki (compact) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    difficulty_key = _normalize_difficulty_level(difficulty or age_group)
    normalized_age = _normalize_age_group(age_group or difficulty_key)
    display_age = _get_level_display(age_group, difficulty_key)

    shape_block = ""
    if chosen_shape:
        ex = _get_default_hint(chosen_shape)
        shape_block = f"SHAPE REQUIRED: geometry_hint must start with '{chosen_shape}'. Example: {ex}"
    elif quiz_type == "Geometriya" and not custom_topic:
        shape = random.choice(
            [
                "circle",
                "rectangle",
                "trapezoid",
                "rhombus",
                "right_triangle",
                "isosceles_triangle",
                "parallelogram",
                "hexagon",
            ]
        )
        shape_block = f"SHAPE REQUIRED: geometry_hint must start with '{shape}'."

    # â”€â”€ Yoshga mos qoida va mavzular â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    age_rule = _get_age_rule(normalized_age)
    difficulty_rule = _get_difficulty_rule(difficulty_key, quiz_type)
    
    # Grade asosida mavzular olish (topic_registry dan)
    internet_context = ""
    generation_notes = topic_context_service.build_generation_notes(
        custom_topic,
        normalized_age,
        difficulty_key,
        quiz_type,
    )
    if custom_topic:
        topics_str = custom_topic
        topic_rule = f"TOPIC REQUIRED: Formulate the question STRICTLY on: {custom_topic}. Stay simple and topic-faithful.\n"
        topic_context = topic_context_service.fetch_internet_context(custom_topic, quiz_type)
        internet_msg = topic_context.to_prompt_text()
        if internet_msg:
            internet_context = (
                f"{internet_msg}"
                "Use this context only to make the example realistic and aligned with the topic.\n"
            )
    else:
        topics_str = _pick_topics_for_type(normalized_age, quiz_type, n=8)
        topic_rule = ""

    # â”€â”€ Image qoidasi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    needs_img = _needs_visual(quiz_type)
    img_rule = "IMAGE REQUIRED (x in hint too)" if needs_img else "image optional"

    # â”€â”€ Mantiqiy fikrlash / Boshqotirma unchun maxsus matematika qoidasi â”€â”€â”€
    math_op_rule = ""
    if quiz_type == "Boshqotirma":
        math_op_rule = "PUZZLE: Use ONLY grid/crossword/labyrinth/scale shapes. NO hf_prompt. Numbers in cells."
    elif quiz_type == "Mantiqiy fikrlash":
        math_op_rule = "LOGIC: Prefer condition, ordering, inference, and verbal reasoning. Avoid forcing image-dependent shapes unless the topic clearly needs a diagram."
    elif quiz_type == "IQ / Tanqidiy fikrlash":
        math_op_rule = "CRITICAL THINKING: Prefer analogy, coding, ordering, data interpretation, and verbal logic. Avoid childish examples and avoid image-dependent puzzles."
    elif quiz_type == "Prezident maktabi":
        math_op_rule = "ADMISSION STYLE: Use advanced verbal/analytical reasoning, evidence-based conclusion, ordering, and inference. Avoid easy arithmetic and avoid image-dependent puzzles."

# â”€â”€ Asosiy prompt (tejamkor) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    variety_rules = ""
    if custom_topic:
        topic_lower = custom_topic.lower()
        if "arifmetika" in topic_lower or "qo'shish" in topic_lower or "ayirish" in topic_lower or "kopaytirish" in topic_lower or "bolish" in topic_lower:
            variety_rules = "VARY the operations: for addition use +, for subtraction use -, for multiplication use Ã—, for division use Ã·. Use DIFFERENT numbers each time (not same 5+3 repeatedly). Mix operations!"
        elif "kasr" in topic_lower:
            variety_rules = "VARY: use different denominators (2,3,4,5,6,8,10,12), different operations (add/subtract/multiply/divide), different fraction types (proper/improper/mixed). Example: 1/2+1/4, 3/4-1/8, 2/3Ã—1/6, 5/8Ã·1/4"
        elif "tenglama" in topic_lower:
            variety_rules = "VARY the equation types: x+5=10, 2x=8, 15-x=7, 3x+2=11, x/4=3, 2x-3=7, x+8=15. Put x in DIFFERENT positions each time."
        elif "perimetr" in topic_lower or "yuza" in topic_lower:
            variety_rules = "VARY: calculate perimeter of square (side=4), rectangle (3Ã—5), triangle. Calculate area of different shapes. Use DIFFERENT side lengths each time."
        elif "foiz" in topic_lower or "nisbat" in topic_lower:
            variety_rules = "VARY: 10%, 20%, 25%, 50%, 75% of different numbers. Different question types (find %, find number, increase/decrease by %). Mix it up!"
        elif "pifagor" in topic_lower:
            variety_rules = "VARY the Pythagoras task type: find hypotenuse, find missing leg, rectangle diagonal, verify a^2+b^2=c^2, or square-on-hypotenuse area. Do NOT repeat only one pattern."
        elif "geometriya" in topic_lower or "burchak" in topic_lower:
            variety_rules = "VARY: different shapes (triangle, square, rectangle, circle), different angles (30Â°, 45Â°, 60Â°, 90Â°), different question types (find angle, find side, find perimeter)."
        elif "aylana" in topic_lower or "doira" in topic_lower:
            variety_rules = "VARY: ask radius from diameter, diameter from radius, circumference with a stated pi assumption, or area. Change both numbers and task style."
        elif "ehtimol" in topic_lower:
            variety_rules = "VARY: red/blue/green outcomes, complement probability, and different total counts. Do not repeat the same ball-color question form."
        elif "ildiz" in topic_lower or "daraja" in topic_lower:
            variety_rules = "VARY: direct square root, inverse square question, root of an expression, square value, cube value, and power expressions. Avoid repeating only one root form."
        elif "ekub" in topic_lower or "ekuk" in topic_lower:
            variety_rules = "VARY: direct EKUB, direct EKUK, choose the correct pair for a target EKUB/EKUK, and change the number pairs each time."
        elif "tub" in topic_lower or "karrali" in topic_lower or "boluvchi" in topic_lower:
            variety_rules = "VARY: find prime/composite numbers, find factors of different numbers (12, 18, 24, 30), find multiples of different numbers. Use different numbers!"
        else:
            variety_rules = "VARY: use completely different numbers and question format than before. Make each question UNIQUE!"
    
    prompt = (
        f"Seed:V-{random_seed} Q:{attempt_idx + 1}/{total_count} "
        f"Age:{display_age} Type:{quiz_type}\n"
        f"LEVEL: {age_rule}\n"
        f"DIFFICULTY PROFILE: {difficulty_rule}\n"
        f"{topic_rule}"
        f"TOPIC CANDIDATES: {topics_str}\n"
        f"{internet_context}"
        f"SIMPLICITY RULE: {generation_notes}\n"
        f"AGE-APPROPRIATE RULE: {age_rule}. Strictly follow this level.\n"
        f"STRICT FORBIDDEN FOR {display_age}: {', '.join(_FORBIDDEN_TOKENS_BY_AGE.get(normalized_age, ()))}.\n"
        "DO NOT use these forbidden terms in question, options, or explanation.\n"
        "WRITE 1 clear Uzbek question about the TOPIC.\n"
        "Keep it short, direct, and easy to understand.\n"
        "Prefer one-step or two-step school-level problems with clean numbers.\n"
        f"{variety_rules}\n"
        "Use variety: different numbers, different question types (real-world word problem, calculate, compare, etc.)\n"
        "Logic and facts must be 100% correct.\n"
        "Explanation: concise, step-by-step, ending with 'Javob: ...'.\n"
        f"{math_op_rule}\n"
        f"HINT FORMAT: SHAPE|key=val|... (unknown=x or ?)\n"
        f"SHAPES: {_SHAPES_REF}\n"
        f"{shape_block}\n"
        f"IMAGE: {img_rule}\n"
        "CRITICAL: Each question must be UNIQUE and CREATIVE!\n"
        "IMPORTANT: Base the question on the provided topic. Repeat the chosen topic in the JSON 'topic' field.\n"
        "OUTPUT JSON ONLY (no markdown blocks):\n"
        '{"question":"...","options":["correct","wrong1","wrong2","wrong3"],'
        '"correct_index":N,"explanation":"... Javob:...","topic":"...",'
        '"geometry_hint":"SHAPE|..."}'
    )

    messages = [
        {"role": "system", "content": _SYSTEM_QUIZ},
        {"role": "user", "content": prompt},
    ]

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "messages": messages,
        "temperature": 0.72,
        "max_tokens": 700,
        "response_format": {"type": "json_object"},
    }

    # Xizmat turiga qarab URL va Model
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
    elif service == "huggingface":
        url = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.3-70B-Instruct/v1/chat/completions"
        payload["model"] = "meta-llama/Llama-3.3-70B-Instruct"
    else:  # groq (default)
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload["model"] = "llama-3.3-70b-versatile"

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)

        # HF yoki ba'zi provayderlar response_format ni qo'llab-quvvatlamasligi mumkin
        if response.status_code == 400 and "response_format" in response.text:
            payload_retry = {k: v for k, v in payload.items() if k != "response_format"}
            response = requests.post(
                url, headers=headers, json=payload_retry, timeout=60
            )

        if response.status_code != 200:
            if response.status_code == 429:
                raise Exception(f"RateLimitExhausted: {response.text}")
            raise Exception(
                f"API Error ({service}): {response.status_code} - {response.text}"
            )

        resp_json = response.json()
        raw_text = resp_json["choices"][0]["message"]["content"].strip()

        # Markdown bloklarini tozalash
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]

        parsed = json.loads(raw_text.strip())
        ok, reason, cleaned = _validate_quiz_payload(
            parsed,
            display_age,
            quiz_type,
            needs_img,
            required_topic=custom_topic,
            difficulty=difficulty_key,
        )
        if not ok:
            raise Exception(f"QuizValidationError: {reason}")
        return cleaned

    except Exception as e:
        raise Exception(f"{service} Xatosi: {str(e)}")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Dublikat tekshiruvi (sinxron â€” thread da chaqiriladi)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def _sync_is_duplicate(question_text: str) -> bool:
    """
    Bir xil savol matni bazada mavjudligini tekshiradi.
    True qaytarsa â€” dublikat, o'tkazib yuborish kerak.
    """
    if not question_text:
        return False

    from database.models import Quiz, get_session

    session = get_session()
    try:
        existing = (
            session.query(Quiz).filter(Quiz.question_text == question_text).first()
        )
        return existing is not None
    finally:
        session.close()


def _normalize_quiz_signature(
    question_text: str,
    topic: str | None = None,
    quiz_type: str | None = None,
    options: list[str] | None = None,
) -> str:
    text = _clean_text(question_text).lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9%'/+*=()\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    topic_text = _clean_text(topic).lower()
    quiz_type_text = _clean_text(quiz_type).lower()
    structured_key = _extract_structured_duplicate_key(text, topic_text, quiz_type_text)
    option_part = " | ".join(sorted(_clean_text(option).lower() for option in (options or []) if _clean_text(option)))
    if structured_key:
        return f"{quiz_type_text}::{topic_text}::{structured_key}"
    return f"{quiz_type_text}::{topic_text}::{text}::{option_part}".strip(":")


def _extract_structured_duplicate_key(
    question_text: str,
    topic: str | None = None,
    quiz_type: str | None = None,
) -> str:
    text = _clean_text(question_text).lower()
    normalized = re.sub(r"\s+", " ", text)
    normalized = normalized.replace("×", "*").replace("÷", "/")
    normalized = normalized.strip()

    equation_match = re.search(r"([0-9x+\-*/() ]+=[0-9x+\-*/() ]+)", normalized)
    if equation_match:
        equation = re.sub(r"\s+", "", equation_match.group(1))
        return f"equation::{equation}"

    sqrt_match = re.search(r"(\d+)\s+ning\s+kvadrat\s+ildiz", normalized)
    if sqrt_match:
        return f"sqrt::{sqrt_match.group(1)}"

    square_match = re.search(r"(\d+)\s+ning\s+kvadratini", normalized)
    if square_match:
        return f"square::{square_match.group(1)}"

    percent_of_match = re.search(r"(\d+)\s+sonining\s+(\d+)\s+foiz", normalized)
    if percent_of_match:
        return f"percent_of::{percent_of_match.group(1)}::{percent_of_match.group(2)}"

    percent_find_whole_match = re.search(r"(\d+)\s+foizi\s+(\d+)\s+ga\s+teng", normalized)
    if percent_find_whole_match:
        return f"percent_whole::{percent_find_whole_match.group(1)}::{percent_find_whole_match.group(2)}"

    fraction_reduce_match = re.search(r"(\d+)\s*/\s*(\d+)\s+kasrni\s+qisqart", normalized)
    if fraction_reduce_match:
        return f"fraction_reduce::{fraction_reduce_match.group(1)}::{fraction_reduce_match.group(2)}"

    fraction_sum_match = re.search(r"(\d+)\s*/\s*(\d+)\s*\+\s*(\d+)\s*/\s*(\d+)", normalized)
    if fraction_sum_match:
        return (
            "fraction_sum::"
            f"{fraction_sum_match.group(1)}/{fraction_sum_match.group(2)}::"
            f"{fraction_sum_match.group(3)}/{fraction_sum_match.group(4)}"
        )

    proportion_match = re.search(r"(\d+)\s*:\s*(\d+)\s*=\s*(\d+)\s*:\s*x", normalized)
    if proportion_match:
        return (
            "proportion::"
            f"{proportion_match.group(1)}:{proportion_match.group(2)}="
            f"{proportion_match.group(3)}:x"
        )

    sequence_numbers = re.findall(r"\d+", normalized)
    if ("ketma-ket" in normalized or "qatorni davom" in normalized or "qonuniyat" in normalized) and len(sequence_numbers) >= 4:
        return "sequence::" + ",".join(sequence_numbers[:5])

    return ""


def _infer_pattern_family(question_text: str, topic: str | None = None, quiz_type: str | None = None) -> str:
    topic_text = _clean_text(topic).lower()
    quiz_type_text = _clean_text(quiz_type).lower()
    text = _clean_text(question_text).lower()
    text = re.sub(r"\s+", " ", text)

    if "foiz" in topic_text or "%" in text:
        if "o'sish" in text or "oshdi" in text or "oshiril" in text:
            return "percent_growth"
        if "kamay" in text:
            return "percent_decrease"
        if "sonning o'zini top" in text or "foizi" in text and "ga teng" in text:
            return "percent_find_whole"
        return "percent_of"

    if "kasr" in topic_text or re.search(r"\d+\s*/\s*\d+", text):
        if "+" in text:
            return "fraction_sum"
        if "-" in text:
            return "fraction_subtraction"
        if "×" in text or "*" in text:
            return "fraction_multiplication"
        if "÷" in text:
            return "fraction_division"
        if "qisqart" in text:
            return "fraction_reduce"
        if "ga teng" in text:
            return "fraction_equivalent"
        if "katta" in text or "kichik" in text:
            return "fraction_compare"
        return "fraction_generic"

    if "nisbat" in topic_text or "proporsiya" in topic_text:
        if "sodda ko'rinish" in text or "sodda korinish" in text:
            return "ratio_simplify"
        if "daftar narxi" in text or "turadi" in text:
            return "proportion_word_problem"
        return "proportion_missing"

    if "perimetr" in topic_text:
        if "kvadrat" in text:
            return "perimeter_square"
        if "uchburchak" in text:
            return "perimeter_triangle"
        if "perimetri" in text and "ikkinchi tomoni" in text:
            return "perimeter_missing_side"
        return "perimeter_rectangle"
    if "yuza" in topic_text or "maydon" in topic_text:
        if "kvadrat" in text:
            return "area_square"
        if "uchburchak" in text or "balandligi" in text:
            return "area_triangle"
        if "yuzi" in text and "ikkinchi tomoni" in text:
            return "area_missing_side"
        return "area_rectangle"
    if (
        "pifagor" in topic_text
        or "gipotenuza" in text
        or "katet" in text
        or ("diagonal" in text and "to'rt" in text)
    ):
        if "gipotenuzaga qurilgan kvadrat" in text or ("gipotenuza" in text and "kvadrat yuz" in text):
            return "pythagoras_square_area"
        if "ikkinchi katet" in text or ("gipotenuzasi" in text and "bir kateti" in text):
            return "pythagoras_missing_leg"
        if "diagonal" in text and "to'rt" in text:
            return "pythagoras_diagonal"
        if "ko'rsatuvchi tenglik" in text or "ekanini ko'rsatuvchi" in text or "to'g'ri burchakli ekan" in text:
            return "pythagoras_identity"
        return "pythagoras_hypotenuse"
    if "burchak" in topic_text:
        if "qo'shni burchak" in text or "bir chiziq ustida" in text:
            return "angle_linear_pair"
        if "to'g'ri burchak" in text:
            return "angle_right_part"
        return "angle_triangle"
    if "tub" in topic_text:
        if "murakkab son" in text:
            return "composite_select"
        if "tub bo'luvchi" in text or "tub bo'luvchilaridan" in text:
            return "prime_factor"
        return "prime_select"
    if "ekub" in topic_text or "ekuk" in topic_text or "ekub" in text or "ekuk" in text:
        if "qaysi juftlik" in text and "ekub" in text:
            return "gcd_pair_choice"
        if "qaysi juftlik" in text and "ekuk" in text:
            return "lcm_pair_choice"
        if "ekuk" in text:
            return "lcm_value"
        return "gcd_value"
    if "aylana" in topic_text or "doira" in topic_text:
        if "uzunligini" in text:
            return "circle_circumference"
        if "yuzini" in text:
            return "circle_area"
        if "diametri nechaga" in text or "diametrini toping" in text:
            return "circle_diameter"
        if "radiusini" in text:
            return "circle_radius"
        return "circle_measure"
    if "qonuniyat" in text or "qatorni davom" in text or "ketma-ket" in text:
        if "ayirmasini" in text:
            return "sequence_difference"
        if "x ni toping" in text:
            return "sequence_missing_term"
        return "sequence_next_term"
    if "ehtimol" in topic_text or ("tasodifiy" in text and "shar" in text):
        if "bo'lmaslik" in text:
            return "probability_complement"
        if "ko'k bo'lish" in text:
            return "probability_blue"
        return "probability_red"
    if "ildiz" in topic_text or "daraja" in topic_text:
        if "ildiz" in text and "ifoda" in text:
            return "root_expression"
        if "qaysi sonning kvadrati" in text:
            return "root_inverse"
        if "ildiz" in text:
            return "square_root"
        if "kubini" in text or "³" in text:
            return "power_cube"
        if "ifodaning qiymati" in text:
            return "power_expression"
        return "power_value"
    if "tenglama" in topic_text or "ifoda" in topic_text or " x " in f" {text} ":
        if re.search(r"\d+x\s*[+\-]\s*\d+\s*=\s*\d+x\s*[+\-]\s*\d+", text):
            return "equation_balanced"
        if re.search(r"\(\s*x\s*[+\-]\s*\d+\s*\)\s*/\s*\d+", text) or re.search(r"\d+\s*\(\s*x\s*[+\-]\s*\d+\s*\)", text):
            return "equation_grouped"
        if re.search(r"x\s*/\s*\d+\s*=", text) or re.search(r"\d+x\s*/\s*\d+\s*=", text):
            return "equation_division"
        if re.search(r"\d+x\s*[+\-]\s*\d+\s*=", text):
            return "equation_linear"
        if re.search(r"\d+x\s*=", text):
            return "equation_multiplication"
        return "equation_one_step"
    if quiz_type_text in {"iq / tanqidiy fikrlash", "mantiqiy fikrlash", "prezident maktabi"}:
        return "logic_reasoning"
    return "general"


def _is_semantic_duplicate_text(left: str, right: str) -> bool:
    left_clean = re.sub(r"[^a-z0-9%'/+*=()\- ]+", " ", _clean_text(left).lower())
    right_clean = re.sub(r"[^a-z0-9%'/+*=()\- ]+", " ", _clean_text(right).lower())
    left_clean = re.sub(r"\s+", " ", left_clean).strip()
    right_clean = re.sub(r"\s+", " ", right_clean).strip()
    if not left_clean or not right_clean:
        return False
    if left_clean == right_clean:
        return True
    if fuzz is None:
        return False
    return float(fuzz.token_set_ratio(left_clean, right_clean)) >= 97.0


def _sync_find_duplicate_reason(
    question_text: str,
    topic: str | None = None,
    quiz_type: str | None = None,
    options: list[str] | None = None,
) -> str | None:
    if not question_text:
        return None

    from database.models import Quiz, get_session

    candidate_signature = _normalize_quiz_signature(question_text, topic, quiz_type, options)
    session = get_session()
    try:
        query = session.query(Quiz)
        if quiz_type:
            query = query.filter(Quiz.quiz_type == str(quiz_type))
        recent_quizzes = query.order_by(Quiz.id.desc()).limit(400).all()
        for quiz in recent_quizzes:
            existing_options = [quiz.option_a, quiz.option_b, quiz.option_c, quiz.option_d]
            existing_signature = _normalize_quiz_signature(
                quiz.question_text,
                quiz.topic,
                quiz.quiz_type,
                existing_options,
            )
            if candidate_signature == existing_signature:
                return "exact_signature"
            if _is_semantic_duplicate_text(question_text, quiz.question_text):
                same_topic = not topic or _clean_text(topic).lower() == _clean_text(quiz.topic).lower()
                if same_topic:
                    return "semantic_match"
        return None
    finally:
        session.close()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Asosiy generatsiya funksiyasi
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def _enforce_shape(q_data: dict, chosen_shape: str) -> dict:
    """
    3-qatlam: AI qaytargan geometry_hint da noto'g'ri shakl yoki hint yo'q bo'lsa,
    chosen_shape bilan FORCE qiladi.

    Logika:
      - Hint yo'q yoki null â†’ default hint
      - Hint bor lekin boshqa shakl â†’ shakl almashtiriladi, qiymatlar saqlanadi
      - Hint to'g'ri shaklda â†’ o'zgartirmasdan qaytariladi
    """
    hint = q_data.get("geometry_hint", "")
    hint_str = str(hint).strip() if hint else ""
    hint_valid = bool(hint_str) and hint_str.lower() != "null"

    # hf_prompt hint larini o'zgartirmaymiz (ular rasm uchun)
    if hint_valid and hint_str.startswith("hf_prompt|"):
        return q_data

    if not hint_valid:
        # AI hint bermadi â†’ default
        q_data["geometry_hint"] = _get_default_hint(chosen_shape)
        return q_data

    # Hint bor â€” shakl to'g'riligini tekshirish
    ai_shape = hint_str.split("|")[0].strip().lower()

    # Moslashuvchan taqqoslash (masalan "triangle" chosen_shape "right_triangle" ga mos keladi)
    shape_match = (
        chosen_shape in ai_shape or ai_shape in chosen_shape or ai_shape == chosen_shape
    )

    if not shape_match:
        # AI boshqa shakl ishlatdi â†’ shakl almashtiramiz, qiymatlar qoladi
        parts = hint_str.split("|")
        if len(parts) > 1:
            # Eski qiymatlarni saqlaymiz
            new_hint = chosen_shape + "|" + "|".join(parts[1:])
        else:
            new_hint = _get_default_hint(chosen_shape)
        q_data["geometry_hint"] = new_hint

    return q_data


async def trigger_quiz_generation(
    bot,
    chat_id,
    age_group: str,
    quiz_type: str,
    count: int = 30,
    duration_minutes: int = 30,
    custom_topic: str | None = None,
    difficulty: str | None = None,
) -> None:
    """
    AI dan quiz tuzib, to'g'ridan-to'g'ri Telegramga Inline klaviatura bilan yuboradi.
    """
    import aiogram.types as aiotypes
    from aiogram.enums import ParseMode
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    from database.models import Quiz, get_session
    from services.book_question_bank import book_question_bank
    from services.settings_store import get_setting_value
    from services.self_improvement.engine import self_improvement_engine

    channel_id = chat_id or get_setting_value("channel_id")
    teacher_targets = _split_teacher_targets(get_setting_value("teacher_username"))
    if not channel_id:
        logger.error("Quiz yuborilmadi: Kanal ID (channel_id) sozlanmagan!")
        return

    effective_quiz_type = _canonical_quiz_type(quiz_type)
    requested_quiz_type = effective_quiz_type
    difficulty_key = _normalize_difficulty_level(difficulty or age_group)
    normalized_age = _normalize_age_group(age_group or difficulty_key)
    display_level = _get_level_display(age_group, difficulty_key)
    sent_count = 0
    attempt_idx = 0
    used_book_questions = set()
    used_signatures = set()
    pattern_usage: dict[tuple[str, str], int] = {}
    last_pattern_by_topic: dict[str, str] = {}
    last_sent_topic_name: str | None = None

    while sent_count < count:
        shape_pool = _get_shape_pool(effective_quiz_type, sent_count, count)
        needs_image = _needs_visual(effective_quiz_type, sent_count)
        shape_seed = f"{effective_quiz_type}_{sent_count}_{normalized_age}_{custom_topic or 'any'}"
        chosen_shape = _infer_shape_from_topic(custom_topic, effective_quiz_type)
        if not chosen_shape and shape_pool and not custom_topic:
            chosen_shape = _pick_random_shape(shape_pool, shape_seed)

        slot_attempts = 0
        duplicate_streak = 0
        while True:
            slot_attempts += 1
            attempt_idx += 1
            rnd_seed = f"{random.randint(1000, 99999)}_{attempt_idx}"
            allow_duplicates = _should_allow_duplicate(slot_attempts)
            force_local_retry = _should_force_local_retry(slot_attempts, duplicate_streak)
            planned_topic = custom_topic or _pick_planned_topic(
                effective_quiz_type,
                difficulty_key,
                sent_count,
                slot_attempts=slot_attempts,
                last_topic=last_sent_topic_name,
            )
            fallback_topic = planned_topic or custom_topic
            prefer_local_generation = _should_prefer_local_channel_generation(effective_quiz_type, custom_topic)
            q_data = None
            error_msg = None

            if prefer_local_generation:
                q_data = _build_local_fallback_quiz(
                    normalized_age,
                    effective_quiz_type,
                    chosen_shape,
                    fallback_topic,
                    sent_count + slot_attempts,
                    needs_image,
                    difficulty_key,
                )
            elif not force_local_retry:
                if effective_quiz_type in _CRITICAL_QUIZ_TYPES:
                    q_data = critical_thinking_bank.get_quiz_payload(
                        quiz_type=requested_quiz_type,
                        custom_topic=planned_topic,
                        exclude_questions=used_book_questions,
                        age_group=display_level,
                        difficulty=difficulty_key,
                    )
                if not q_data and _should_use_book_payload(effective_quiz_type, custom_topic, difficulty_key):
                    q_data = book_question_bank.get_quiz_payload(
                        quiz_type=effective_quiz_type,
                        custom_topic=planned_topic if custom_topic else None,
                        exclude_questions=used_book_questions,
                        strict_topic=bool(custom_topic),
                    )
                if not q_data:
                    result, error_msg = await asyncio.to_thread(
                        execute_with_rotation,
                        run_ai_generation,
                        normalized_age,
                        effective_quiz_type,
                        rnd_seed,
                        attempt_idx,
                        count,
                        chosen_shape,
                        planned_topic,
                        difficulty_key,
                        ai_role="quiz_gen",
                    )
                    q_data = result or {}
            else:
                q_data = _build_local_fallback_quiz(
                    normalized_age,
                    effective_quiz_type,
                    chosen_shape,
                    fallback_topic,
                    sent_count + slot_attempts,
                    needs_image,
                    difficulty_key,
                )

            if error_msg:
                logger.warning(
                    "Quiz generatsiyasi o'tkazildi: age=%s type=%s topic=%s attempt=%s reason=%s",
                    display_level,
                    requested_quiz_type,
                    custom_topic or "-",
                    attempt_idx,
                    error_msg,
                )
                q_data = _build_local_fallback_quiz(
                    normalized_age,
                    effective_quiz_type,
                    chosen_shape,
                    fallback_topic,
                    sent_count + slot_attempts,
                    needs_image,
                    difficulty_key,
                )

            question_text = q_data.get("question", "").strip()
            question_options = [str(option) for option in q_data.get("options", [])]
            if question_text:
                topic_name = _clean_text(q_data.get("topic", planned_topic or requested_quiz_type)) or requested_quiz_type
                local_signature = _normalize_quiz_signature(
                    question_text,
                    topic_name,
                    requested_quiz_type,
                    question_options,
                )
                duplicate_reason = None
                if local_signature in used_signatures:
                    duplicate_reason = "current_batch"
                else:
                    duplicate_reason = await asyncio.to_thread(
                        _sync_find_duplicate_reason,
                        question_text,
                        topic_name,
                        requested_quiz_type,
                        question_options,
                    )
                if duplicate_reason and not allow_duplicates:
                    duplicate_streak += 1
                    inferred_topic = _clean_text(q_data.get("topic"))
                    if not custom_topic and inferred_topic:
                        fallback_topic = inferred_topic
                    logger.info(
                        "Dublikat o'tkazildi (%s), shu slot uchun qayta uriniladi: %s...",
                        duplicate_reason,
                        question_text[:60],
                    )
                    self_improvement_engine.record_generation_outcome(
                        request_payload={
                            "subject": requested_quiz_type,
                            "grade": _resolve_grade_for_level(display_level, difficulty_key),
                            "difficulty": difficulty_key,
                            "topic": fallback_topic or custom_topic,
                        },
                        response_payload={
                            "success": False,
                            "questions": [],
                            "generator_used": "channel_quiz_generation",
                            "error_message": f"duplicate_blocked:{duplicate_reason}:{question_text[:120]}",
                        },
                        trace_metrics={"duplicate_streak": float(duplicate_streak), "slot_attempts": float(slot_attempts)},
                    )
                    if duplicate_streak >= _FORCE_LOCAL_AFTER_DUPLICATES:
                        logger.info(
                            "Bir xil dublikat ko'p takrorlandi, local fallbackga o'tiladi: type=%s topic=%s slot=%s",
                            requested_quiz_type,
                            fallback_topic or "-",
                            sent_count + 1,
                        )
                    if slot_attempts >= _MAX_SLOT_ATTEMPTS:
                        logger.warning(
                            "Slot juda ko'p qayta urinildi, unique savol qidirish davom etadi: type=%s topic=%s slot=%s",
                            requested_quiz_type,
                            fallback_topic or custom_topic or "-",
                            sent_count + 1,
                        )
                    await asyncio.sleep(min(2, slot_attempts))
                    continue
                else:
                    duplicate_streak = 0

                pattern_family = _infer_pattern_family(question_text, topic_name, requested_quiz_type)
                previous_family = last_pattern_by_topic.get(topic_name)
                family_count = pattern_usage.get((topic_name, pattern_family), 0)
                max_family_repeats = 1 if custom_topic else 2
                allow_pattern_repeat = slot_attempts >= _MAX_SLOT_ATTEMPTS
                if (
                    pattern_family
                    and not allow_pattern_repeat
                    and (previous_family == pattern_family or family_count >= max_family_repeats)
                ):
                    logger.info(
                        "Qolip takrori bloklandi: topic=%s family=%s slot=%s question=%s",
                        topic_name,
                        pattern_family,
                        sent_count + 1,
                        question_text[:80],
                    )
                    self_improvement_engine.record_generation_outcome(
                        request_payload={
                            "subject": requested_quiz_type,
                            "grade": _resolve_grade_for_level(display_level, difficulty_key),
                            "difficulty": difficulty_key,
                            "topic": topic_name,
                        },
                        response_payload={
                            "success": False,
                            "questions": [],
                            "generator_used": "channel_quiz_generation",
                            "error_message": f"pattern_repeat_blocked:{pattern_family}:{question_text[:120]}",
                        },
                        trace_metrics={"slot_attempts": float(slot_attempts), "pattern_family_repeat": float(family_count + 1)},
                    )
                    await asyncio.sleep(min(2, slot_attempts))
                    continue

            question_needs_image = needs_image and q_data.get("source_type") not in {"pdf_book", "critical_thinking_bank"}

            if chosen_shape and question_needs_image and not custom_topic:
                q_data = _enforce_shape(q_data, chosen_shape)

            ok, reason, q_data = _validate_quiz_payload(
                q_data,
                display_level,
                effective_quiz_type,
                question_needs_image,
                required_topic=planned_topic,
                difficulty=difficulty_key,
            )
            if not ok:
                logger.warning(
                    "Quiz validatsiyadan o'tmadi: age=%s type=%s topic=%s slot=%s attempt=%s reason=%s question=%s",
                    display_level,
                    requested_quiz_type,
                    custom_topic or "-",
                    sent_count + 1,
                    slot_attempts,
                    reason,
                    question_text[:160],
                )
                await asyncio.sleep(min(2, slot_attempts))
                continue

            if planned_topic:
                q_data["topic"] = _clean_text(planned_topic)

            media_path = None
            if question_needs_image:
                hint = _clean_text(q_data.get("geometry_hint"))
                local_hint = (
                    hint
                    if hint and hint.lower() != "null" and not hint.startswith("hf_prompt|")
                    else ""
                )

                if local_hint:
                    try:
                        from services.geometry_renderer import create_diagram

                        media_path = await asyncio.to_thread(create_diagram, local_hint)
                        if media_path:
                            logger.info("Lokal rasm muvaffaqiyatli: %s", local_hint[:50])
                    except Exception as image_err:
                        logger.warning(
                            "Lokal rasm render xatosi: age=%s type=%s topic=%s reason=%s hint=%s",
                            display_level,
                            requested_quiz_type,
                            q_data.get("topic", custom_topic or "-"),
                            str(image_err),
                            local_hint[:200],
                        )
                        media_path = None

                if not media_path:
                    image_prompt = (
                        hint.split("|", 1)[1]
                        if hint.startswith("hf_prompt|") and "|" in hint
                        else _build_visual_prompt(
                            q_data,
                            effective_quiz_type,
                            required_topic=custom_topic,
                        )
                    )
                    try:
                        media_path = await asyncio.to_thread(run_ai_image_generation, image_prompt)
                    except Exception as image_err:
                        logger.warning(
                            "Rasm generatsiyasi o'tkazildi (rasmsiz yuboriladi): age=%s type=%s topic=%s reason=%s prompt=%s",
                            display_level,
                            requested_quiz_type,
                            q_data.get("topic", custom_topic or "-"),
                            str(image_err),
                            image_prompt[:200],
                        )
                        media_path = None

            opts = q_data.get("options", [])
            letters = ["A", "B", "C", "D"]
            session = get_session()
            try:
                new_quiz = Quiz(
                    topic=q_data.get("topic", "Boshqa"),
                    quiz_type=requested_quiz_type,
                    age_group=display_level,
                    difficulty=_get_difficulty_display(difficulty_key),
                    question_text=q_data.get("question", "Savol"),
                    option_a=str(opts[0])[:100] if len(opts) > 0 else "A",
                    option_b=str(opts[1])[:100] if len(opts) > 1 else "B",
                    option_c=str(opts[2])[:100] if len(opts) > 2 else "C",
                    option_d=str(opts[3])[:100] if len(opts) > 3 else "D",
                    correct_option_index=int(q_data.get("correct_index", 0)),
                    explanation=q_data.get("explanation", ""),
                    image_path=media_path,
                    message_id=0,
                    chat_id=str(channel_id),
                    is_active=True,
                    poll_id="inline_tizimi",
                    duration_minutes=duration_minutes,
                )
                session.add(new_quiz)
                session.flush()

                msg_caption = (
                    f"<b>Yangi Quiz ({requested_quiz_type}) - {sent_count + 1}/{count}</b>\n\n"
                    f"<b>Quiz ID:</b> <code>{new_quiz.id}</code>\n"
                    f"<b>Mavzu:</b> {q_data.get('topic', 'Aralash')}\n"
                    f"<b>Daraja:</b> {_get_difficulty_display(difficulty_key)}\n"
                    f"<b>Profil:</b> {display_level}\n\n"
                    f"<b>Savol:</b> {q_data.get('question', '')}"
                )

                builder = InlineKeyboardBuilder()
                for idx, opt_text in enumerate(opts):
                    btn_text = f"{letters[idx]}) {str(opt_text)[:40]}"
                    builder.button(text=btn_text, callback_data=f"ans_{new_quiz.id}_{idx}")
                builder.button(
                    text="O'qituvchiga apelatsiya🧑‍🏫",
                    callback_data=f"appeal_{new_quiz.id}",
                )
                builder.adjust(1)
                markup = builder.as_markup()

                msg_id = 0
                send_ok = False
                try:
                    if media_path and os.path.exists(media_path):
                        try:
                            if media_path.endswith(".mp4"):
                                media_file = aiotypes.FSInputFile(media_path)
                                msg_obj = await bot.send_video(
                                    chat_id=channel_id,
                                    video=media_file,
                                    caption=msg_caption[:1000],
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=markup,
                                )
                            else:
                                photo_file = aiotypes.FSInputFile(media_path)
                                msg_obj = await bot.send_photo(
                                    chat_id=channel_id,
                                    photo=photo_file,
                                    caption=msg_caption[:1000],
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=markup,
                                )
                            msg_id = msg_obj.message_id
                            send_ok = True
                        except Exception as media_send_err:
                            logger.warning(
                                "Media yuborishda xato, rasmsiz qayta yuboriladi: slot=%s attempt=%s reason=%s",
                                sent_count + 1,
                                slot_attempts,
                                media_send_err,
                            )
                    if not send_ok:
                        msg_obj = await bot.send_message(
                            channel_id,
                            msg_caption[:4096],
                            parse_mode=ParseMode.HTML,
                            reply_markup=markup,
                        )
                        msg_id = msg_obj.message_id
                        send_ok = True
                except Exception as send_err:
                    logger.warning(
                        "Telegram yuborish xatosi, shu slot qayta uriniladi: slot=%s attempt=%s reason=%s",
                        sent_count + 1,
                        slot_attempts,
                        send_err,
                    )

                if send_ok:
                    new_quiz.message_id = msg_id
                    session.commit()
                    if question_text:
                        topic_name = _clean_text(q_data.get("topic", planned_topic or requested_quiz_type)) or requested_quiz_type
                        pattern_family = _infer_pattern_family(question_text, topic_name, requested_quiz_type)
                        used_signatures.add(
                            _normalize_quiz_signature(
                                question_text,
                                topic_name,
                                requested_quiz_type,
                                question_options,
                            )
                        )
                        pattern_usage[(topic_name, pattern_family)] = pattern_usage.get((topic_name, pattern_family), 0) + 1
                        last_pattern_by_topic[topic_name] = pattern_family
                        last_sent_topic_name = topic_name
                    self_improvement_engine.record_generation_outcome(
                        request_payload={
                            "subject": requested_quiz_type,
                            "grade": _resolve_grade_for_level(display_level, difficulty_key),
                            "difficulty": difficulty_key,
                            "topic": q_data.get("topic", custom_topic),
                        },
                        response_payload={
                            "success": True,
                            "questions": [
                                {
                                    "question": question_text,
                                    "topic": q_data.get("topic", custom_topic),
                                    "type": q_data.get("source_type", "channel_quiz"),
                                    "template_id": q_data.get("source_type", "channel_quiz"),
                                    "metadata": {"pattern_family": pattern_family},
                                }
                            ],
                            "generator_used": q_data.get("source_type", "channel_quiz_generation"),
                        },
                        trace_metrics={
                            "slot_attempts": float(slot_attempts),
                            "duplicate_streak": float(duplicate_streak),
                            "sent_count": float(sent_count + 1),
                        },
                    )
                    teacher_link = _build_telegram_message_link(channel_id, msg_id)
                    if teacher_targets and teacher_link:
                        for teacher_target in teacher_targets:
                            teacher_chat_id = _normalize_teacher_chat_id(teacher_target)
                            if teacher_chat_id is None:
                                continue
                            try:
                                teacher_builder = InlineKeyboardBuilder()
                                teacher_builder.button(
                                    text="🔗 Postni ochish",
                                    url=teacher_link,
                                )
                                teacher_builder.adjust(1)
                                teacher_markup = teacher_builder.as_markup()
                                await bot.send_message(
                                    chat_id=teacher_chat_id,
                                    text=(
                                        f"👨‍🏫 <b>Yangi quiz posti yuborildi</b>\n\n"
                                        f"🆔 <b>Quiz ID:</b> <code>{new_quiz.id}</code>\n"
                                        f"📘 <b>Mavzu:</b> {html.escape(str(q_data.get('topic', 'Aralash')))}\n"
                                        f"🎯 <b>Tur:</b> {html.escape(str(requested_quiz_type))}\n"
                                        f"📈 <b>Daraja:</b> {html.escape(_get_difficulty_display(difficulty_key))}\n"
                                        f"👥 <b>Profil:</b> {html.escape(str(display_level))}\n"
                                        f"📍 <b>Kanal posti:</b> tugmani bosing."
                                    ),
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=teacher_markup,
                                    disable_web_page_preview=True,
                                )
                            except Exception as teacher_err:
                                logger.warning(
                                    "Ustozga post link yuborilmadi: teacher=%s quiz_id=%s reason=%s",
                                    teacher_target,
                                    new_quiz.id,
                                    teacher_err,
                                )
                    sent_count += 1
                    if q_data.get("source_type") in {"pdf_book", "critical_thinking_bank"} and question_text:
                        used_book_questions.add(question_text)
                    break

                session.rollback()
            except Exception as db_err:
                logger.exception(
                    "Quiz DB xatosi, shu slot qayta uriniladi: slot=%s attempt=%s reason=%s",
                    sent_count + 1,
                    slot_attempts,
                    db_err,
                )
                session.rollback()
            finally:
                session.close()
                if media_path and os.path.exists(media_path):
                    try:
                        os.remove(media_path)
                    except Exception:
                        pass

            await asyncio.sleep(min(3, slot_attempts))

        await asyncio.sleep(5)

    if sent_count == count:
        logger.info("%s/%s ta quiz muvaffaqiyatli yuborildi.", sent_count, count)
    summary = self_improvement_engine.refresh_runtime_report(limit=120)
    if summary.get("top_proposal"):
        logger.info(
            "Self-improvement summary: weakest=%s proposal=%s confidence=%.2f",
            summary.get("weakest_target", "-"),
            summary["top_proposal"].get("target", "-"),
            float(summary["top_proposal"].get("confidence", 0.0)),
        )
