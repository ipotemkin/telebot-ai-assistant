"""Клиент для работы с API ProxyAPI."""

import json
import logging
import urllib.error
import urllib.request
from http import HTTPStatus
from typing import Any

logger = logging.getLogger(__name__)


class APIClient:
    """Клиент для работы с ProxyAPI."""

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
        self.timeout = timeout

    def _make_request(
        self, url: str, payload: dict[str, Any], use_alt_endpoint: bool = False
    ) -> tuple[int, dict[str, Any]] | None:
        """
        Выполнить HTTP запрос к API.

        Args:
            url: URL endpoint
            payload: Данные запроса
            use_alt_endpoint: Использовать альтернативный endpoint при ошибке

        Returns:
            Кортеж (status_code, response_data) или None при ошибке
        """
        logger.debug("Отправка запроса к %s", url)
        logger.debug(
            "Payload: %s",
            json.dumps(payload, ensure_ascii=False, indent=2),
        )

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json; charset=UTF-8")
            req.add_header("Authorization", f"Bearer {self.api_key}")

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status_code = response.getcode()
                result = response.read().decode("utf-8")

                if status_code != HTTPStatus.OK and use_alt_endpoint:
                    logger.warning(
                        "Первая попытка не удалась (код %s), "
                        "пробуем альтернативный endpoint",
                        status_code,
                    )
                    return None

                try:
                    response_data: dict[str, Any] = json.loads(result)
                except json.JSONDecodeError:
                    response_data = {"raw_response": result}

                return (status_code, response_data)

        except urllib.error.HTTPError as e:
            status_code = e.code
            try:
                error_body = e.read().decode("utf-8")
            except (AttributeError, UnicodeDecodeError):
                error_body = ""

            if status_code != HTTPStatus.OK and use_alt_endpoint:
                logger.warning(
                    "Первая попытка не удалась (код %s), "
                    "пробуем альтернативный endpoint",
                    status_code,
                )
                return None

            try:
                error_data: dict[str, Any] = json.loads(error_body)
            except json.JSONDecodeError:
                error_data = {"raw_error": error_body}

            logger.error("Ошибка при запросе к %s: %s", url, e)
            return (status_code, error_data)

        except urllib.error.URLError as e:
            logger.error("Ошибка при запросе к %s: %s", url, e)
            raise

    def send_openai_request(
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

        response = self._make_request(
            self.OPENAI_COMPATIBLE_ENDPOINT, payload, use_alt_endpoint=True
        )

        if response is None:
            # Пробуем стандартный OpenAI endpoint
            response = self._make_request(self.OPENAI_ENDPOINT, payload)

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
        """
        Форматировать сообщение об ошибке.

        Args:
            error_data: Данные об ошибке
            status_code: HTTP статус код

        Returns:
            Отформатированное сообщение об ошибке
        """
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
