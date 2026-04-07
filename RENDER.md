# Render Deployment

`AI_MATH` Render uchun default holatda 3 ta xizmat ishlatadi:

- `ai-math-web`
  - Flask admin panel, `/health` va Telegram polling bot
- `ai-math-celery`
  - render, PDF, RAG va og'ir task worker
- `ai-math-beat`
  - cleanup va self-improvement schedule

Infra:

- `ai-math-db` Render Postgres
- `ai-math-redis` Render Key Value

## Fayllar

- `render.yaml`
- `requirements-render.txt`
- `requirements-dev.txt`
- `.python-version`
- `render_web.py`
- `render_bot.py`
- `render_manage.py`

## Deploy oqimi

1. Repo ni Render Blueprint sifatida ulang.
2. `render.yaml` ni sync qiling.
3. Quyidagi secretlarni kiriting:
   - `BOT_TOKEN`
   - `OPENROUTER_API_KEYS`
   - `CEREBRAS_API_KEYS`
   - `SAMBANOVA_API_KEYS`
   - `HUGGINGFACE_API_KEYS`
   - `GROQ_API_KEYS`
   - `SERPER_API_KEY`
   - `SENTRY_DSN` ixtiyoriy
4. `ADMIN_IDS` va `TEACHER_USERNAME` render.yaml orqali default keladi, kerak bo'lsa o'zgartiring.
5. Startup paytida env dagi bot token, adminlar, ustoz va AI keylar bazaga avtomatik yoziladi.
6. Web service ochilgach `/health` ni tekshiring.
7. Web service logida `Telegram boti (polling) ulandi.` yozuvi chiqishini kuting.

## Muhim eslatmalar

- Default konfiguratsiyada `python main.py` Flask va botni bitta web service ichida birga ishga tushiradi.
- `DATABASE_URL` Render Postgres’dan olinadi va kod ichida `postgresql+psycopg://` formatiga normalize qilinadi.
- `REDIS_URL` va `CELERY_RESULT_BACKEND` Render Key Value internal `connectionString` dan olinadi.
- Cache faqat `data/cache/` ichida ishlaydi va safe cleaner bilan tozalanadi.
- Celery Beat har 10 daqiqada cache cleanup, har 6 soatda self-improvement analysis taskini yuboradi.
- `PROMETHEUS_PORT` default yoqilmagan; kerak bo'lsa service env ichidan alohida qo'shiladi.

## Lokal sinov

```powershell
python render_manage.py init-db
python main.py
celery -A services.celery_app.celery_app worker -l info --concurrency=1 --prefetch-multiplier=1
celery -A services.celery_app.celery_app beat -l info
```
