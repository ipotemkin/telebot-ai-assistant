"""Сохранение и загрузка контекста диалога в SQLite."""

import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _ensure_dir(path: Path) -> None:
    """Создать родительский каталог файла при необходимости."""
    path.parent.mkdir(parents=True, exist_ok=True)


def init_db(db_path: Path) -> None:
    """
    Создать таблицы контекста и настроек, если их нет.

    Args:
        db_path: Путь к файлу SQLite.
    """
    _ensure_dir(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS context (
                user_id INTEGER NOT NULL,
                seq INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                PRIMARY KEY (user_id, seq)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (user_id, key)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
    logger.info("Инициализирована БД контекста: %s", db_path)


def get_user_settings(db_path: Path, user_id: int) -> dict[str, str]:
    """
    Загрузить настройки пользователя (key -> value).

    Args:
        db_path: Путь к SQLite.
        user_id: ID пользователя Telegram.

    Returns:
        Словарь настроек (model_id, max_tokens, context_len_messages).
    """
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT key, value FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return {r[0]: r[1] for r in rows}
    finally:
        conn.close()


def set_user_setting(
    db_path: Path, user_id: int, key: str, value: str
) -> None:
    """
    Установить настройку пользователя.

    Args:
        db_path: Путь к SQLite.
        user_id: ID пользователя Telegram.
        key: Ключ (model_id, max_tokens, context_len_messages).
        value: Строковое значение.
    """
    _ensure_dir(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO user_settings (user_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT (user_id, key) DO UPDATE SET value = excluded.value
            """,
            (user_id, key, value),
        )
        conn.commit()
    finally:
        conn.close()


def load_context(
    db_path: Path, user_id: int, limit: int
) -> list[dict[str, str]]:
    """
    Загрузить последние limit сообщений пользователя (в порядке seq).

    Args:
        db_path: Путь к SQLite.
        user_id: ID пользователя Telegram.
        limit: Максимум сообщений (0 = без ограничения).

    Returns:
        Список {"role": ..., "content": ...}.
    """
    conn = sqlite3.connect(db_path)
    try:
        if limit <= 0:
            rows = conn.execute(
                "SELECT role, content FROM context WHERE user_id = ? "
                "ORDER BY seq",
                (user_id,),
            ).fetchall()
        else:
            # Подзапрос: последние limit по seq, затем по порядку
            rows = conn.execute(
                """
                SELECT role, content FROM context
                WHERE user_id = ? AND seq IN (
                    SELECT seq FROM context WHERE user_id = ?
                    ORDER BY seq DESC LIMIT ?
                )
                ORDER BY seq
                """,
                (user_id, user_id, limit),
            ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows]
    finally:
        conn.close()


def save_context(
    db_path: Path,
    user_id: int,
    messages: list[dict[str, str]],
) -> None:
    """
    Сохранить историю сообщений пользователя (полная замена).

    Args:
        db_path: Путь к SQLite.
        user_id: ID пользователя Telegram.
        messages: Список {"role": ..., "content": ...}.
    """
    if not messages:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("DELETE FROM context WHERE user_id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()
        return

    _ensure_dir(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DELETE FROM context WHERE user_id = ?", (user_id,))
        for seq, msg in enumerate(messages):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            conn.execute(
                "INSERT INTO context (user_id, seq, role, content) "
                "VALUES (?, ?, ?, ?)",
                (user_id, seq, role, content),
            )
        conn.commit()
        logger.debug("Сохранён контекст user_id=%s, сообщений=%s", user_id, len(messages))
    finally:
        conn.close()


def clear_context(db_path: Path, user_id: int) -> None:
    """
    Удалить контекст пользователя из БД.

    Args:
        db_path: Путь к SQLite.
        user_id: ID пользователя Telegram.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DELETE FROM context WHERE user_id = ?", (user_id,))
        conn.commit()
        logger.info("Контекст удалён из БД для user_id=%s", user_id)
    finally:
        conn.close()
