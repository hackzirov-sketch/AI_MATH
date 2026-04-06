# Render Deployment

`AI_MATH` Render uchun 4 ta xizmatga bo'lingan:

- `ai-math-web`
  - Flask admin panel va `/health`
- `ai-math-bot`
  - Telegram polling worker
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
   - `SERPER_API_KEY`
   - `SENTRY_DSN` ixtiyoriy
4. Web service ochilgach `/health` ni tekshiring.
5. Bot worker logida `Telegram boti (polling) ulandi.` yozuvi chiqishini kuting.

## Muhim eslatmalar

- Render web service botni ichida ishga tushirmaydi; bot alohida worker sifatida yuradi.
- `DATABASE_URL` Render Postgres’dan olinadi va kod ichida `postgresql+psycopg://` formatiga normalize qilinadi.
- `REDIS_URL` va `CELERY_RESULT_BACKEND` Render Key Value internal `connectionString` dan olinadi.
- Cache faqat `data/cache/` ichida ishlaydi va safe cleaner bilan tozalanadi.
- Celery Beat har 10 daqiqada cache cleanup, har 6 soatda self-improvement analysis taskini yuboradi.
- `PROMETHEUS_PORT` default yoqilmagan; kerak bo'lsa service env ichidan alohida qo'shiladi.

## Lokal sinov

```powershell
python render_manage.py init-db
python render_bot.py
gunicorn render_web:app --bind 0.0.0.0:5000 --workers 2 --timeout 180
celery -A services.celery_app.celery_app worker -l info --concurrency=1 --prefetch-multiplier=1
celery -A services.celery_app.celery_app beat -l info
```
