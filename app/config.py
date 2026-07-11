import os
import secrets


class Config:
    _raw_key = os.getenv("SECRET_KEY", "")
    if not _raw_key:
        import warnings
        _raw_key = secrets.token_hex(32)
        warnings.warn(
            "SECRET_KEY not set — generated a random key. Sessions will be "
            "invalidated on restart. Set SECRET_KEY in .env for production.",
            stacklevel=2,
        )
    SECRET_KEY = _raw_key
    WTF_CSRF_SECRET_KEY = SECRET_KEY

    # API key encryption - REQUIRED for secure API key storage
    API_KEYS_FERNET_KEY = os.getenv("API_KEYS_FERNET_KEY")

    DB_URL = os.getenv("DB_URL", "sqlite:///./dev.db")
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # Cache configuration
    CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))

    # Registration setting
    REGISTRATION_ENABLED = os.getenv("REGISTRATION_ENABLED", "False").lower() == "true"

    # Data retention (days)
    RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "90"))
