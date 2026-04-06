import random
import math
from typing import List, Dict, Tuple, Optional

class TopicGenerator:
    GRADES = list(range(1, 12))
    
    DIFFICULTIES = {
        1: "oson",
        2: "oson",
        3: "oson",
        4: "oson",
        5: "oson",
        6: "oson",
        7: "o'rta",
        8: "o'rta",
        9: "o'rta",
        10: "qiyin",
        11: "qiyin"
    }
    
    TOPICS_BY_GRADE = {
        1: [
            "sonlar_0_10", "sonlar_0_20", "sonlar_0_100",
            "qoshni_sonlar", "son_tarkibi", "juft_toq",
            "taqqoslash", "tartiblash", "qoshish", "ayirish",
            "amallar_boglanishi", "nol_bilan_amallar",
            "arifmetik_ifodalar", "qavs_tanish", "uzunlik_sm",
            "massa_tushuncha", "hajm_tushuncha", "pul_birliklari",
            "vaqt_yaxlit", "vaqt_yarim", "matnli_masalalar",
            "amal_tanlash", "geometriya_nuqta", "togri_egri_chiziq",
            "kesma", "shakllar", "shakllarni_solishtirish"
        ],
        2: [
            "sonlar_1000", "razryadlar", "sonni_yozish",
            "sonni_yigindiga_ajratish", "taqqoslash_3xonali",
            "sonlar_ketma_ketligi", "qoshish_ayirish_ustun",
            "otish_bilan_amallar", "kopaytirish_jadval",
            "kopaytirish_jadvali_2_5", "kopaytirish_jadvali_6_9",
            "bolish_tushuncha", "qavsli_ifodalar_2",
            "noma_lum_x_topish", "uzunlik_sm_dm_m",
            "massa_kg", "hajm_litr", "pul_birliklari_2",
            "birlik_almashtirish", "soat_minut", "kun_hafta_oy",
            "masalalar_1_2amalli", "jadval_masalalar",
            "burchak", "togri_burchak", "shakllarni_chizish",
            "kesma_uzunligi"
        ],
        3: [
            "sonlar_10000", "razryadlar_sinf_bosh", "kengaytirilgan_shakl",
            "qoshish_ayirish_katta", "kopaytirish_jadvali_toliq",
            "kopaytirish_2xonali_1xonali", "bolish_qoldiq",
            "amallar_tartibi", "qavsli_ifodalar_3",
            "noma_lum_tenglamalar", "kasr_tushuncha",
            "surat_maxraj", "kasrlarni_solishtirish",
            "uzunlik_mm_sm_dm_m_km", "massa_g_kg",
            "hajm_l", "vaqt_sekund_minut_soat",
            "birliklar_otish", "masalalar_2_3amalli",
            "mantiqiy_masalalar", "perimetr", "togri_tortburchak_kvadrat",
            "shakllarni_qismlarga_bolish", "simmetriya_bosh"
        ],
        4: [
            "sonlar_million", "sinflar_birlik_minglar",
            "rim_raqamlari_bosh", "qoshish_ayirish_kopxonali",
            "kopaytirish_2_3xonali", "bolish_ustun",
            "qoldiqli_bolish", "amallar_tartibi_murakkab",
            "murakkab_ifodalar", "bir_nechta_qavs",
            "tenglamalar_yechish", "oddiy_kasrlar",
            "kasrlarni_qisqartirish", "kasrlarni_taqqoslash",
            "kasr_qoshish_ayirish", "aralash_son",
            "onli_kasrlar", "onli_kasrlarni_oxish",
            "onli_kasrlar_amallar", "tezlik_masofa_vaqt",
            "narx_miqdor_qiymat", "massa_hajm_uzunlik",
            "barcha_birliklar", "murakkab_birlik_masalalari",
            "masalalar_3_4amalli", "real_hayat_masalalari",
            "jadval_diagramma_masalalar", "perimetr_4",
            "yuzani_hisoblash", "kvadrat_yuza", "togri_tortburchak_yuza",
            "burchak_turlari", "parallel_kesishuvchi",
            "fazoviy_shakllar", "kub", "togri_tortburchak_prizma",
            "shar", "simmetriya"
        ],
        5: [
            "kop_xonali_sonlar", "sonlarni_taqqoslash_5",
            "tub_murakkab_sonlar", "boluvchilar_karralilar",
            "tub_sonlarga_ajratish", "EKUB_EKUK",
            "qoshish_ayirish_5", "kopaytirish_ustun_5",
            "bolish_ustun_5", "amallar_tartibi_5",
            "oddiy_kasrlar_5", "kasrlarni_qisqartirish_5",
            "kasrlarni_taqqoslash_5", "kasr_qoshish_ayirish_5",
            "kasr_kopaytirish_bolish_5", "onli_kasrlar_5",
            "onli_kasrlar_amallar_5", "uzunlik_5", "massa_5",
            "vaqt_5", "birliklarni_almashtirish_5",
            "harfli_ifodalar", "formulalar",
            "nuqta_chiziq_kesma", "burchaklar_5",
            "uchburchak_turlari_5", "togri_tortburchak_kvadrat_5",
            "perimetr_yuza_5"
        ],
        6: [
            "manfiy_musbat_sonlar", "koordinata_togri_chiziq",
            "manfiy_sonlar_bilan_amallar", "modul_tushuncha",
            "oddiy_kasrlar_6", "onli_kasrlar_6",
            "barcha_amallar_6", "nisbat",
            "proporsiya", "masshtab",
            "foiz_topish", "foizga_doir_masalalar",
            "sonning_foizi", "foizdan_son_topish",
            "algebraik_ifodalar_6", "qavslarni_ochish",
            "burchaklar_yigindisi", "uchburchak_xossalari_6",
            "aylana_va_doira", "yuzalar_6",
            "sonlar_kvadrati", "darajalar_6"
        ],
        7: [
            "algebraik_ifodalar_7", "kophadlar_7",
            "qisqartirilgan_kopaytirish", "a_plus_b_kvadrat",
            "a_minus_b_kvadrat", "a_kvadrat_minus_b_kvadrat",
            "bir_noma_lumli_tenglamalar_7", "tengsizliklar_7",
            "funksiya_tushuncha", "funksiya_grafik",
            "chiziqli_funksiya_7", "togri_chiziqlar_7",
            "parallel_chiziqlar_7", "uchburchak_7",
            "uchburchak_turlari_7", "burchaklar_yigindisi_7",
            "median_7", "balandlik_7", "bissektrisa_7",
            "perimetr_7", "yuza_7", "tenglamalar_sistemasi_7"
        ],
        8: [
            "kophadlar_8", "kopaytirish_bolish_8",
            "kasrli_ifodalar_8", "algebraik_kasrlar",
            "soddalashtirish_8", "kvadrat_tenglama",
            "to_liq_va_to_liqmas_kvadrat", "diskriminant",
            "ildizlar_8", "tengsizliklar_8",
            "chiziqli_tengsizliklar_8", "togri_tortburchaklar_8",
            "parallelogramm_8", "trapetsiya_8",
            "aylana_8", "markaziy_burchak",
            "yoy_8", "pifagor_teoremasi",
            "togri_burchakli_uchburchak_8", "sinus_kosinus_8"
        ],
        9: [
            "kvadrat_tenglamalar_9", "to_liq_kvadrat_tenglama",
            "to_liqmas_kvadrat_tenglama", "vieta_formulasi",
            "kvadrat_funksiya", "kvadrat_funksiya_grafik",
            "kvadrat_tengsizliklar_9", "arifmetik_progressiya",
            "arifmetik_progressiya_n_had", "geometrik_progressiya",
            "geometrik_progressiya_n_had", "uchburchaklar_o_xshashligi",
            "o_xshashlik_koeffitsienti", "sinus_teoremasi_bosh",
            "kosinus_teoremasi_bosh", "aylana_uzunligi",
            "doira_yuzi", "trigonometriya_9",
            "sin_30_45_60", "pifagor_9"
        ],
        10: [
            "korsatkichli_funksiya", "korsatkichli_tenglamalar",
            "logarifmik_funksiya", "logarifmlar",
            "logarifm_asosiy_formulalar", "logarifmik_tenglamalar",
            "trigonometriya_10", "trigonometrik_formulalar",
            "trigonometrik_tenglamalar_10", "trigonometrik_ifodalar",
            "ketma_ketliklar_10", "limit_tushuncha",
            "hosila_chegaralari", "togri_chiziq_va_tekislik",
            "parallel_perpendikulyar", "prizma",
            "piramida", "silindr", "konus", "shar_10",
            "fazoviy_shakllar_yuzalari", "fazoviy_shakllar_hajmlari"
        ],
        11: [
            "hosila_tarifi", "hosila_qoidalari",
            "hosila_jadvali", "murakkab_funksiya_hosila",
            "ekstremum", "eng_katta_eng_kichik",
            "hosila_amaliyot", "boshlangich_tushuncha",
            "integral", "aniq_integral",
            "murakkab_funksiyalar_11", "grafiklar_11",
            "logarifmik_tenglamalar_11", "trigonometrik_tenglamalar_11",
            "permutatsiya", "kombinatsiya",
            "variantlar_soni", "ehtimollik",
            "takroriy_almashtirishlar", "sinuslar_teoremasi_11",
            "kosinuslar_teoremasi_11", "uchburchak_yuzi_formulalar",
            "fazoviy_geometriya_11", "kesimlar"
        ]
    }

    def __init__(self):
        self.grade = None
        self.difficulty = None
        self.question_count = None
        self.subject = None

    def set_params(self, grade: int, difficulty: str, question_count: int, subject: str):
        self.grade = grade
        self.difficulty = difficulty
        self.question_count = question_count
        self.subject = subject

    def get_topics_by_grade(self, grade: int) -> List[str]:
        return self.TOPICS_BY_GRADE.get(grade, [])

    def get_difficulty_for_grade(self, grade: int) -> str:
        return self.DIFFICULTIES.get(grade, "o'rta")

    def get_random_topic(self, grade: int, difficulty: str = None) -> str:
        topics = self.get_topics_by_grade(grade)
        if not topics:
            return "sonlar_asosiy"
        if difficulty:
            return random.choice(topics)
        return random.choice(topics)

    def generate_distractors(self, correct_answer: float, topic: str, count: int = 3) -> List[float]:
        correct = float(correct_answer)
        distractors = []
        
        if correct == 0:
            distractors = [random.choice([1, 2, 3, 4, 5]) for _ in range(count)]
        else:
            for _ in range(count):
                variation = random.choice([
                    correct * random.uniform(0.5, 0.9),
                    correct * random.uniform(1.1, 1.5),
                    correct + random.randint(1, 10) if correct < 100 else correct + random.randint(10, 50),
                    correct - random.randint(1, min(10, int(correct))) if correct > 5 else correct + random.randint(1, 5)
                ])
                if variation != correct and variation > 0:
                    distractors.append(round(variation, 1))
            
            while len(distractors) < count:
                distractors.append(correct + random.randint(1, 20))
        
        while len(distractors) < count:
            distractors.append(correct + random.randint(1, 30))
        
        return distractors[:count]

    def format_distractors(self, correct: float, distractors: List[float]) -> Dict[str, float]:
        options = distractors + [correct]
        random.shuffle(options)
        
        result = {}
        labels = ['A', 'B', 'C', 'D']
        for i, val in enumerate(options):
            result[labels[i]] = val
        
        correct_label = [k for k, v in result.items() if v == correct][0]
        return result, correct_label

    def generate_question(self, grade: int, difficulty: str, topic: str = None) -> Dict:
        if topic is None:
            topic = self.get_random_topic(grade, difficulty)
        
        generator_method = f"generate_{topic}"
        if hasattr(self, generator_method):
            return getattr(self, generator_method)(difficulty)
        else:
            return self._generate_generic_question(grade, topic, difficulty)

    def _generate_generic_question(self, grade: int, topic: str, difficulty: str) -> Dict:
        a = random.randint(1, min(50, grade * 10))
        b = random.randint(1, min(50, grade * 10))
        
        if difficulty == "oson":
            a = random.randint(1, 20)
            b = random.randint(1, 20)
        
        operations = ["+", "-"]
        if grade >= 2:
            operations.append("*")
        if grade >= 3:
            operations.append("//")
        
        op = random.choice(operations)
        
        if op == "+":
            correct = a + b
            question = f"{a} + {b} = ?"
        elif op == "-":
            if a < b:
                a, b = b, a
            correct = a - b
            question = f"{a} - {b} = ?"
        else:
            correct = a * b
            question = f"{a} × {b} = ?"
        
        distractors = self.generate_distractors(correct, topic)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": topic,
            "grade": grade,
            "difficulty": difficulty
        }

    def generate_questions_batch(self, grade: int, difficulty: str, count: int, topic: str = None) -> List[Dict]:
        questions = []
        topics = self.get_topics_by_grade(grade)
        
        if topic:
            topics = [t for t in topics if topic.lower() in t.lower()]
            if not topics:
                topics = self.get_topics_by_grade(grade)
        
        for _ in range(count):
            topic = random.choice(topics)
            q = self.generate_question(grade, difficulty, topic)
            questions.append(q)
        
        return questions

    def generate_sonlar_0_10(self, difficulty: str) -> Dict:
        num = random.randint(0, 10)
        correct = num
        question = f"Quyidagi sonni ayting: {num}"
        
        distractors = self.generate_distractors(correct, "sonlar", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "sonlar_0_10",
            "grade": 1,
            "difficulty": difficulty
        }

    def generate_qoshni_sonlar(self, difficulty: str) -> Dict:
        num = random.randint(2, 9)
        correct = num + 1
        question = f"{num} sonining qo'shnisi qaysi?"
        
        distractors = self.generate_distractors(correct, "qoshni_sonlar", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "qoshni_sonlar",
            "grade": 1,
            "difficulty": difficulty
        }

    def generate_son_tarkibi(self, difficulty: str) -> Dict:
        parts = [(1, 6), (2, 5), (3, 4), (4, 3), (5, 2), (6, 1)]
        a, b = random.choice(parts)
        correct = a + b
        question = f"{a} + {b} = ?"
        
        distractors = self.generate_distractors(correct, "son_tarkibi", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "son_tarkibi",
            "grade": 1,
            "difficulty": difficulty
        }

    def generate_juft_toq(self, difficulty: str) -> Dict:
        num = random.randint(1, 10)
        correct = "juft" if num % 2 == 0 else "toq"
        question = f"{num} soni juftmi yoki toqmi?"
        options = {"A": "juft", "B": "toq", "C": "hech qaysi", "D": "ikkala ham"}
        
        return {
            "question": question,
            "options": options,
            "correct": "A" if correct == "juft" else "B",
            "correct_value": correct,
            "topic": "juft_toq",
            "grade": 1,
            "difficulty": difficulty
        }

    def generate_qoshish(self, difficulty: str) -> Dict:
        if difficulty == "oson":
            a, b = random.randint(0, 5), random.randint(0, 5)
        else:
            a, b = random.randint(0, 9), random.randint(0, 9)
        
        correct = a + b
        question = f"{a} + {b} = ?"
        
        distractors = self.generate_distractors(correct, "qoshish", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "qoshish",
            "grade": 1,
            "difficulty": difficulty
        }

    def generate_ayirish(self, difficulty: str) -> Dict:
        a, b = random.randint(3, 10), random.randint(0, 5)
        if a < b:
            a, b = b, a
        
        correct = a - b
        question = f"{a} - {b} = ?"
        
        distractors = self.generate_distractors(correct, "ayirish", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "ayirish",
            "grade": 1,
            "difficulty": difficulty
        }

    def generate_taqqoslash(self, difficulty: str) -> Dict:
        a, b = random.randint(1, 10), random.randint(1, 10)
        if a == b:
            b = a + 1
        
        correct = ">" if a > b else "<"
        if a > b:
            question = f"{a} ___ {b} (katta belgi qo'ying)"
        else:
            question = f"{a} ___ {b} (katta belgi qo'ying)"
        
        options = {"A": ">", "B": "<", "C": "=", "D": "≥"}
        correct_label = "A" if correct == ">" else "B"
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "taqqoslash",
            "grade": 1,
            "difficulty": difficulty
        }

    def generate_sonlar_0_100(self, difficulty: str) -> Dict:
        tens = random.choice([10, 20, 30, 40, 50, 60, 70, 80, 90])
        ones = random.randint(1, 9)
        correct = tens + ones
        question = f"{tens} + {ones} = ?"
        
        distractors = self.generate_distractors(correct, "sonlar_0_100", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "sonlar_0_100",
            "grade": 1,
            "difficulty": difficulty
        }

    def generate_shakllar(self, difficulty: str) -> Dict:
        shapes = [
            ("kvadrat", "4 ta tomoni teng, 4 ta burchagi bor"),
            ("uchburchak", "3 ta tomoni, 3 ta burchagi bor"),
            ("doira", "Aylana shakli, burchaklari yo'q"),
            ("togri_tortburchak", "4 ta tomoni, qarama-qarshi tomonlari teng")
        ]
        
        shape, desc = random.choice(shapes)
        question = f"Qaysi shakl: {desc}?"
        
        options = {"A": "kvadrat", "B": "uchburchak", "C": "doira", "D": "togri_tortburchak"}
        shape_map = {"kvadrat": "A", "uchburchak": "B", "doira": "C", "togri_tortburchak": "D"}
        
        return {
            "question": question,
            "options": options,
            "correct": shape_map[shape],
            "correct_value": shape,
            "topic": "shakllar",
            "grade": 1,
            "difficulty": difficulty
        }

    def generate_kesma(self, difficulty: str) -> Dict:
        length = random.randint(1, 10)
        question = f"Kesmaning uzunligi {length} sm. Kesma nechta nuqtadan iborat?"
        options = {"A": "2", "B": "3", "C": "4", "D": "cheksiz"}
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "2",
            "topic": "kesma",
            "grade": 1,
            "difficulty": difficulty
        }

    def generate_uzunlik_sm(self, difficulty: str) -> Dict:
        length = random.randint(1, 20)
        question = f"Linealkaning uzunligi {length} sm. Bu necha santimetr?"
        
        distractors = self.generate_distractors(length, "uzunlik_sm", 3)
        options, correct_label = self.format_distractors(length, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": length,
            "topic": "uzunlik_sm",
            "grade": 1,
            "difficulty": difficulty
        }

    def generate_sonlar_1000(self, difficulty: str) -> Dict:
        num = random.randint(100, 999)
        correct = num
        question = f"{num} sonining raqamlari yig'indisi nechiga teng?"
        digit_sum = sum(int(d) for d in str(num))
        
        distractors = self.generate_distractors(digit_sum, "sonlar_1000", 3)
        options, correct_label = self.format_distractors(digit_sum, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": digit_sum,
            "topic": "sonlar_1000",
            "grade": 2,
            "difficulty": difficulty
        }

    def generate_razryadlar(self, difficulty: str) -> Dict:
        num = random.randint(100, 999)
        question = f"{num} sonida nechta yuzlik bor?"
        correct = int(str(num)[0])
        
        distractors = self.generate_distractors(correct, "razryadlar", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "razryadlar",
            "grade": 2,
            "difficulty": difficulty
        }

    def generate_kopaytirish_jadval(self, difficulty: str) -> Dict:
        num = random.randint(2, 9)
        multiplier = random.randint(1, 10)
        correct = num * multiplier
        question = f"{num} × {multiplier} = ?"
        
        distractors = self.generate_distractors(correct, "kopaytirish_jadval", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "kopaytirish_jadval",
            "grade": 2,
            "difficulty": difficulty
        }

    def generate_burchak(self, difficulty: str) -> Dict:
        types = [
            ("To'g'ri burchak", "90° ga teng"),
            ("O'tkir burchak", "90° dan kichik"),
            ("O'tmas burchak", "90° dan katta")
        ]
        
        btype, desc = random.choice(types)
        question = f"Qaysi burchak {desc}?"
        
        options = {"A": "To'g'ri burchak", "B": "O'tkir burchak", "C": "O'tmas burchak", "D": "Teng tomonli burchak"}
        type_map = {"To'g'ri burchak": "A", "O'tkir burchak": "B", "O'tmas burchak": "C"}
        
        return {
            "question": question,
            "options": options,
            "correct": type_map[btype],
            "correct_value": btype,
            "topic": "burchak",
            "grade": 2,
            "difficulty": difficulty
        }

    def generate_sonlar_10000(self, difficulty: str) -> Dict:
        num = random.randint(1000, 9999)
        question = f"{num} sonini yaxlitlangan shaklda yozing:"
        correct = (num // 1000) * 1000
        question += f" (minglikgacha)"
        
        distractors = self.generate_distractors(correct, "sonlar_10000", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "sonlar_10000",
            "grade": 3,
            "difficulty": difficulty
        }

    def generate_kasr_tushuncha(self, difficulty: str) -> Dict:
        numerator = random.randint(1, 9)
        denominator = random.randint(2, 10)
        correct = numerator / denominator
        question = f"{numerator}/{denominator} kasri qanday son?"
        
        distractors = self.generate_distractors(round(correct, 2), "kasr_tushuncha", 3)
        options, correct_label = self.format_distractors(round(correct, 2), distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": round(correct, 2),
            "topic": "kasr_tushuncha",
            "grade": 3,
            "difficulty": difficulty
        }

    def generate_perimetr(self, difficulty: str) -> Dict:
        a = random.randint(2, 10)
        b = random.randint(2, 10)
        correct = 2 * (a + b)
        question = f"To'g'ri to'rtburchakning bo'yi {a} sm, eni {b} sm. Perimetri necha sm?"
        
        distractors = self.generate_distractors(correct, "perimetr", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "perimetr",
            "grade": 3,
            "difficulty": difficulty
        }

    def generate_sonlar_million(self, difficulty: str) -> Dict:
        num = random.randint(100000, 999999)
        question = f"{num} sonida nechta raqam bor?"
        correct = len(str(num))
        
        options = {"A": correct, "B": correct + 1, "C": correct - 1, "D": 7}
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": correct,
            "topic": "sonlar_million",
            "grade": 4,
            "difficulty": difficulty
        }

    def generate_yuzani_hisoblash(self, difficulty: str) -> Dict:
        if difficulty == "oson":
            a = random.randint(2, 6)
            b = random.randint(2, 6)
        else:
            a = random.randint(3, 10)
            b = random.randint(3, 10)
        
        correct = a * b
        question = f"Kvadratning tomoni {a} sm. Yuzasi necha sm²?"
        
        distractors = self.generate_distractors(correct, "yuzani_hisoblash", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "yuzani_hisoblash",
            "grade": 4,
            "difficulty": difficulty
        }

    def generate_tub_murakkab_sonlar(self, difficulty: str) -> Dict:
        numbers = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 4, 6, 8, 9, 10, 12, 15, 21, 25, 27]
        num = random.choice(numbers)
        is_prime = num in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
        correct = "tub" if is_prime else "murakkab"
        
        question = f"{num} soni tubmi yoki murakkabmi?"
        options = {"A": "tub", "B": "murakkab", "C": "baribir", "D": "noma'lum"}
        correct_label = "A" if correct == "tub" else "B"
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "tub_murakkab_sonlar",
            "grade": 5,
            "difficulty": difficulty
        }

    def generate_boluvchilar_karralilar(self, difficulty: str) -> Dict:
        num = random.randint(2, 12)
        divisor = random.randint(2, 5)
        correct = num * divisor
        
        question = f"{num} sonining karralisi bo'ladigan sonni ko'rsating:"
        options = {"A": num * 2, "B": num - 1, "C": num + divisor, "D": num // 2 if num % 2 == 0 else num * 3}
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": num * 2,
            "topic": "boluvchilar_karralilar",
            "grade": 5,
            "difficulty": difficulty
        }

    def generate_burchaklar_5(self, difficulty: str) -> Dict:
        angles = [(30, "30°"), (45, "45°"), (60, "60°"), (90, "90°"), (120, "120°")]
        angle, angle_str = random.choice(angles)
        
        if angle < 90:
            correct = "o'tkir"
            types = ["o'tkir", "o'tmas", "to'g'ri", "teng"]
        elif angle == 90:
            correct = "to'g'ri"
            types = ["o'tkir", "o'tmas", "to'g'ri", "teng"]
        else:
            correct = "o'tmas"
            types = ["o'tkir", "o'tmas", "to'g'ri", "teng"]
        
        question = f"{angle_str} burchak qanday burchak?"
        options = {"A": types[0], "B": types[1], "C": types[2], "D": types[3]}
        correct_label = list(options.keys())[list(options.values()).index(correct)]
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "burchaklar_5",
            "grade": 5,
            "difficulty": difficulty
        }

    def generate_perimetr_yuza_5(self, difficulty: str) -> Dict:
        a = random.randint(3, 8)
        b = random.randint(3, 8)
        correct = a * b
        perimetr = 2 * (a + b)
        
        question = f"To'g'ri to'rtburchakning tomonlari {a} sm va {b} sm. Yuzasi necha sm²?"
        
        distractors = [perimetr, a + b, a + b + perimetr]
        distractors = [d for d in distractors if d != correct][:3]
        while len(distractors) < 3:
            distractors.append(correct + random.randint(1, 10))
        
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "perimetr_yuza_5",
            "grade": 5,
            "difficulty": difficulty
        }

    def generate_manfiy_musbat_sonlar(self, difficulty: str) -> Dict:
        num = random.randint(1, 20)
        correct = -num
        question = f"{num} ning qarama-qarshi soni qaysi?"
        
        distractors = self.generate_distractors(correct, "manfiy_musbat", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "manfiy_musbat_sonlar",
            "grade": 6,
            "difficulty": difficulty
        }

    def generate_modul_tushuncha(self, difficulty: str) -> Dict:
        num = random.randint(1, 20)
        question = f"|-{num}| = ?"
        correct = num
        
        distractors = self.generate_distractors(correct, "modul", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "modul_tushuncha",
            "grade": 6,
            "difficulty": difficulty
        }

    def generate_nisbat(self, difficulty: str) -> Dict:
        a = random.randint(2, 9)
        b = random.randint(2, 9)
        correct = round(a / b, 2)
        question = f"{a}:{b} nisbatning qiymatini toping"
        
        distractors = self.generate_distractors(correct, "nisbat", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "nisbat",
            "grade": 6,
            "difficulty": difficulty
        }

    def generate_proporsiya(self, difficulty: str) -> Dict:
        a = random.randint(2, 9)
        b = random.randint(2, 9)
        c = a * b
        question = f"{a} : {b} = {c} : x. x ni toping"
        correct = c * b / a
        
        distractors = self.generate_distractors(round(correct, 1), "proporsiya", 3)
        options, correct_label = self.format_distractors(round(correct, 1), distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": round(correct, 1),
            "topic": "proporsiya",
            "grade": 6,
            "difficulty": difficulty
        }

    def generate_foiz_topish(self, difficulty: str) -> Dict:
        num = random.randint(10, 100)
        percent = random.choice([10, 20, 25, 50])
        correct = num * percent / 100
        question = f"{num} ning {percent}% ini toping"
        
        distractors = self.generate_distractors(correct, "foiz", 3)
        options, correct_label = self.format_distractors(round(correct, 1), distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": round(correct, 1),
            "topic": "foiz_topish",
            "grade": 6,
            "difficulty": difficulty
        }

    def generate_masshtab(self, difficulty: str) -> Dict:
        real = random.choice([100, 200, 500, 1000])
        map_scale = random.choice([1, 2, 5, 10])
        question = f"Masshtab 1:{map_scale}. Xaritada {real // map_scale} sm. Haqiqiy masofa qancha metr?"
        correct = real
        
        distractors = self.generate_distractors(correct, "masshtab", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "masshtab",
            "grade": 6,
            "difficulty": difficulty
        }

    def generate_burchaklar_yigindisi(self, difficulty: str) -> Dict:
        a = random.randint(20, 80)
        b = random.randint(20, 80 - a)
        correct = 180 - (a + b)
        question = f"Uchburchakning ikki burchagi {a}° va {b}°. Uchinchi burchak necha gradus?"
        
        distractors = self.generate_distractors(correct, "burchaklar_yigindisi", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "burchaklar_yigindisi",
            "grade": 6,
            "difficulty": difficulty
        }

    def generate_aylana_va_doira(self, difficulty: str) -> Dict:
        r = random.randint(2, 10)
        question = f"Aylanarning radiusi {r} sm. Diametri necha sm?"
        correct = 2 * r
        
        distractors = self.generate_distractors(correct, "aylana_va_doira", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "aylana_va_doira",
            "grade": 6,
            "difficulty": difficulty
        }

    def generate_algebraik_ifodalar_7(self, difficulty: str) -> Dict:
        a = random.randint(1, 10)
        x = random.randint(1, 10)
        result = a + x
        question = f"a = {a} bo'lsa, a + {x} ifodaning qiymatini toping"
        
        distractors = self.generate_distractors(result, "algebraik_ifodalar", 3)
        options, correct_label = self.format_distractors(result, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": result,
            "topic": "algebraik_ifodalar_7",
            "grade": 7,
            "difficulty": difficulty
        }

    def generate_qisqartirilgan_kopaytirish(self, difficulty: str) -> Dict:
        a = random.randint(2, 5)
        b = random.randint(2, 5)
        
        formula = random.choice(["a_plus_b_kvadrat", "a_minus_b_kvadrat", "a_kvadrat_minus_b_kvadrat"])
        
        if formula == "a_plus_b_kvadrat":
            correct = (a + b) ** 2
            question = f"({a} + {b})² = ?"
        elif formula == "a_minus_b_kvadrat":
            if a < b:
                a, b = b, a
            correct = (a - b) ** 2
            question = f"({a} - {b})² = ?"
        else:
            correct = a ** 2 - b ** 2
            question = f"{a}² - {b}² = ?"
        
        distractors = self.generate_distractors(correct, formula, 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": formula,
            "grade": 7,
            "difficulty": difficulty
        }

    def generate_tenglamalar_7(self, difficulty: str) -> Dict:
        x = random.randint(1, 10)
        a = random.randint(2, 5)
        b = random.randint(1, 10)
        correct = x
        
        question = f"x + {b} = {a * x + b} tenglamani yeching"
        
        distractors = self.generate_distractors(correct, "tenglamalar", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "bir_noma_lumli_tenglamalar_7",
            "grade": 7,
            "difficulty": difficulty
        }

    def generate_median_7(self, difficulty: str) -> Dict:
        lengths = sorted([random.randint(2, 10) for _ in range(3)])
        question = f"Uchburchakning tomonlari {lengths[0]} sm, {lengths[1]} sm, {lengths[2]} sm. Mediana nima?"
        correct = "Median - bu uchburchak uchidan qarama-qarshi tomonning o'rtasiga tushirilgan segment"
        options = {
            "A": "Uchburchak uchidan qarama-qarshi tomonning o'rtasiga tushirilgan segment",
            "B": "Burchakni teng ikkiga bo'luvchi chiziq",
            "C": "Uchburchak uchidan qarama-qarshi tomonga tushirilgan perpendikulyar",
            "D": "Uchburchakning barcha tomonlari yig'indisi"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": correct,
            "topic": "median_7",
            "grade": 7,
            "difficulty": difficulty
        }

    def generate_kvadrat_tenglama(self, difficulty: str) -> Dict:
        x = random.randint(1, 5)
        a = 1
        b = -(x + x)
        c = x * x
        correct = x
        
        question = f"x² - {abs(b)}x + {c} = 0 tenglamani yeching"
        
        distractors = self.generate_distractors(correct, "kvadrat_tenglama", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "kvadrat_tenglama",
            "grade": 8,
            "difficulty": difficulty
        }

    def generate_diskriminant(self, difficulty: str) -> Dict:
        a = 1
        b = random.randint(3, 9)
        c = random.randint(2, 9)
        correct = b ** 2 - 4 * a * c
        question = f"x² + {b}x + {c} = 0 tenglamaning diskriminantini toping (D = b² - 4ac)"
        
        distractors = self.generate_distractors(correct, "diskriminant", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "diskriminant",
            "grade": 8,
            "difficulty": difficulty
        }

    def generate_pifagor_teoremasi(self, difficulty: str) -> Dict:
        a = random.randint(3, 6)
        b = random.randint(4, 6)
        c = int(math.sqrt(a**2 + b**2))
        
        if a**2 + b**2 == c**2:
            question = f"To'g'ri burchakli uchburchakning katetlari {a} sm va {b} sm. Gipotenuza necha sm?"
            correct = c
            
            distractors = self.generate_distractors(correct, "pifagor", 3)
            options, correct_label = self.format_distractors(correct, distractors)
        else:
            c_sq = a**2 + b**2
            question = f"To'g'ri burchakli uchburchakning katetlari {a} sm va {b} sm. Gipotenuza kvadrati necha sm²?"
            correct = c_sq
            
            distractors = self.generate_distractors(correct, "pifagor", 3)
            options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "pifagor_teoremasi",
            "grade": 8,
            "difficulty": difficulty
        }

    def generate_parallelogramm_8(self, difficulty: str) -> Dict:
        question = "Parallelogrammning qarama-qarshi burchaklari..."
        options = {
            "A": "Teng",
            "B": "Qo'shni",
            "C": "To'ldiruvchi",
            "D": "Bir-biriga bog'liq emas"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "Teng",
            "topic": "parallelogramm_8",
            "grade": 8,
            "difficulty": difficulty
        }

    def generate_trapetsiya_8(self, difficulty: str) -> Dict:
        question = "Trapetsiyaning o'rta chizig'i qanday hisoblanadi?"
        options = {
            "A": "Asoslar yig'indisining yarmi",
            "B": "Asoslar ayirmasi",
            "C": "Balandlikning yarmi",
            "D": "Yon tomonlar yig'indisi"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "Asoslar yig'indisining yarmi",
            "topic": "trapetsiya_8",
            "grade": 8,
            "difficulty": difficulty
        }

    def generate_vieta_formulasi(self, difficulty: str) -> Dict:
        x1 = random.randint(1, 5)
        x2 = random.randint(1, 5)
        b = -(x1 + x2)
        c = x1 * x2
        
        question = f"x² {'+' if b > 0 else ''}{b}x {'+' if c > 0 else ''}{c} = 0 tenglamaning ildizlari yig'indisi qancha?"
        correct = x1 + x2
        
        distractors = self.generate_distractors(correct, "vieta", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "vieta_formulasi",
            "grade": 9,
            "difficulty": difficulty
        }

    def generate_kvadrat_funksiya(self, difficulty: str) -> Dict:
        question = "y = x² funksiyaning grafigi qanday shakl?"
        options = {
            "A": "Parabola",
            "B": "To'g'ri chiziq",
            "C": "Aylana",
            "D": "Uchburchak"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "Parabola",
            "topic": "kvadrat_funksiya",
            "grade": 9,
            "difficulty": difficulty
        }

    def generate_arifmetik_progressiya(self, difficulty: str) -> Dict:
        a1 = random.randint(1, 10)
        d = random.randint(2, 5)
        n = 5
        an = a1 + (n - 1) * d
        question = f"Aritmetik progressiya: a₁ = {a1}, d = {d}. a₅ ni toping"
        correct = an
        
        distractors = self.generate_distractors(correct, "arifmetik_progressiya", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "arifmetik_progressiya",
            "grade": 9,
            "difficulty": difficulty
        }

    def generate_geometrik_progressiya(self, difficulty: str) -> Dict:
        a1 = random.randint(1, 5)
        q = 2
        n = 4
        an = a1 * (q ** (n - 1))
        question = f"Geometrik progressiya: a₁ = {a1}, q = {q}. a₄ ni toping"
        correct = an
        
        distractors = self.generate_distractors(correct, "geometrik_progressiya", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "geometrik_progressiya",
            "grade": 9,
            "difficulty": difficulty
        }

    def generate_uchburchaklar_o_xshashligi(self, difficulty: str) -> Dict:
        question = "Ikki uchburchak o'xshash bo'lishi uchun qanday shart kerak?"
        options = {
            "A": "Burchaklari teng",
            "B": "Tomonlari teng",
            "C": "Perimetrlari teng",
            "D": "Yuzalari teng"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "Burchaklari teng",
            "topic": "uchburchaklar_o_xshashligi",
            "grade": 9,
            "difficulty": difficulty
        }

    def generate_sinus_kosinus_9(self, difficulty: str) -> Dict:
        angles = [(30, 0.5, 0.87), (45, 0.71, 0.71), (60, 0.87, 0.5)]
        angle, sin_val, cos_val = random.choice(angles)
        
        if random.choice([True, False]):
            question = f"sin({angle}°) = ?"
            correct = round(sin_val, 2)
        else:
            question = f"cos({angle}°) = ?"
            correct = round(cos_val, 2)
        
        distractors = self.generate_distractors(correct, "sinus_kosinus", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "sin_30_45_60",
            "grade": 9,
            "difficulty": difficulty
        }

    def generate_aylana_uzunligi(self, difficulty: str) -> Dict:
        r = random.randint(2, 10)
        correct = round(2 * 3.14 * r, 2)
        question = f"Aylananing radiusi {r} sm. Aylana uzunligini toping (π ≈ 3.14)"
        
        distractors = self.generate_distractors(correct, "aylana_uzunligi", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "aylana_uzunligi",
            "grade": 9,
            "difficulty": difficulty
        }

    def generate_doira_yuzi(self, difficulty: str) -> Dict:
        r = random.randint(2, 8)
        correct = round(3.14 * r * r, 2)
        question = f"Aylananing radiusi {r} sm. Doira yuzasini toping (π ≈ 3.14)"
        
        distractors = self.generate_distractors(correct, "doira_yuzi", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "doira_yuzi",
            "grade": 9,
            "difficulty": difficulty
        }

    def generate_korsatkichli_funksiya(self, difficulty: str) -> Dict:
        question = "y = 2ˣ funksiya qanday funksiya?"
        options = {
            "A": "Ko'rsatkichli funksiya",
            "B": "Chiziqli funksiya",
            "C": "Kvadrat funksiya",
            "D": "Logarifmik funksiya"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "Ko'rsatkichli funksiya",
            "topic": "korsatkichli_funksiya",
            "grade": 10,
            "difficulty": difficulty
        }

    def generate_logarifmlar(self, difficulty: str) -> Dict:
        base = random.choice([2, 3, 10])
        power = random.randint(2, 5)
        result = base ** power
        question = f"log_{base}({result}) = ?"
        correct = power
        
        distractors = self.generate_distractors(correct, "logarifmlar", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "logarifmlar",
            "grade": 10,
            "difficulty": difficulty
        }

    def generate_trigonometriya_10(self, difficulty: str) -> Dict:
        question = "cos²α + sin²α = ?"
        options = {"A": "1", "B": "0", "C": "2", "D": "-1"}
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "1",
            "topic": "trigonometriya_10",
            "grade": 10,
            "difficulty": difficulty
        }

    def generate_limit_tushuncha(self, difficulty: str) -> Dict:
        question = "lim(x→0) sin(x)/x = ?"
        options = {"A": "1", "B": "0", "C": "∞", "D": "-1"}
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "1",
            "topic": "limit_tushuncha",
            "grade": 10,
            "difficulty": difficulty
        }

    def generate_prizma(self, difficulty: str) -> Dict:
        question = "To'g'ri burchakli prizmaning hajmi qanday topiladi?"
        options = {
            "A": "Asos yuzasi × balandlik",
            "B": "Tomonlari yig'indisi",
            "C": "Perimetr × balandlik",
            "D": "Barcha qirralar yig'indisi"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "Asos yuzasi × balandlik",
            "topic": "prizma",
            "grade": 10,
            "difficulty": difficulty
        }

    def generate_piramida(self, difficulty: str) -> Dict:
        question = "Piramidaning hajmi qanday topiladi?"
        options = {
            "A": "(1/3) × Asos yuzasi × balandlik",
            "B": "Asos yuzasi × balandlik",
            "C": "(1/2) × Asos yuzasi × balandlik",
            "D": "Barcha qirralar ko'paytmasi"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "(1/3) × Asos yuzasi × balandlik",
            "topic": "piramida",
            "grade": 10,
            "difficulty": difficulty
        }

    def generate_silindr(self, difficulty: str) -> Dict:
        r = random.randint(2, 5)
        h = random.randint(3, 8)
        correct = round(3.14 * r * r * h, 2)
        question = f"Silindrning radiusi {r} sm, balandligi {h} sm. Hajmini toping (π ≈ 3.14)"
        
        distractors = self.generate_distractors(correct, "silindr", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "silindr",
            "grade": 10,
            "difficulty": difficulty
        }

    def generate_konus(self, difficulty: str) -> Dict:
        question = "Konusning hajmi formulasini ko'rsating"
        options = {
            "A": "V = (1/3)πr²h",
            "B": "V = πr²h",
            "C": "V = (2/3)πr²h",
            "D": "V = πr²h/2"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "V = (1/3)πr²h",
            "topic": "konus",
            "grade": 10,
            "difficulty": difficulty
        }

    def generate_shar_10(self, difficulty: str) -> Dict:
        r = random.randint(2, 5)
        correct = round((4/3) * 3.14 * r**3, 2)
        question = f"Sharning radiusi {r} sm. Hajmini toping (π ≈ 3.14)"
        
        distractors = self.generate_distractors(correct, "shar", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "shar_10",
            "grade": 10,
            "difficulty": difficulty
        }

    def generate_hosila_tarifi(self, difficulty: str) -> Dict:
        question = "Funksiyaning hosilasi deb nimaga aytiladi?"
        options = {
            "A": "Funksiyaning o'zgarish tezligi",
            "B": "Funksiyaning qiymati",
            "C": "Funksiyaning eng katta qiymati",
            "D": "Funksiyaning eng kichik qiymati"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "Funksiyaning o'zgarish tezligi",
            "topic": "hosila_tarifi",
            "grade": 11,
            "difficulty": difficulty
        }

    def generate_hosila_qoidalari(self, difficulty: str) -> Dict:
        question = "(u·v)' = ?"
        options = {
            "A": "u'v + uv'",
            "B": "u'v - uv'",
            "C": "u'v'",
            "D": "u' + v'"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "u'v + uv'",
            "topic": "hosila_qoidalari",
            "grade": 11,
            "difficulty": difficulty
        }

    def generate_ekstremum(self, difficulty: str) -> Dict:
        question = "Funksiyaning ekstremum nuqtasida hosila..."
        options = {
            "A": "0 ga teng",
            "B": "1 ga teng",
            "C": "Musbat",
            "D": "Manfiy"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "0 ga teng",
            "topic": "ekstremum",
            "grade": 11,
            "difficulty": difficulty
        }

    def generate_integral(self, difficulty: str) -> Dict:
        question = "∫xⁿdx = ?"
        options = {
            "A": "xⁿ⁺¹/(n+1) + C",
            "B": "nxⁿ⁻¹ + C",
            "C": "xⁿ + C",
            "D": "(n+1)xⁿ + C"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "xⁿ⁺¹/(n+1) + C",
            "topic": "integral",
            "grade": 11,
            "difficulty": difficulty
        }

    def generate_permutatsiya(self, difficulty: str) -> Dict:
        n = random.randint(5, 8)
        correct = math.factorial(n)
        question = f"P({n}, {n}) = {n}! nechiga teng?"
        
        distractors = self.generate_distractors(correct, "permutatsiya", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "permutatsiya",
            "grade": 11,
            "difficulty": difficulty
        }

    def generate_kombinatsiya(self, difficulty: str) -> Dict:
        n = random.randint(5, 8)
        r = random.randint(2, 4)
        correct = math.comb(n, r)
        question = f"C({n}, {r}) = ?"
        
        distractors = self.generate_distractors(correct, "kombinatsiya", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "kombinatsiya",
            "grade": 11,
            "difficulty": difficulty
        }

    def generate_ehtimollik(self, difficulty: str) -> Dict:
        favorable = random.randint(1, 5)
        total = random.randint(favorable + 1, 10)
        correct = round(favorable / total, 2)
        question = f"Sovg'alarda {total} ta shar bor, shundan {favorable} tasi qizil. Qizil shar olish ehtimolligi?"
        
        distractors = self.generate_distractors(correct, "ehtimollik", 3)
        options, correct_label = self.format_distractors(correct, distractors)
        
        return {
            "question": question,
            "options": options,
            "correct": correct_label,
            "correct_value": correct,
            "topic": "ehtimollik",
            "grade": 11,
            "difficulty": difficulty
        }

    def generate_sinuslar_teoremasi_11(self, difficulty: str) -> Dict:
        question = "Sinuslar teoremasi formulasini ko'rsating"
        options = {
            "A": "a/sin(A) = b/sin(B) = c/sin(C)",
            "B": "a·sin(A) = b·sin(B) = c·sin(C)",
            "C": "a + sin(A) = b + sin(B)",
            "D": "a² = b² + c² - 2bc·cos(A)"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "a/sin(A) = b/sin(B) = c/sin(C)",
            "topic": "sinuslar_teoremasi_11",
            "grade": 11,
            "difficulty": difficulty
        }

    def generate_kosinuslar_teoremasi_11(self, difficulty: str) -> Dict:
        question = "Kosinuslar teoremasi formulasini ko'rsating"
        options = {
            "A": "a² = b² + c² - 2bc·cos(A)",
            "B": "a/sin(A) = b/sin(B)",
            "C": "a = b + c",
            "D": "a² = b² + c²"
        }
        
        return {
            "question": question,
            "options": options,
            "correct": "A",
            "correct_value": "a² = b² + c² - 2bc·cos(A)",
            "topic": "kosinuslar_teoremasi_11",
            "grade": 11,
            "difficulty": difficulty
        }

    def get_topic_suggestions(self, subject: str, grade: int) -> List[str]:
        """Fanga qarab mavzu tavsiyalarini beradi"""
        subject_lower = subject.lower()
        
        suggestions = {
            "matematika": {
                "description": "Matematika mavzulari",
                "topics": [
                    "Sonlar va arifmetika",
                    "Kasrlar va foizlar",
                    "Tenglamalar",
                    "Geometriya asoslari",
                    "O'lchovlar va birliklar"
                ]
            },
            "algebra": {
                "description": "Algebra mavzulari",
                "topics": [
                    "Algebraik ifodalar",
                    "Tenglamalar va tengsizliklar",
                    "Funksiyalar",
                    "Ko'paytirish formulalari",
                    "Darajalar va ildizlar"
                ]
            },
            "geometriya": {
                "description": "Geometriya mavzulari",
                "topics": [
                    "Uchburchaklar",
                    "To'rtburchaklar",
                    "Aylana va doira",
                    "Perimetr va yuza",
                    "Burchaklar"
                ]
            }
        }
        
        for key, data in suggestions.items():
            if key in subject_lower or subject_lower in key:
                return data["topics"]
        
        topics = self.get_topics_by_grade(grade)
        readable_topics = [t.replace("_", " ").title() for t in topics[:8]]
        return readable_topics

    def get_all_topics_flat(self) -> List[str]:
        """Barcha mavzularni tekis ro'yxatda qaytaradi"""
        all_topics = []
        for topics in self.TOPICS_BY_GRADE.values():
            all_topics.extend(topics)
        return list(set(all_topics))

topic_generator = TopicGenerator()
