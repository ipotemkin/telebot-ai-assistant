"""Асинхронный HTTP-клиент для работы с API ProxyAPI (aiohttp)."""

import json
import logging
from http import HTTPStatus
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class APIClient:
    """Асинхронный клиент для работы с ProxyAPI."""

    OPENAI_ENDPOINT = "https://api.proxyapi.ru/openai/v1/chat/completions"
    OPENAI_COMPATIBLE_ENDPOINT = (
        "https://openai.api.proxyapi.ru/v1/chat/completions"
    )

    def __init__(self, api_key: str, timeout: int = 120):
        """
        Инициализация клиента.

        Args:
            api_key: API ключ для ProxyAPI
            timeout: Таймаут запроса в секундах
        """
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        url: str,
        payload: dict[str, Any],
        use_alt_endpoint: bool = False,
    ) -> tuple[int, dict[str, Any]] | None:
        """
        Выполнить HTTP запрос к API.

        Args:
            session: Сессия aiohttp
            url: URL endpoint
            payload: Данные запроса
            use_alt_endpoint: При не-200 вернуть None (попробовать другой URL)

        Returns:
            Кортеж (status_code, response_data) или None при ошибке
        """
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Authorization": f"Bearer {self.api_key}",
        }
        logger.debug("Отправка запроса к %s", url)
        logger.debug(
            "Payload: %s",
            json.dumps(payload, ensure_ascii=False, indent=2),
        )
        try:
            async with session.post(
                url, json=payload, headers=headers, timeout=self.timeout
            ) as resp:
                status_code = resp.status
                body = await resp.text()
                try:
                    response_data: dict[str, Any] = json.loads(body)
                except json.JSONDecodeError:
                    response_data = {"raw_response": body}

                if status_code != HTTPStatus.OK and use_alt_endpoint:
                    logger.warning(
                        "Первая попытка не удалась (код %s), "
                        "пробуем альтернативный endpoint",
                        status_code,
                    )
                    return None
                return (status_code, response_data)
        except aiohttp.ClientError as e:
            logger.error("Ошибка при запросе к %s: %s", url, e)
            raise

    async def send_openai_request(
        self,
        model_id: str,
        messages: list,
        thinking: dict[str, Any] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """
        Отправить запрос через OpenAI-совместимый API.

        Args:
            model_id: ID модели
            messages: История сообщений
            thinking: Параметры рассуждений (опционально)
            temperature: Temperature (опционально)
            max_tokens: Макс. токенов в ответе (опционально)

        Returns:
            Ответ API
        """
        payload: dict[str, Any] = {"model": model_id, "messages": messages}
        if thinking:
            payload["thinking"] = thinking
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        async with aiohttp.ClientSession() as session:
            response = await self._make_request(
                session,
                self.OPENAI_COMPATIBLE_ENDPOINT,
                payload,
                use_alt_endpoint=True,
            )
            if response is None:
                response = await self._make_request(
                    session, self.OPENAI_ENDPOINT, payload
                )
            if response is None:
                raise Exception("Не удалось выполнить запрос к API")
            return self._handle_response(response)

    def _handle_response(
        self, response: tuple[int, dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Обработать ответ API.

        Args:
            response: Кортеж (status_code, response_data)

        Returns:
            Распарсенный JSON ответ

        Raises:
            Exception: При ошибке API
        """
        status_code, response_data = response
        if status_code != HTTPStatus.OK:
            error_msg = self._format_error(response_data, status_code)
            logger.error(error_msg)
            raise Exception(error_msg)
        return response_data

    def _format_error(
        self, error_data: dict[str, Any], status_code: int
    ) -> str:
        """Форматировать сообщение об ошибке API."""
        error_msg = f"Ошибка API (код {status_code})"
        if "detail" in error_data:
            error_msg += f": {error_data['detail']}"
        elif "error" in error_data:
            error_obj = error_data.get("error", {})
            if isinstance(error_obj, dict):
                error_msg += f": {error_obj.get('message', 'Unknown error')}"
            else:
                error_msg += f": {error_obj}"
        elif "message" in error_data:
            error_msg += f": {error_data['message']}"
        return error_msg
