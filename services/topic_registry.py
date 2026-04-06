"""
services/topic_registry.py

Tizimdagi barcha fanlar va mavzular registrysi (1-11 sinflar uchun).
"""

TOPICS_BY_GRADE = {
    1: [
        {"slug": "sonlar_0_100", "title": "Sonlar va sanash (0–100)"},
        {"slug": "son_tarkibi", "title": "Son tarkibi (7 = 5 + 2)"},
        {"slug": "taqqoslash", "title": "Katta, kichik, teng tushunchasi"},
        {"slug": "qoshish", "title": "Qo'shish va ayirish (sodda)"},
        {"slug": "qavs_tanish", "title": "Qavslar bilan tanishish"},
        {"slug": "uzunlik_sm", "title": "Uzunlik (sm) o'lchash"},
        {"slug": "vaqt_yaxlit", "title": "Vaqt: soat va daqiqa"},
        {"slug": "shakllar", "title": "Nuqta, kesma, shakllar"},
    ],
    2: [
        {"slug": "sonlar_1000", "title": "Uch xonali sonlar (0–1000)"},
        {"slug": "razryadlar", "title": "Razryadlar: birlik, o'nlik, yuzlik"},
        {"slug": "qoshish_ayirish_ustun", "title": "Qo'shish va ayirish (ustun usul)"},
        {"slug": "kopaytirish_jadval", "title": "Ko'paytirish va bo'lish tushunchasi"},
        {"slug": "noma_lum_x_topish", "title": "Noma'lum sonni topish (x + 5 = 9)"},
        {"slug": "uzunlik_sm_dm_m", "title": "Uzunlik: sm, dm, m"},
        {"slug": "massa_kg", "title": "Massa (kg) va Hajm (litr)"},
        {"slug": "burchak", "title": "Burchak turlari va kesma uzunligi"},
    ],
    3: [
        {"slug": "sonlar_10000", "title": "Katta sonlar (0–10 000)"},
        {"slug": "kopaytirish_jadvali_toliq", "title": "Ko'paytirish jadvali (to'liq)"},
        {"slug": "kopaytirish_2xonali_1xonali", "title": "2 xonali sonni 1 xonali songa ko'paytirish"},
        {"slug": "bolish_qoldiq", "title": "Bo'lish (qoldiq bilan)"},
        {"slug": "kasr_tushuncha", "title": "Oddiy kasrlar (surat va maxraj)"},
        {"slug": "vaqt_sekund_minut_soat", "title": "Vaqt (sekund, minut, soat)"},
        {"slug": "perimetr", "title": "Perimetr: to'g'ri to'rtburchak va kvadrat"},
        {"slug": "mantiqiy_masalalar", "title": "Mantiqiy masalalar"},
    ],
    4: [
        {"slug": "sonlar_million", "title": "Ko'p xonali sonlar (0–1 000 000)"},
        {"slug": "kopaytirish_2_3xonali", "title": "Ko'paytirish (2–3 xonali sonlar)"},
        {"slug": "bolish_ustun", "title": "Bo'lish (ustun usul / qoldiqli)"},
        {"slug": "kasr_qoshish_ayirish", "title": "Kasrlarni qo'shish va ayirish (bir xil maxraj)"},
        {"slug": "onli_kasrlar", "title": "O'nli kasrlar (boshlanish: 0.1, 0.5)"},
        {"slug": "tezlik_masofa_vaqt", "title": "Tezlik, vaqt va masofa (v = s/t)"},
        {"slug": "yuzani_hisoblash", "title": "Yuzani hisoblash (S = a*b)"},
        {"slug": "fazoviy_shakllar", "title": "Fazoviy shakllar: kub, prizma, shar"},
    ],
    5: [
        {"slug": "natural_sonlar", "title": "Natural sonlar va amallar"},
        {"slug": "tub_murakkab_sonlar", "title": "Tub va murakkab sonlar"},
        {"slug": "boluvchilar_karralilar", "title": "Bo'luvchilar va karralilar"},
        {"slug": "kasrlarni_qisqartirish_5", "title": "Oddiy kasrlarni qisqartirish"},
        {"slug": "onli_kasrlar_amallar_5", "title": "O'nli kasrlar bilan amallar"},
        {"slug": "harfli_ifodalar", "title": "Harfli ifodalar va formulalar"},
        {"slug": "burchaklar_5", "title": "Uchburchak turlari va burchaklari"},
        {"slug": "perimetr_yuza_5", "title": "Perimetr va yuza masalalari"},
    ],
    6: [
        {"slug": "manfiy_musbat_sonlar", "title": "Manfiy va musbat sonlar"},
        {"slug": "koordinata_togri_chiziq", "title": "Koordinata to'g'ri chizig'i"},
        {"slug": "nisbat", "title": "Nisbat va proporsiya"},
        {"slug": "foiz_topish", "title": "Masshtab va Foiz hisobi"},
        {"slug": "algebraik_ifodalar_6", "title": "Algebraik ifodalar va qavslarni ochish"},
        {"slug": "burchaklar_yigindisi", "title": "Burchaklar yigindisi"},
        {"slug": "aylana_va_doira", "title": "Aylana va doira yuzasi"},
    ],
    7: [
        {"slug": "algebraik_ifodalar_7", "title": "Algebraik ifodalar va ko'phadlar"},
        {"slug": "qisqartirilgan_kopaytirish", "title": "Qisqartirilgan ko'paytirish formulalari"},
        {"slug": "bir_noma_lumli_tenglamalar_7", "title": "Bir noma'lumli tenglamalar va tengsizliklar"},
        {"slug": "funksiya_tushuncha", "title": "Funksiya tushunchasi va grafiklar"},
        {"slug": "parallel_chiziqlar_7", "title": "Parallel chiziqlar xossalari"},
        {"slug": "uchburchak_7", "title": "Uchburchak: median, balandlik, bissektrisa"},
    ],
    8: [
        {"slug": "kasrli_ifodalar_8", "title": "Algebraik kasrlar va soddalashtirish"},
        {"slug": "kvadrat_tenglama", "title": "Kvadrat tenglamalar (Diskriminant)"},
        {"slug": "tengsizliklar_8", "title": "Chiziqli tengsizliklar"},
        {"slug": "togri_tortburchaklar_8", "title": "To'rtburchaklar: parallelogramm, trapetsiya"},
        {"slug": "aylana_8", "title": "Aylana: markaziy burchak va yoy"},
        {"slug": "pifagor_teoremasi", "title": "Pifagor teoremasi"},
    ],
    9: [
        {"slug": "vieta_formulasi", "title": "Vieta formulasi"},
        {"slug": "kvadrat_funksiya", "title": "Kvadrat funksiya va uning grafigi"},
        {"slug": "kvadrat_tengsizliklar_9", "title": "Kvadrat tengsizliklar"},
        {"slug": "arifmetik_progressiya", "title": "Arifmetik va geometrik progressiyalar"},
        {"slug": "uchburchaklar_o_xshashligi", "title": "Uchburchaklar o'xshashligi"},
        {"slug": "trigonometriya_9", "title": "Trigonometriya (sin, cos, tan boshlanish)"},
        {"slug": "aylana_uzunligi", "title": "Aylana uzunligi va doira yuzi"},
    ],
    10: [
        {"slug": "korsatkichli_funksiya", "title": "Ko'rsatkichli va logarifmik funksiyalar"},
        {"slug": "trigonometrik_tenglamalar_10", "title": "Trigonometrik tenglamalar"},
        {"slug": "ketma_ketliklar_10", "title": "Ketma-ketliklar va limit tushunchasi"},
        {"slug": "togri_chiziq_va_tekislik", "title": "Fazoviy geometriya: parallellik va perpendikulyarlik"},
        {"slug": "fazoviy_shakllar_hajmlari", "title": "Prizma, piramida, silindr, konus, shar"},
    ],
    11: [
        {"slug": "hosila_jadvali", "title": "Hosila (derivative) va uning qoidalari"},
        {"slug": "ekstremum", "title": "Ekstremumlar va grafiklar tahlili"},
        {"slug": "integral", "title": "Integral (boshlang'ich funksiya)"},
        {"slug": "logarifmik_tenglamalar_11", "title": "Logarifmik va trigonometrik tenglamalar (murakkab)"},
        {"slug": "ehtimollik", "title": "Kombinatorika va Ehtimollik nazariyasi"},
        {"slug": "fazoviy_geometriya_11", "title": "Fazoviy shakllar: hajm va yuzalar"},
    ],
}

SUBJECT_TYPES = {
    "Matematika": ["Algebra / Matematika", "Geometriya", "Boshqotirma", "Mantiqiy fikrlash"],
    "Geometriya": ["Geometriya"],
    "Ehtimollik": ["Algebra / Matematika"],
    "Mantiq": ["Boshqotirma", "Mantiqiy fikrlash", "IQ / Tanqidiy fikrlash", "Prezident maktabi"],
    "IQ": ["IQ / Tanqidiy fikrlash"],
    "Prezident maktabi": ["Prezident maktabi", "IQ / Tanqidiy fikrlash"],
}

def get_topics_for_grade(grade: int) -> list[dict]:
    return TOPICS_BY_GRADE.get(grade, TOPICS_BY_GRADE[5])

def get_all_subjects() -> list[str]:
    return list(SUBJECT_TYPES.keys())
