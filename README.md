# Telegram Matematika Quiz Boti (AI + Flask Admin Panel)

Bu loyiha to'liq o'zbek tiliga yo'naltirilgan, Telegram kanallarida matematika, geometriya va mantiqiy savollarni (Google Gemini AI yordamida) doimiy va avtomatik ravishda tashkil etadigan tizim. Bitta loyihaning o'zida ham qabul qiluvchi **Telegram Bot poller**, ham nazorat qiluvchi **Flask Admin Panel** markazlashgan holda birlashtirilgan. Baza butunlay lokal - SQLite (`database.db`) ga asoslangan, tashqi bulut DB talab qilinmaydi.

## 🚀 O'rnatish va Ishga Tushirish (Mahalliy)
1. Kutubxonalarni o'rnating: `pip install -r requirements.txt`
2. Muhit faylini yarating `.env` (mavjud bo'lmasa namunalardan oling) va maxfiy ma'lumotlarni yozing:
   ```env
   FLASK_SECRET_KEY=maxfiy_tarmoq_kaliti
   BOT_TOKEN=telegram_botfather_tokken # Yoki admin paneldan kiritsangiz ham bo'ladi
   ```
3. Dasturni yagona markazdan ishga tushiring: `python main.py`
4. Dastur bir vaqtning o'zida lokal `http://localhost:5000` manzilida Admin panelni, doimiy fonda esa Botni ishga tushiradi. Agar bazalar yo'q bo'lsa mantiqiy modelar o'zi fayl yaratib turadi.

## ☁️ Render.com da Joylashtirish (Deploy)
Loyiha aynan **Render.com** uchun yagona "entry-point" qilib mo'ljallangan va faqat bitta "Web Service" tarifida ham mukammal ishlaydi:
1. GitHub repozitoriyasiga kodni joylang, Render tizimidan ulanib "New Web Service" qiling.
2. Build Command orqali: `pip install -r requirements.txt` ni yozing.
3. Start Command qismiga esa shunchaki: `python main.py`
4. Environment Variables sahifasida:
   - Python versiyasini stabil ko'tarish uchun `PYTHON_VERSION` (Masalan `3.10.0`) qo'shing.

**Nega bunday maxsus arxitektura qilingan?**  
Render platformasi siz ko'rsatgan "Web Service" ga 60 soniya ichida PORT orqali yondashib holatni tekshiradi. Ammo Telegram polling tizimi (getUpdates bloklanishi) Port ochmaydi. Shuning uchun loyiha `main.py` bazasida Asosiy (Main) Thread orqali 0.0.0.0 manzilida Flask server ochadi (Render xotirjam bo'ladi va o'chirmaydi), hamda ayni o'sha joyda o'zining fonidagi (Daemon) maxfiy IP manzil ishlatmaydigan bot loop'ni ko'tarib oladi!

## ⚙️ Telegram Cheklovlari va Reyting Arxitekturasi (Leaderboard Yechimi)
Telegram'ning ommaviy kanallardagi Native Poll (Telegram original so'rovnomasi) xususiyatlariga ko'ra poll'larda individual ovoz beruvchining kimligi **anonim saqlanadi**. Shuning uchun ushbu bot kelgusidagi qo'shimchalar uchun quyidagi xavfsiz va aniq ball to'plash arxitekturasiga tayanadi:

1. **Kanal vazifasi**: FAQAT keng ommadan "Yosh" va "Soha"ni ajratib olish (Anonim Poll ko'tarish) hamda keyingi generatsiya qilingan Quizlarni anonim ravishda uzatish uchun ishlatiladi.  
2. **Haqiqiy Leaderboard (Ballar reytingi) ni tuzish mexanizmi**:
   * Oqimli (Realtime) reyting yig'ish kanalda bevosita anonim yechib ilojsiz ekanligi bois bu yerda ma'lumotlar bazasida mo'ljallanganidek `User` va `QuizResult` saqlab turiladi.   
   * Siz botni to'liq kanalda test qilganingizdan keyin, reytinga har bir o'quvchi qo'shilishi faqat shaxsiy suhbatga bot orqali `Inline Button (Link)` yoki qandaydir bog'langan guruh `Discussion Group` orqali yozilishini joriy etishingiz mumkin. Aynan hozirgi backend modelingiz bunga zamin tayyorlab hisoblab bera oladi.
3. **AI qismi**: Gemini sun'iy intellekti kalit limitini aylanib ishlashi, API tugab qolsa ham kodni buzilmasdan boshqasiga saqlab o'tishi barchasi qulay vizual orqali ishlaydi.

## 💡 Kelajakdagi takomillashtirish g'oyalari (Future Improvements)
- Reyting varaqasini Flask panelidek yoki undanda chiroyliroq, har xil animatsiya qilingan **Telegram WebApp** orqali har bir foydalanuvchiga profili kabi qilib namoyish qilib yozilishini qo'shish.
- Oshpazona osonlikda Matplotlib geometrik dvigatelini kuchaytirib ketish - oddiy "Geometriya hints" ni chuqurroq, kengroq parse qilib minglab uslubdagi trapetsiya va figuralarni chizuvchi murakkab funksiyalar yozish. U arxitekturaning barchasi bugun poydevor qilindi.
