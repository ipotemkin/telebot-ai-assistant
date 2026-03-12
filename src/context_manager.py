"""Хранение контекста диалога: память + SQLite, восстановление при перезапуске."""

import asyncio
import logging
from pathlib import Path
from typing import Any

from ai_assistant.openai_assistant import OpenAIAssistant
from context_storage import (
    clear_context as storage_clear,
    get_user_settings as storage_get_settings,
    init_db,
    load_context as storage_load,
    save_context as storage_save,
    set_user_setting as storage_set_setting,
)

logger = logging.getLogger(__name__)


class ContextManager:
    """Менеджер контекста: один ассистент на пользователя, история в SQLite."""

    def __init__(
        self,
        api_key: str,
        model_id: str,
        temperature: float,
        max_tokens: int,
        context_len_messages: int,
        db_path: Path,
    ):
        """
        Инициализация.

        Args:
            api_key: Ключ API (OpenAI/ProxyAPI).
            model_id: ID модели (например gpt-4o).
            temperature: Temperature для генерации.
            max_tokens: Максимум токенов в ответе.
            context_len_messages: Макс. число сообщений в контексте.
            db_path: Путь к файлу SQLite.
        """
        self._api_key = api_key
        self._model_config: dict[str, Any] = {
            "id": model_id,
            "name": model_id,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "context_len_messages": context_len_messages,
        }
        self._db_path = db_path
        self._assistants: dict[int, OpenAIAssistant] = {}
        self._lock = asyncio.Lock()
        init_db(db_path)

    async def _get_user_settings_async(self, user_id: int) -> dict[str, str]:
        """Загрузить настройки пользователя из БД (в executor)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: storage_get_settings(self._db_path, user_id),
        )

    def _make_assistant(
        self,
        initial_history: list[dict[str, str]],
        model_config: dict[str, Any],
    ) -> OpenAIAssistant:
        """Создать ассистента с заданной историей и конфигом."""
        assistant = OpenAIAssistant(self._api_key, dict(model_config))
        assistant.conversation_history = list(initial_history)
        return assistant

    async def get_assistant(self, user_id: int) -> OpenAIAssistant:
        """
        Получить ассистента для пользователя (из кэша или загрузить из БД).

        Args:
            user_id: ID пользователя Telegram.

        Returns:
            OpenAIAssistant с историей диалога этого пользователя.
        """
        async with self._lock:
            if user_id in self._assistants:
                return self._assistants[user_id]
            settings = await self._get_user_settings_async(user_id)
            config = dict(self._model_config)
            if "model_id" in settings:
                config["id"] = settings["model_id"]
                config["name"] = settings["model_id"]
            if "max_tokens" in settings:
                try:
                    config["max_tokens"] = int(settings["max_tokens"])
                except ValueError:
                    pass
            if "context_len_messages" in settings:
                try:
                    config["context_len_messages"] = int(
                        settings["context_len_messages"]
                    )
                except ValueError:
                    pass
            if "temperature" in settings:
                try:
                    config["temperature"] = float(settings["temperature"])
                except ValueError:
                    pass
            limit = config.get("context_len_messages", 20)
            loop = asyncio.get_event_loop()
            history = await loop.run_in_executor(
                None,
                lambda: storage_load(self._db_path, user_id, limit),
            )
            self._assistants[user_id] = self._make_assistant(history, config)
            logger.info(
                "Загружен контекст для user_id=%s, сообщений=%s",
                user_id,
                len(history),
            )
            return self._assistants[user_id]

    async def persist_context(self, user_id: int) -> None:
        """
        Сохранить историю диалога пользователя в SQLite (после обмена).

        Обрезает историю до context_len_messages перед сохранением.

        Args:
            user_id: ID пользователя Telegram.
        """
        async with self._lock:
            if user_id not in self._assistants:
                return
            assistant = self._assistants[user_id]
            limit = self._model_config.get("context_len_messages", 20)
            history = assistant.conversation_history
            if limit > 0 and len(history) > limit:
                history = history[-limit:]
            to_save = list(history)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: storage_save(self._db_path, user_id, to_save),
        )

    async def clear_context(self, user_id: int) -> None:
        """
        Очистить историю диалога пользователя (память и БД).

        Args:
            user_id: ID пользователя Telegram.
        """
        async with self._lock:
            if user_id in self._assistants:
                self._assistants[user_id].clear_history()
                logger.info("Контекст очищен в памяти для user_id=%s", user_id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: storage_clear(self._db_path, user_id),
        )

    async def set_user_setting(
        self, user_id: int, key: str, value: str
    ) -> None:
        """
        Установить настройку пользователя и сбросить кэш ассистента.

        Args:
            user_id: ID пользователя Telegram.
            key: model_id, max_tokens или context_len_messages.
            value: Строковое значение.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: storage_set_setting(self._db_path, user_id, key, value),
        )
        async with self._lock:
            if user_id in self._assistants:
                del self._assistants[user_id]
                logger.info(
                    "Сброшен кэш ассистента для user_id=%s после смены %s",
                    user_id,
                    key,
                )

    async def get_user_model_info(self, user_id: int) -> dict[str, Any]:
        """
        Текущие настройки модели для пользователя (модель, temperature,
        max_tokens, context_len_messages).
        """
        settings = await self._get_user_settings_async(user_id)
        info = {
            "name": self._model_config.get("name", ""),
            "id": self._model_config.get("id", ""),
            "temperature": self._model_config.get("temperature", 0.0),
            "max_tokens": self._model_config.get("max_tokens", 0),
            "context_len_messages": self._model_config.get(
                "context_len_messages", 0
            ),
        }
        if "model_id" in settings:
            info["id"] = settings["model_id"]
            info["name"] = settings["model_id"]
        if "max_tokens" in settings:
            try:
                info["max_tokens"] = int(settings["max_tokens"])
            except ValueError:
                pass
        if "context_len_messages" in settings:
            try:
                info["context_len_messages"] = int(
                    settings["context_len_messages"]
                )
            except ValueError:
                pass
        if "temperature" in settings:
            try:
                info["temperature"] = float(settings["temperature"])
            except ValueError:
                pass
        return info

    def get_model_info(self) -> dict[str, Any]:
        """Информация о модели по умолчанию для логов."""
        return {
            "name": self._model_config.get("name", ""),
            "id": self._model_config.get("id", ""),
        }
