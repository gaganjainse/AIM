from datetime import timedelta
import os
import sys

from dotenv import load_dotenv


if getattr(sys, "frozen", False):
    _BASE_PATH = sys._MEIPASS
else:
    _BASE_PATH = os.path.abspath(".")

load_dotenv(os.path.join(_BASE_PATH, ".env"))


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class Config:
    BASE_DIR = _BASE_PATH
    TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
    STATIC_DIR = os.path.join(BASE_DIR, "static")
    DATA_DIR = os.path.join(BASE_DIR, "data")
    BACKUP_DIR = os.path.join(BASE_DIR, "backups")

    SECRET_KEY = _required_env("FLASK_SECRET")

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = _env_int("DB_PORT", 3306)
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = _required_env("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME", "attendance_db")
    DB_POOL_SIZE = _env_int("DB_POOL_SIZE", 5)
    MYSQL_BIN = os.getenv("MYSQL_BIN", "mysql")
    MYSQLDUMP_BIN = os.getenv("MYSQLDUMP_BIN", "mysqldump")
    DEBUG = _env_bool("FLASK_DEBUG", False)

    MAIL_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
    MAIL_PORT = _env_int("EMAIL_SMTP_PORT", 587)
    MAIL_USE_TLS = _env_bool("EMAIL_SMTP_TLS", True)
    MAIL_USERNAME = os.getenv("EMAIL_USER")
    MAIL_PASSWORD = os.getenv("EMAIL_PASS")
    MAIL_DEFAULT_SENDER = os.getenv("EMAIL_USER")

    MAX_LOGIN_ATTEMPTS = _env_int("MAX_LOGIN_ATTEMPTS", 5)
    LOGIN_LOCK_MINUTES = _env_int("LOGIN_LOCK_MINUTES", 15)
    SESSION_LIFETIME_MINUTES = _env_int("SESSION_LIFETIME_MINUTES", 30)
    MAX_CONTENT_LENGTH = _env_int("MAX_CONTENT_LENGTH_MB", 10) * 1024 * 1024
    TRUST_PROXY_COUNT = max(0, _env_int("TRUST_PROXY_COUNT", 1))
    BACKUP_RETENTION_DAYS = _env_int("BACKUP_RETENTION_DAYS", 30)
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "aim_session")

    PERMANENT_SESSION_LIFETIME = timedelta(minutes=SESSION_LIFETIME_MINUTES)
    SESSION_PERMANENT = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    JSON_SORT_KEYS = False

    # ── Rate Limiting ──────────────────────────────────────────────────────────
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per day, 50 per hour")
    RATELIMIT_HEADERS_ENABLED = True

    # ── Caching ─────────────────────────────────────────────────────────────────
    CACHE_TYPE = os.getenv("CACHE_TYPE", "SimpleCache")
    CACHE_REDIS_URL = os.getenv("CACHE_REDIS_URL")
    CACHE_DEFAULT_TIMEOUT = _env_int("CACHE_DEFAULT_TIMEOUT", 300)

    # ── CORS ────────────────────────────────────────────────────────────────────
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []

    # ── Argon2id ────────────────────────────────────────────────────────────────
    ARGON2_TIME_COST = _env_int("ARGON2_TIME_COST", 2)
    ARGON2_MEMORY_COST = _env_int("ARGON2_MEMORY_COST", 65536)
    ARGON2_PARALLELISM = _env_int("ARGON2_PARALLELISM", 4)

    # ── Backup Encryption ───────────────────────────────────────────────────────
    BACKUP_ENCRYPTION_KEY = os.getenv("BACKUP_ENCRYPTION_KEY", "")

    # ── Metrics ─────────────────────────────────────────────────────────────────
    METRICS_ENABLED = _env_bool("METRICS_ENABLED", True)
