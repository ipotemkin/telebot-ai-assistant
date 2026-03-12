"""Ассистент для работы с OpenAI моделями через ProxyAPI."""

import logging

from .base import Assistant

logger = logging.getLogger(__name__)


class OpenAIAssistant(Assistant):
    """Ассистент для работы с OpenAI моделями (GPT-4o)."""

    def _build_payload(self, messages: list) -> dict:
        """
        Построить payload для OpenAI API.

        Args:
            messages: История сообщений (уже обрезана по context_len)

        Returns:
            Payload для API запроса
        """
        model_id = self.model_config["id"]
        payload: dict = {"model": model_id, "messages": messages}
        if "temperature" in self.model_config:
            payload["temperature"] = self.model_config["temperature"]
        if "max_tokens" in self.model_config:
            payload["max_tokens"] = self.model_config["max_tokens"]
        return payload

    def _send_api_request(self, payload: dict) -> dict:
        """
        Отправить запрос к OpenAI API.

        Args:
            payload: Payload запроса

        Returns:
            Ответ API
        """
        return self.client.send_openai_request(
            model_id=payload["model"],
            messages=payload["messages"],
            temperature=payload.get("temperature"),
            max_tokens=payload.get("max_tokens"),
        )

    def _extract_thinking(self, response_data: dict) -> str | None:
        """
        Извлечь рассуждения из ответа OpenAI API.

        Args:
            response_data: Данные ответа API

        Returns:
            Рассуждения или None (OpenAI модели не поддерживают рассуждения)
        """
        # OpenAI модели не поддерживают рассуждения
        return None
