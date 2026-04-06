"""
web/app.py
Flask servisini sozlash. Buni main.py import qilib Serverda ishgatushiradi.
"""

import os

from flask import Flask

from .routes import setup_routes


def create_app():
    # Templates va static jildlarining lokatsiyasini aniq belgilash
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, "templates")
    static_dir = os.path.join(base_dir, "static")

    # Static papka mavjud bo'lmasa yaratib qo'yamiz (Flask ogohlantirishlarining oldini olish)
    os.makedirs(static_dir, exist_ok=True)

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "matematika-quiz-bot-ultra-secret")

    # Barcha router/viewlarni ruyhatdan o'tkazish
    setup_routes(app)

    return app
