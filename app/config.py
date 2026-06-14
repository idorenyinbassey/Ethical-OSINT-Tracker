import os
import secrets


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
    DB_URL = os.getenv("DB_URL", "sqlite:///./dev.db")
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
