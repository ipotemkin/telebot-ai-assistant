"""Конфигурация бота из переменных окружения."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Загружаем .env из корня проекта (родитель к src)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# Каталог данных по умолчанию (рядом с .env)
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "context.db"


def _get_required(key: str, env_keys: list[str] | None = None) -> str:
    """Взять значение из первой найденной переменной окружения."""
    keys = [key] if not env_keys else env_keys
    for k in keys:
        value = os.getenv(k)
        if value and value.strip():
            return value.strip()
    names = ", ".join(keys)
    raise ValueError(f"Не задана переменная окружения: {names}")


def _get_float(key: str, default: float) -> float:
    """Прочитать float из окружения."""
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value.strip())
    except ValueError:
        return default


def _get_int(key: str, default: int) -> int:
    """Прочитать int из окружения."""
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def get_bot_token() -> str:
    """Токен Telegram бота (BOT_TOKEN)."""
    return _get_required("BOT_TOKEN")


def get_openai_api_key() -> str:
    """API ключ для OpenAI/ProxyAPI (OPENAI_API_KEY, GENAPI_KEY или
    PROXYAPI_KEY).
    """
    return _get_required(
        "OPENAI_API_KEY",
        ["OPENAI_API_KEY", "GENAPI_KEY", "PROXYAPI_KEY"],
    )


def get_openai_model() -> str:
    """ID модели OpenAI (OPENAI_MODEL). По умолчанию gpt-4o."""
    return os.getenv("OPENAI_MODEL", "gpt-4o").strip() or "gpt-4o"


def get_temperature() -> float:
    """Temperature для генерации (TEMPERATURE). По умолчанию 0.7."""
    return _get_float("TEMPERATURE", 0.7)


def get_max_tokens() -> int:
    """Максимум токенов в ответе (MAX_TOKENS). По умолчанию 2048."""
    return _get_int("MAX_TOKENS", 2048)


def get_context_len_messages() -> int:
    """Размер контекстного окна в сообщениях (CONTEXT_LEN_MESSAGES).
    По умолчанию 20.
    """
    return _get_int("CONTEXT_LEN_MESSAGES", 20)


def get_db_path() -> Path:
    """Путь к файлу SQLite с контекстом (DB_PATH)."""
    value = os.getenv("DB_PATH", "").strip()
    if value:
        return Path(value)
    return DEFAULT_DB_PATH
