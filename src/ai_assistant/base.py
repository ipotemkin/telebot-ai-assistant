"""Базовые классы для AI ассистентов (асинхронные)."""

import logging
from abc import ABC, abstractmethod

from .client import APIClient

logger = logging.getLogger(__name__)


class BaseAssistant(ABC):
    """Абстрактный базовый класс для AI ассистентов."""

    def __init__(self, api_key: str, model_config: dict):
        """
        Инициализация ассистента.

        Args:
            api_key: API ключ для ProxyAPI
            model_config: Конфигурация модели
        """
        self.api_key = api_key
        self.model_config = model_config
        self.conversation_history: list[dict[str, str]] = []
        self.client = APIClient(api_key)

    def add_message(self, role: str, content: str) -> None:
        """
        Добавить сообщение в историю диалога.

        Args:
            role: Роль отправителя ('user' или 'assistant')
            content: Содержимое сообщения
        """
        self.conversation_history.append({"role": role, "content": content})
        logger.debug(
            "Добавлено сообщение: role=%s, content_length=%s",
            role,
            len(content),
        )

    def clear_history(self) -> None:
        """Очистить историю диалога."""
        self.conversation_history = []
        logger.info("История диалога очищена")

    @abstractmethod
    async def send_message(self, user_message: str) -> tuple[str, str | None]:
        """
        Отправить сообщение модели и получить ответ.

        Args:
            user_message: Сообщение пользователя

        Returns:
            Tuple[ответ_модели, рассуждения_или_None]
        """
        pass

    @abstractmethod
    def _extract_thinking(self, response_data: dict) -> str | None:
        """
        Извлечь рассуждения из ответа API.

        Args:
            response_data: Данные ответа API

        Returns:
            Рассуждения или None
        """
        pass

    @abstractmethod
    def _build_payload(self, messages: list[dict]) -> dict:
        """
        Построить payload для запроса.

        Args:
            messages: История сообщений

        Returns:
            Payload для API запроса
        """
        pass


class Assistant(BaseAssistant):
    """Базовый класс с общей реализацией для ассистентов."""

    async def send_message(self, user_message: str) -> tuple[str, str | None]:
        """
        Отправить сообщение модели и получить ответ.

        Args:
            user_message: Сообщение пользователя

        Returns:
            Tuple[ответ_модели, рассуждения_или_None]
        """
        if not self.model_config:
            raise ValueError("Модель не выбрана")

        self.add_message("user", user_message)
        limit = self.model_config.get("context_len_messages", 0)
        messages_for_api = (
            self.conversation_history[-limit:]
            if limit > 0
            else self.conversation_history
        )

        try:
            payload = self._build_payload(messages_for_api)
            response_data = await self._send_api_request(payload)

            assistant_message = self._extract_message(response_data)
            thinking_content = self._extract_thinking(response_data)

            self.add_message("assistant", assistant_message)
            if limit > 0 and len(self.conversation_history) > limit:
                self.conversation_history = (
                    self.conversation_history[-limit:]
                )

            logger.info(
                "Получен ответ: message_length=%s, thinking_length=%s",
                len(assistant_message),
                len(thinking_content) if thinking_content else 0,
            )

            return assistant_message, thinking_content

        except Exception as e:
            logger.error("Ошибка при отправке сообщения: %s", e)
            raise

    def _extract_message(self, response_data: dict) -> str:
        """
        Извлечь сообщение из ответа API.

        Args:
            response_data: Данные ответа API

        Returns:
            Сообщение ассистента
        """
        if "choices" in response_data:
            message_data = response_data["choices"][0]["message"]
            content = message_data.get("content", "")
            return str(content) if content else ""

        # Нативный Anthropic формат
        content_blocks = response_data.get("content", [])
        message = ""
        for block in content_blocks:
            if block.get("type") == "text":
                message += block.get("text", "")
        return message

    @abstractmethod
    async def _send_api_request(self, payload: dict) -> dict:
        """
        Отправить запрос к API.

        Args:
            payload: Payload запроса

        Returns:
            Ответ API
        """
        pass
