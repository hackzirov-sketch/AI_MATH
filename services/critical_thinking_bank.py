import random
import re
from typing import Callable, Dict, List, Optional


def _normalize_text(value: str | None) -> str:
    text = str(value or "").lower()
    text = (
        text.replace("’", "'")
        .replace("ʻ", "'")
        .replace("ʼ", "'")
        .replace("`", "'")
    )
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class CriticalThinkingBank:
    def __init__(self):
        self._logic_types = {
            "mantiqiy fikrlash",
            "tanqidiy fikrlash",
            "iq / tanqidiy fikrlash",
            "iq",
            "kritik fikrlash",
            "prezident maktabi",
        }
        self._iq_types = {"iq", "iq / tanqidiy fikrlash", "tanqidiy fikrlash", "kritik fikrlash"}
        self._president_types = {"prezident maktabi", "prezident maktabi iq", "president school"}
        self._support_keywords = (
            "iq",
            "prezident",
            "prizident",
            "president",
            "tanqid",
            "critical",
            "kritik",
            "mantiqiy fikr",
            "analitik",
            "xulosa",
        )
        self._topic_suggestions_by_profile = {
            "general": [
                "Analogiya",
                "Ketma-ketlik",
                "Kodlash",
                "Mantiqiy xulosa",
                "Tanqidiy tahlil",
                "Matn tahlili",
                "Yo'nalish va fazoviy fikrlash",
                "Qarindoshlik mantiqi",
                "Jadval va ma'lumot tahlili",
                "Tartib va joylashuv",
            ],
            "iq": [
                "Analogiya",
                "Ketma-ketlik",
                "Kodlash",
                "Mantiqiy xulosa",
                "Tanqidiy tahlil",
                "Jadval va ma'lumot tahlili",
                "Tartib va joylashuv",
                "Yo'nalish va fazoviy fikrlash",
            ],
            "president": [
                "Analogiya",
                "Mantiqiy xulosa",
                "Tanqidiy tahlil",
                "Matn tahlili",
                "Jadval va ma'lumot tahlili",
                "Tartib va joylashuv",
                "Shartli fikrlash",
                "Dalil va xulosa",
            ],
        }
        self._source_names = {
            "general": "IQ / Tanqidiy fikrlash banki",
            "iq": "IQ / Tanqidiy fikrlash banki",
            "president": "Prezident maktabi mantiq banki",
        }
        self._profile_signals = {
            "general": ("analogiya", "xulosa", "shart", "tartib", "tahlil", "dalil"),
            "iq": ("analogiya", "kod", "xulosa", "tartib", "tahlil"),
            "president": ("xulosa", "dalil", "tahlil", "albatta", "qo'llab-quvvatlaydi", "shart"),
        }
        self._generator_map = {
            "analogiya": self._generate_analogy,
            "ketma": self._generate_sequence,
            "kod": self._generate_code_sum,
            "xulosa": self._generate_syllogism,
            "tanqid": self._generate_evidence_reasoning,
            "tahlil": self._generate_data_reasoning,
            "matn": self._generate_reading_inference,
            "dalil": self._generate_evidence_reasoning,
            "shart": self._generate_condition_reasoning,
            "yonalish": self._generate_direction_reasoning,
            "yo'nalish": self._generate_direction_reasoning,
            "qarindosh": self._generate_family_reasoning,
            "jadval": self._generate_matrix_reasoning,
            "tartib": self._generate_order_reasoning,
            "joylash": self._generate_order_reasoning,
            "rost": self._generate_statement_truth,
            "stul": self._generate_seating_reasoning,
            "o'rindiq": self._generate_seating_reasoning,
        }

    def supports(
        self,
        subject: str | None = None,
        topic: str | None = None,
        quiz_type: str | None = None,
    ) -> bool:
        normalized_quiz_type = _normalize_text(quiz_type)
        if normalized_quiz_type in self._logic_types:
            return True

        normalized_subject = _normalize_text(subject)
        if normalized_subject in {"iq", "tanqidiy fikrlash", "mantiqiy fikrlash", "prezident maktabi"}:
            return True

        combined = " ".join(
            value for value in (_normalize_text(subject), _normalize_text(topic), normalized_quiz_type) if value
        )
        return any(keyword in combined for keyword in self._support_keywords)

    def get_available_topics(
        self,
        subject: str | None = None,
        topic: str | None = None,
        quiz_type: str | None = None,
        limit: int = 8,
    ) -> List[str]:
        if not self.supports(subject=subject, topic=topic, quiz_type=quiz_type):
            return []

        profile = self._profile_from_request(subject=subject, topic=topic, quiz_type=quiz_type)
        suggestions = self._topic_suggestions_by_profile.get(profile, self._topic_suggestions_by_profile["general"])
        normalized = _normalize_text(topic)
        if not normalized:
            return suggestions[:limit]

        matched = []
        for label in suggestions:
            if any(token in _normalize_text(label) for token in normalized.split()):
                matched.append(label)

        if not matched:
            matched = suggestions
        return matched[:limit]

    def get_test_questions(
        self,
        subject: str,
        topic: str | None,
        count: int,
        grade: int,
        difficulty: str,
    ) -> List[Dict]:
        if not self.supports(subject=subject, topic=topic):
            return []

        profile = self._profile_from_request(subject=subject, topic=topic, quiz_type=subject)
        generated = self._generate_batch(
            count=count,
            grade=grade,
            difficulty=difficulty,
            topic=topic,
            exclude_questions=None,
            subject=subject,
            quiz_type=subject,
        )
        result = []
        for index, item in enumerate(generated, start=1):
            options = {chr(65 + pos): option for pos, option in enumerate(item["options"])}
            correct_label = chr(65 + item["correct_index"])
            result.append(
                {
                    "number": index,
                    "type": "critical_thinking",
                    "question": item["question"],
                    "question_text": item["question"],
                    "options": options,
                    "correct": correct_label,
                    "correct_label": correct_label,
                    "correct_value": item["options"][item["correct_index"]],
                    "answer": item["options"][item["correct_index"]],
                    "topic": item["topic"],
                    "grade": grade,
                    "difficulty": difficulty,
                    "source": self._source_names.get(profile, self._source_names["general"]),
                    "source_type": "critical_thinking_bank",
                    "question_style": "president_school" if profile == "president" else "critical_thinking",
                }
            )
        return result

    def get_quiz_payload(
        self,
        quiz_type: str,
        custom_topic: str | None = None,
        exclude_questions: Optional[set[str]] = None,
        age_group: str | None = None,
        difficulty: str | None = None,
    ) -> Optional[Dict]:
        if not self.supports(topic=custom_topic, quiz_type=quiz_type):
            return None

        profile = self._profile_from_request(topic=custom_topic, quiz_type=quiz_type)
        grade = self._grade_from_age(age_group, profile=profile)
        difficulty_value = _normalize_text(difficulty)
        if difficulty_value not in {"oson", "o'rta", "qiyin"}:
            difficulty_value = self._difficulty_from_age(age_group, profile=profile)
        generated = self._generate_batch(
            count=1,
            grade=grade,
            difficulty=difficulty_value,
            topic=custom_topic,
            exclude_questions=exclude_questions,
            subject=quiz_type,
            quiz_type=quiz_type,
        )
        if not generated:
            return None

        item = generated[0]
        return {
            "question": item["question"],
            "topic": item["topic"],
            "options": item["options"],
            "correct_index": item["correct_index"],
            "explanation": item["explanation"],
            "geometry_hint": "null",
            "source_type": "critical_thinking_bank",
            "source": self._source_names.get(profile, self._source_names["general"]),
            "question_style": "president_school" if profile == "president" else "critical_thinking",
        }

    def _generate_batch(
        self,
        count: int,
        grade: int,
        difficulty: str,
        topic: str | None,
        exclude_questions: Optional[set[str]],
        subject: str | None,
        quiz_type: str | None,
    ) -> List[Dict]:
        profile = self._profile_from_request(subject=subject, topic=topic, quiz_type=quiz_type)
        used = {_normalize_text(question) for question in exclude_questions or set()}
        questions = []
        specific_pool = self._resolve_generators(topic=topic, difficulty=difficulty, grade=grade, profile=profile)
        full_pool = self._resolve_generators(topic=None, difficulty=difficulty, grade=grade, profile=profile)

        for pool in (specific_pool, full_pool):
            attempts = 0
            max_attempts = max(40, count * 20)
            while len(questions) < count and attempts < max_attempts:
                attempts += 1
                generator = random.choice(pool)
                item = self._finalize_generated_item(
                    generator(grade=grade, difficulty=difficulty),
                    profile=profile,
                )
                if not self._is_valid_item(item, profile=profile):
                    continue
                signature = _normalize_text(item["question"])
                if not signature or signature in used:
                    continue
                used.add(signature)
                questions.append(item)
            if len(questions) >= count:
                break

        return questions[:count]

    def _resolve_generators(
        self,
        topic: str | None,
        difficulty: str,
        grade: int,
        profile: str,
    ) -> List[Callable[..., Dict]]:
        difficulty_key = _normalize_text(difficulty)
        easy_pool = [
            self._generate_sequence,
            self._generate_analogy,
            self._generate_odd_one_out,
            self._generate_code_sum,
            self._generate_direction_reasoning,
            self._generate_matrix_reasoning,
        ]
        medium_pool = easy_pool + [
            self._generate_family_reasoning,
            self._generate_order_reasoning,
            self._generate_condition_reasoning,
            self._generate_data_reasoning,
            self._generate_reading_inference,
            self._generate_statement_truth,
        ]
        hard_pool = medium_pool + [
            self._generate_syllogism,
            self._generate_evidence_reasoning,
            self._generate_alternating_sequence,
            self._generate_seating_reasoning,
        ]

        if profile == "president":
            default_pool = [
                self._generate_analogy,
                self._generate_syllogism,
                self._generate_evidence_reasoning,
                self._generate_data_reasoning,
                self._generate_reading_inference,
                self._generate_order_reasoning,
                self._generate_condition_reasoning,
                self._generate_statement_truth,
                self._generate_seating_reasoning,
                self._generate_matrix_reasoning,
                self._generate_alternating_sequence,
            ]
        elif grade <= 4:
            default_pool = easy_pool
        elif difficulty_key == "qiyin":
            default_pool = hard_pool
        elif difficulty_key == "oson":
            default_pool = easy_pool
        elif profile == "iq":
            default_pool = medium_pool + [self._generate_alternating_sequence]
        else:
            default_pool = medium_pool

        normalized_topic = _normalize_text(topic)
        if not normalized_topic:
            return default_pool

        selected = []
        for keyword, generator in self._generator_map.items():
            if keyword in normalized_topic and generator not in selected:
                selected.append(generator)

        if not selected:
            return default_pool

        return selected

    def _profile_from_request(
        self,
        subject: str | None = None,
        topic: str | None = None,
        quiz_type: str | None = None,
    ) -> str:
        combined = " ".join(
            value for value in (_normalize_text(subject), _normalize_text(topic), _normalize_text(quiz_type)) if value
        )
        if any(label in combined for label in self._president_types) or "prezident" in combined or "president" in combined:
            return "president"
        if any(label in combined for label in self._iq_types) or "iq" in combined:
            return "iq"
        return "general"

    def _grade_from_age(self, age_group: str | None, profile: str = "general") -> int:
        normalized = _normalize_text(age_group)
        if any(token in normalized for token in ("6-9", "boshlang", "oson")):
            return 5 if profile == "president" else 4
        if any(token in normalized for token in ("akademik", "olimpiada", "14", "18+")):
            return 9 if profile == "president" else 8
        if any(token in normalized for token in ("qiyin", "murakkab")):
            return 8 if profile == "president" else 7
        return 7 if profile == "president" else 6

    def _difficulty_from_age(self, age_group: str | None, profile: str = "general") -> str:
        normalized = _normalize_text(age_group)
        if any(token in normalized for token in ("6-9", "boshlang", "oson")):
            return "oson"
        if any(token in normalized for token in ("akademik", "olimpiada", "14", "18+", "qiyin", "murakkab")):
            return "qiyin"
        if profile == "president":
            return "qiyin"
        return "o'rta"

    def _finalize_generated_item(self, item: Dict, profile: str) -> Dict:
        question = str(item.get("question", "")).strip()
        topic = str(item.get("topic", "")).strip() or "Mantiqiy xulosa"
        options = [str(option).strip() for option in item.get("options", []) if str(option).strip()]
        if len(options) < 4:
            for fallback in ("A", "B", "C", "D"):
                if len(options) >= 4:
                    break
                if fallback not in options:
                    options.append(fallback)
        options = options[:4]

        try:
            correct_index = int(item.get("correct_index", 0))
        except Exception:
            correct_index = 0
        if correct_index not in range(len(options)):
            correct_index = 0

        explanation = str(item.get("explanation", "")).strip()
        if len(explanation) < 18:
            explanation = f"Mantiqiy tahlil orqali to'g'ri javob topiladi. Javob: {options[correct_index]}"
        elif "Javob:" not in explanation:
            explanation = f"{explanation} Javob: {options[correct_index]}"

        if profile == "president" and len(question) < 25:
            question = f"Diqqat bilan o'qing va to'g'ri xulosani tanlang: {question}"

        return {
            "topic": topic,
            "question": question,
            "options": options,
            "correct_index": correct_index,
            "explanation": explanation,
        }

    def _is_valid_item(self, item: Dict, profile: str) -> bool:
        question = str(item.get("question", "")).strip()
        topic = str(item.get("topic", "")).strip()
        options = [str(option).strip() for option in item.get("options", []) if str(option).strip()]

        if len(question) < (24 if profile == "president" else 14):
            return False
        if len(options) != 4:
            return False
        if len({option.lower() for option in options}) != 4:
            return False

        try:
            correct_index = int(item.get("correct_index", 0))
        except Exception:
            return False
        if correct_index not in range(4):
            return False

        full_text = _normalize_text(" ".join([question, topic, *options, str(item.get("explanation", ""))]))
        signals = self._profile_signals.get(profile, self._profile_signals["general"])
        if profile in {"iq", "president"} and not any(signal in full_text for signal in signals):
            return False
        if profile == "president":
            textual_options = sum(1 for option in options if re.search(r"[a-z]", option.lower()))
            if textual_options < 3:
                return False
        return True

    def _pack_question(
        self,
        topic: str,
        question: str,
        correct: str | int,
        distractors: List[str | int],
        explanation: str,
    ) -> Dict:
        correct_text = str(correct)
        unique = []
        seen = set()
        for value in [correct_text, *[str(item) for item in distractors]]:
            key = value.lower()
            if value and key not in seen:
                seen.add(key)
                unique.append(value)
        while len(unique) < 4:
            filler = str(len(unique) + 2)
            if filler.lower() not in seen:
                seen.add(filler.lower())
                unique.append(filler)
        options = unique[:4]
        random.shuffle(options)
        return {
            "topic": topic,
            "question": question,
            "options": options,
            "correct_index": options.index(correct_text),
            "explanation": explanation,
        }

    def _numeric_distractors(self, correct: int, spread: int = 4) -> List[int]:
        candidates = [
            correct - spread,
            correct - max(1, spread // 2),
            correct + max(1, spread // 2),
            correct + spread,
            correct + spread + 2,
        ]
        result = []
        for value in candidates:
            if value > 0 and value != correct and value not in result:
                result.append(value)
        return result[:3]

    def _generate_sequence(self, grade: int, difficulty: str) -> Dict:
        start = random.randint(2, 10 + max(0, grade - 3))
        step = random.randint(2, 4 if _normalize_text(difficulty) == "oson" else 7)
        seq = [start + step * index for index in range(5)]
        question = f"Ketma-ketlikni davom ettiring: {seq[0]}, {seq[1]}, {seq[2]}, {seq[3]}, ?"
        explanation = f"Har safar {step} qo'shilmoqda. Shuning uchun keyingi son {seq[4]}."
        return self._pack_question(
            topic="Ketma-ketlik",
            question=question,
            correct=seq[4],
            distractors=self._numeric_distractors(seq[4], spread=step + 1),
            explanation=explanation,
        )

    def _generate_alternating_sequence(self, grade: int, difficulty: str) -> Dict:
        odd_start = random.randint(2, 8)
        even_start = odd_start + random.randint(3, 7)
        odd_step = random.randint(2, 4)
        even_step = random.randint(2, 4)
        seq = [
            odd_start,
            even_start,
            odd_start + odd_step,
            even_start + even_step,
            odd_start + 2 * odd_step,
            even_start + 2 * even_step,
        ]
        correct = odd_start + 3 * odd_step
        question = f"Qonuniyatni toping: {seq[0]}, {seq[1]}, {seq[2]}, {seq[3]}, {seq[4]}, {seq[5]}, ?"
        explanation = (
            f"Toq o'rinlardagi sonlar {odd_step} tadan ortmoqda, juft o'rinlardagi sonlar esa {even_step} tadan. "
            f"Shuning uchun keyingi son {correct}."
        )
        return self._pack_question(
            topic="Ketma-ketlik",
            question=question,
            correct=correct,
            distractors=self._numeric_distractors(correct, spread=odd_step + even_step),
            explanation=explanation,
        )

    def _generate_analogy(self, grade: int, difficulty: str) -> Dict:
        pairs = [
            ("Ko'z", "ko'rish", "quloq", "eshitish", ["hid bilish", "tatib ko'rish", "yurish"]),
            ("Termometr", "harorat", "tarozi", "og'irlik", ["balandlik", "tezlik", "uzunlik"]),
            ("Kompas", "yo'nalish", "soat", "vaqt", ["masofa", "rang", "harorat"]),
            ("Qalam", "yozish", "cho'tka", "bo'yash", ["o'qish", "o'lchash", "kesish"]),
            ("Kalit", "qulf", "parol", "tizim", ["monitor", "stol", "telefon"]),
            ("Shifokor", "davolash", "o'qituvchi", "o'rgatish", ["kutish", "yugurish", "tinglash"]),
        ]
        first, second, third, correct, distractors = random.choice(pairs)
        question = f"Analogiyani toping: {first} : {second} = {third} : ?"
        explanation = f"{first} {second} bilan bog'liq bo'lsa, xuddi shunday {third} {correct} bilan bog'liq."
        return self._pack_question(
            topic="Analogiya",
            question=question,
            correct=correct,
            distractors=distractors,
            explanation=explanation,
        )

    def _generate_odd_one_out(self, grade: int, difficulty: str) -> Dict:
        sets = [
            (["Kvadrat", "Uchburchak", "Doira", "Olma"], "Olma", "Birinchi uchta geometrik shakl, olma esa meva."),
            (["Metall", "Yog'och", "Shisha", "Seshanba"], "Seshanba", "Birinchi uchta material, seshanba esa hafta kuni."),
            (["Qalam", "Daftar", "Kitob", "Bulut"], "Bulut", "Birinchi uchta o'quv quroli, bulut esa tabiat hodisasi."),
            (["Tulki", "Bo'ri", "Arslon", "Sabzi"], "Sabzi", "Birinchi uchta hayvon, sabzi esa sabzavot."),
            (["Dushanba", "Payshanba", "Shanba", "Qovun"], "Qovun", "Birinchi uchta hafta kuni, qovun esa meva."),
        ]
        options, correct, explanation = random.choice(sets)
        options = options[:]
        random.shuffle(options)
        return {
            "topic": "Klassifikatsiya",
            "question": "Qaysi variant boshqalari bilan bir guruhga kirmaydi?",
            "options": options,
            "correct_index": options.index(correct),
            "explanation": explanation,
        }

    def _generate_code_sum(self, grade: int, difficulty: str) -> Dict:
        words = ["BOLA", "KITOB", "QALAM", "DARA", "OLMA", "STOL", "RASM", "LOYIHA"]
        word = random.choice(words)
        correct = sum(ord(char) - 64 for char in word)
        question = f"A=1, B=2, C=3 ... Z=26 bo'lsa, {word} so'zining kodi nechaga teng?"
        explanation = f"Har bir harfning tartib raqami olinadi va yig'iladi. {word} uchun natija {correct}."
        return self._pack_question(
            topic="Kodlash",
            question=question,
            correct=correct,
            distractors=self._numeric_distractors(correct, spread=5),
            explanation=explanation,
        )

    def _generate_condition_reasoning(self, grade: int, difficulty: str) -> Dict:
        scenarios = [
            (
                "Agar yomg'ir yog'sa, maydon yopiladi. Maydon yopilmadi. Qaysi xulosa to'g'ri?",
                "Yomg'ir yog'magan bo'lishi kerak",
                ["Yomg'ir albatta yog'di", "Maydon keyin yopiladi", "Hech narsa bilib bo'lmaydi"],
                "Shartga ko'ra yomg'ir bo'lsa maydon yopiladi. Maydon yopilmagan ekan, yomg'ir yog'magan.",
            ),
            (
                "Agar chiroq yonsa, elektr bor. Elektr yo'q. Qaysi xulosa to'g'ri?",
                "Chiroq yonmaydi",
                ["Chiroq albatta yonadi", "Elektr keyin keladi", "Xulosa qilib bo'lmaydi"],
                "Elektr yo'q bo'lsa, chiroqning yonishi mumkin emas.",
            ),
            (
                "Agar Aziz darsga kelsa, guruh to'liq bo'ladi. Guruh to'liq emas. Demak:",
                "Aziz kelmagan",
                ["Aziz kelgan", "Dars bo'lmagan", "Hech narsa ma'lum emas"],
                "Aziz kelganda guruh to'liq bo'lishi kerak edi. Guruh to'liq emas, demak Aziz kelmagan.",
            ),
        ]
        question, correct, distractors, explanation = random.choice(scenarios)
        return self._pack_question(
            topic="Mantiqiy xulosa",
            question=question,
            correct=correct,
            distractors=distractors,
            explanation=explanation,
        )

    def _generate_family_reasoning(self, grade: int, difficulty: str) -> Dict:
        templates = [
            (
                "Nodira Kamolning qizi. Kamol esa Alisherning o'g'li. Nodira Alisherga kim bo'ladi?",
                "Nabirasi",
                ["Qizi", "Singlisi", "Xolasi"],
                "Kamol Alisherning o'g'li bo'lsa, Nodira Alisherning nabirasi bo'ladi.",
            ),
            (
                "Bekzod Madinaning akasi. Madina esa Ozodaning qizi. Bekzod Ozodaga kim bo'ladi?",
                "O'g'li",
                ["Jiyani", "Akasi", "Otasi"],
                "Madina Ozodaning qizi bo'lsa, uning akasi Bekzod ham Ozodaning farzandi bo'ladi.",
            ),
            (
                "Malika Dilshodning onasi. Dilshod esa Azizning otasi. Malika Azizga kim bo'ladi?",
                "Buvisi",
                ["Xolasi", "Onasi", "Singlisi"],
                "Dilshod Azizning otasi bo'lsa, Dilshodning onasi Malika Azizning buvisi bo'ladi.",
            ),
            (
                "Sardor Zuhra ning ukasi. Zuhra esa Komilning qizi. Sardor Komilga kim bo'ladi?",
                "O'g'li",
                ["Jiyani", "Nabirasi", "Akasi"],
                "Zuhra Komilning qizi bo'lsa, uning ukasi Sardor ham Komilning farzandi bo'ladi.",
            ),
        ]
        question, correct, distractors, explanation = random.choice(templates)
        return self._pack_question(
            topic="Qarindoshlik mantiqi",
            question=question,
            correct=correct,
            distractors=distractors,
            explanation=explanation,
        )

    def _generate_direction_reasoning(self, grade: int, difficulty: str) -> Dict:
        scenarios = [
            ("shimolga", "sharqqa", "janubga", "Sharqda"),
            ("sharqqa", "shimolga", "g'arbga", "Shimolda"),
            ("janubga", "g'arbga", "shimolga", "G'arbda"),
            ("g'arbga", "janubga", "sharqqa", "Janubda"),
        ]
        first_dir, second_dir, third_dir, correct_dir = random.choice(scenarios)
        first = random.randint(3, 7)
        second = random.randint(2, 6)
        question = (
            f"Jasur {first_dir} {first} qadam, {second_dir} {second} qadam, {third_dir} {first} qadam yurdi. "
            "U boshlang'ich nuqtaga nisbatan qayerda turibdi?"
        )
        explanation = f"Birinchi va uchinchi yo'nalishlar bir-birini bekor qiladi, natijada {correct_dir.lower()} {second} qadam qoladi."
        opposite_horizontal = "G'arbda" if correct_dir == "Sharqda" else "Sharqda"
        opposite_vertical = "Shimolda" if correct_dir != "Shimolda" else "Janubda"
        return self._pack_question(
            topic="Yo'nalish va fazoviy fikrlash",
            question=question,
            correct=f"{correct_dir} {second} qadam",
            distractors=[
                f"{opposite_horizontal} {second} qadam",
                f"{opposite_vertical} {second} qadam",
                "Boshlang'ich nuqtada",
            ],
            explanation=explanation,
        )

    def _generate_order_reasoning(self, grade: int, difficulty: str) -> Dict:
        templates = [
            (
                "Nodira Malika dan oldin turibdi. Malika Sevinchdan oldin. Kim oxirida turadi?",
                "Sevinch",
                ["Nodira", "Malika", "Ularning barchasi bir xil o'rinda"],
                "Nodira -> Malika -> Sevinch tartibi kelib chiqadi, demak oxirida Sevinch turadi.",
            ),
            (
                "Ali Bekzoddan keyin. Bekzod Dildoradan keyin. Kim birinchi turadi?",
                "Dildora",
                ["Ali", "Bekzod", "Hech biri"],
                "Tartib Dildora -> Bekzod -> Ali bo'ladi. Birinchi Dildora turadi.",
            ),
            (
                "Kamola Shahnozadan oldin, Shahnoza Diyoraning oldida. Kim o'rtada turadi?",
                "Shahnoza",
                ["Kamola", "Diyora", "Aniq emas"],
                "Kamola -> Shahnoza -> Diyora tartibida o'rtadagi ism Shahnoza.",
            ),
        ]
        question, correct, distractors, explanation = random.choice(templates)
        return self._pack_question(
            topic="Tartib va joylashuv",
            question=question,
            correct=correct,
            distractors=distractors,
            explanation=explanation,
        )

    def _generate_statement_truth(self, grade: int, difficulty: str) -> Dict:
        templates = [
            (
                "1) Barcha A lar B. 2) Ba'zi B lar C. Quyidagilardan qaysi biri albatta to'g'ri?",
                "Hech biri albatta C emas",
                [
                    "Barcha A lar C",
                    "Ba'zi A lar C",
                    "Barcha C lar A",
                ],
                "Ikkinchi gap faqat ba'zi B lar C ekanini aytadi, A lar haqida majburiy bog'lanish bermaydi.",
            ),
            (
                "1) Hamma stipendiya oluvchilar testdan o'tgan. 2) Dilnoza testdan o'tgan. Qaysi xulosa to'g'ri?",
                "Dilnoza stipendiya olganini aniq bilib bo'lmaydi",
                [
                    "Dilnoza albatta stipendiya olgan",
                    "Dilnoza testdan o'tmagan",
                    "Testdan o'tganlarning hech biri stipendiya olmaydi",
                ],
                "Testdan o'tish stipendiya uchun yetarli emas. Shuning uchun Dilnoza stipendiya olganini aniq ayta olmaymiz.",
            ),
            (
                "1) Barcha qizil qutilar yopiq. 2) Hech bir yopiq quti stol ustida emas. Qaysi xulosa albatta to'g'ri?",
                "Hech bir qizil quti stol ustida emas",
                [
                    "Stol ustidagi hamma qutilar qizil",
                    "Yopiq bo'lmagan qutilar qizil",
                    "Qizil qutilarning hammasi stol ustida",
                ],
                "Qizil quti bo'lsa yopiq, yopiq quti stol ustida bo'lmaydi. Demak qizil quti ham stol ustida bo'lmaydi.",
            ),
        ]
        question, correct, distractors, explanation = random.choice(templates)
        return self._pack_question(
            topic="Shartli fikrlash",
            question=question,
            correct=correct,
            distractors=distractors,
            explanation=explanation,
        )

    def _generate_matrix_reasoning(self, grade: int, difficulty: str) -> Dict:
        rules = [
            (lambda a, b: a + b),
            (lambda a, b: a * b),
            (lambda a, b: 2 * a + b),
        ]
        rule = random.choice(rules)
        a1, b1 = random.randint(2, 6), random.randint(2, 6)
        a2, b2 = random.randint(2, 6), random.randint(2, 6)
        a3, b3 = random.randint(2, 6), random.randint(2, 6)
        c1 = rule(a1, b1)
        c2 = rule(a2, b2)
        correct = rule(a3, b3)
        question = f"Qoidani toping: {a1}, {b1} -> {c1}; {a2}, {b2} -> {c2}; {a3}, {b3} -> ?"
        explanation = f"Birinchi ikkita misolda bir xil qoida ishlatilgan. Shu qoida bilan javob {correct}."
        return self._pack_question(
            topic="Jadval va ma'lumot tahlili",
            question=question,
            correct=correct,
            distractors=self._numeric_distractors(correct, spread=max(3, grade // 2)),
            explanation=explanation,
        )

    def _generate_data_reasoning(self, grade: int, difficulty: str) -> Dict:
        templates = [
            (
                "28 o'quvchining 18 tasi shaxmatga, 12 tasi robototexnikaga qatnaydi. 7 tasi ikkala to'garakka ham qatnaydi. Faqat shaxmatga qatnaydiganlar nechta?",
                11,
                "18 dan 7 ni ayiramiz, chunki 7 o'quvchi ikkala to'garakka ham qatnaydi.",
            ),
            (
                "40 kitobning 26 tasi badiiy, 18 tasi ilmiy. 9 tasi ikkala ro'yxatda ham qayd etilgan. Faqat badiiy ro'yxatdagi kitoblar nechta?",
                17,
                "Faqat badiiy ro'yxatdagilar soni 26 - 9 = 17.",
            ),
            (
                "35 o'quvchining 20 tasi ingliz tiliga, 15 tasi rus tiliga qatnaydi. 6 tasi ikkala guruhga ham qatnaydi. Ingliz tiliga faqat o'zi qatnaydiganlar nechta?",
                14,
                "Faqat ingliz tili guruhi uchun 20 - 6 = 14 bo'ladi.",
            ),
        ]
        question, correct, explanation = random.choice(templates)
        return self._pack_question(
            topic="Matn tahlili",
            question=question,
            correct=correct,
            distractors=self._numeric_distractors(correct, spread=4),
            explanation=explanation,
        )

    def _generate_reading_inference(self, grade: int, difficulty: str) -> Dict:
        templates = [
            (
                "Matn: Maktabda ertalab 15 daqiqalik o'qish vaqti joriy qilindi. Bir oy ichida kutubxonadan olingan kitoblar soni ham, o'quvchilarning qisqa savollarga javob berish tezligi ham oshdi. Qaysi xulosa eng asosli?",
                "Qisqa o'qish vaqti o'quvchilarning matn bilan ishlash odatini kuchaytirgan bo'lishi mumkin",
                [
                    "Kutubxonadagi barcha kitoblar bir xil qiziqarli bo'lgan",
                    "Har bir o'quvchi endi albatta eng yuqori baho oladi",
                    "O'qish vaqti sport natijalarini ham oshirgan",
                ],
                "Matndagi ikki ko'rsatkich bir yo'nalishda o'zgargani o'qish odati kuchaygan bo'lishi mumkinligini bildiradi.",
            ),
            (
                "Matn: Sinfga savol-javobdan oldin 3 daqiqalik reja tuzish odati kiritildi. Shundan keyin o'quvchilarning og'zaki chiqishlari tartibliroq bo'ldi, lekin vaqt sarfi deyarli o'zgarmadi. Qaysi xulosa eng mantiqiy?",
                "Qisqa reja tuzish javob sifatini yaxshilab, vaqtni keskin oshirmagan",
                [
                    "Reja tuzish faqat kuchsiz o'quvchilarga yordam beradi",
                    "Vaqt o'zgarmagan bo'lsa, sifat ham o'zgarmagan",
                    "Endi reja tuzishning o'zi dars o'rniga o'tadi",
                ],
                "Matnda javoblar tartibliroq bo'lgani aytilgan va vaqt sarfi deyarli o'zgarmagani bu xulosani qo'llab-quvvatlaydi.",
            ),
            (
                "Matn: Ikki guruhga bir xil masala berildi. Birinchi guruh avval misollarni tahlil qildi, ikkinchi guruh darhol yechishga o'tdi. Birinchi guruh kamroq xato qildi. Qaysi xulosa eng asosli?",
                "Boshlang'ich tahlil xatolar sonini kamaytirishga yordam bergan bo'lishi mumkin",
                [
                    "Ikkinchi guruhdagi barcha o'quvchilar tayyorsiz bo'lgan",
                    "Darhol yechish usuli har doim noto'g'ri bo'ladi",
                    "Masala faqat birinchi guruh uchun oson bo'lgan",
                ],
                "Ikki guruh farqi aynan yondashuvda bo'lgani uchun eng ehtiyotkor xulosa tahlilning foydasiga boradi.",
            ),
        ]
        question, correct, distractors, explanation = random.choice(templates)
        return self._pack_question(
            topic="Matn tahlili",
            question=question,
            correct=correct,
            distractors=distractors,
            explanation=explanation,
        )

    def _generate_seating_reasoning(self, grade: int, difficulty: str) -> Dict:
        templates = [
            (
                "To'rtta o'quvchi bir qatorda o'tiribdi: Ali, Bek, Diyor, Lola. Ali chap chetda emas. Lola o'ng chetda. Bek Ali ning chapida. Kim chap chetda o'tirgan?",
                "Bek",
                ["Ali", "Diyor", "Lola"],
                "Lola o'ng chetda. Bek Ali ning chapida bo'lishi kerak va Ali chap chetda emas. Eng mos joy Bek uchun chap chet bo'ladi.",
            ),
            (
                "Besh o'quvchi ketma-ket turibdi. Madina Saidaning o'ngida, Said esa Kamolning o'ngida. Eng chapda kim turishi mumkin?",
                "Kamol",
                ["Madina", "Said", "Aniq emas"],
                "Tartib Kamol -> Said -> Madina ko'rinishida keladi. Shuning uchun chap tomonda Kamol turadi.",
            ),
            (
                "Uch stulda Nodira, Ozod va Vali o'tirgan. Nodira chapda. Vali o'ngda o'tirmaydi. O'rtadagi kim?",
                "Vali",
                ["Ozod", "Nodira", "Aniq emas"],
                "Nodira chapda. Vali o'ngda bo'la olmasa, u o'rtada o'tiradi va Ozod o'ngda qoladi.",
            ),
        ]
        question, correct, distractors, explanation = random.choice(templates)
        return self._pack_question(
            topic="Tartib va joylashuv",
            question=question,
            correct=correct,
            distractors=distractors,
            explanation=explanation,
        )

    def _generate_syllogism(self, grade: int, difficulty: str) -> Dict:
        templates = [
            (
                "Barcha olimpiada ishtirokchilari saralashdan o'tgan. Saralashdan o'tgan barcha o'quvchilar ro'yxatga olingan. Demak:",
                "Barcha olimpiada ishtirokchilari ro'yxatga olingan",
                [
                    "Ro'yxatga olinganlarning hammasi olimpiada ishtirokchisi",
                    "Saralashdan o'tmaganlar ro'yxatga olinadi",
                    "Hech bir olimpiada ishtirokchisi ro'yxatga olinmagan",
                ],
                "A -> B va B -> C bo'lsa, A -> C kelib chiqadi.",
            ),
            (
                "Barcha ko'k papkalar yopiq. Yopiq papkalarning hech biri stol ustida emas. Demak:",
                "Hech bir ko'k papka stol ustida emas",
                [
                    "Stol ustidagi hamma papkalar ko'k",
                    "Yopiq bo'lmagan barcha papkalar ko'k",
                    "Ko'k papkalarning hammasi stol ustida",
                ],
                "Ko'k papka bo'lsa yopiq, yopiq papka stol ustida bo'lmaydi. Shuning uchun ko'k papka ham stol ustida bo'lmaydi.",
            ),
            (
                "Barcha robotlar zaryadlanadi. Zaryadlangan barcha qurilmalarda chiroq yonadi. Demak:",
                "Barcha robotlarda chiroq yonadi",
                [
                    "Chirog'i yongan hamma narsa robot",
                    "Hech bir robot zaryadlanmaydi",
                    "Faqat ba'zi robotlarda chiroq yonadi",
                ],
                "Robot -> zaryadlangan, zaryadlangan -> chiroq yonadi. Demak robot -> chiroq yonadi.",
            ),
        ]
        question, correct, distractors, explanation = random.choice(templates)
        return self._pack_question(
            topic="Mantiqiy xulosa",
            question=question,
            correct=correct,
            distractors=distractors,
            explanation=explanation,
        )

    def _generate_evidence_reasoning(self, grade: int, difficulty: str) -> Dict:
        templates = [
            (
                "Maktab bog'ida daraxtlar ko'paygani uchun hovli salqinroq bo'ldi. Qaysi dalil bu fikrni eng yaxshi qo'llab-quvvatlaydi?",
                "Daraxt ekilgan joylarda tush payti harorat 3 daraja pastroq o'lchandi",
                [
                    "O'quvchilar yozda ko'proq suv ichdi",
                    "Maktab devorlari qayta bo'yaldi",
                    "Sport musobaqalari soni oshdi",
                ],
                "Haroratning pasaygani haqidagi o'lchov asosiy fikrni bevosita qo'llab-quvvatlaydi.",
            ),
            (
                "Kutubxonada jim o'qish soati joriy etilgach, o'quvchilar ko'proq kitob tugata boshladi. Qaysi ma'lumot bu fikrni kuchaytiradi?",
                "Jim o'qish soati boshlanganidan keyin bir haftada tugatilgan kitoblar soni ancha oshgan",
                [
                    "Kutubxonaga yangi stullar olib kelindi",
                    "Ba'zi o'quvchilar uyga ertaroq qaytdi",
                    "Kutubxonachi yangi jurnal obuna qildi",
                ],
                "Asosiy da'voni kuchaytiradigan narsa aynan kitob tugatish sonining oshganini ko'rsatadigan ma'lumot.",
            ),
            (
                "Sinfda ertalabki qisqa takrorlash mashqlari natijani yaxshiladi. Qaysi fakt bu xulosani eng ko'p qo'llab-quvvatlaydi?",
                "Mashqlar joriy etilganidan keyin nazorat ishidagi o'rtacha ball oshdi",
                [
                    "O'quvchilar yangi daftar sotib oldi",
                    "Sinfxona devoriga plakatlar ilindi",
                    "Darsdan keyin sport to'garagi ochildi",
                ],
                "Natijaning oshgani haqida to'g'ridan-to'g'ri ko'rsatkich berilgan variant eng kuchli dalildir.",
            ),
        ]
        question, correct, distractors, explanation = random.choice(templates)
        return self._pack_question(
            topic="Tanqidiy tahlil",
            question=question,
            correct=correct,
            distractors=distractors,
            explanation=explanation,
        )


critical_thinking_bank = CriticalThinkingBank()
