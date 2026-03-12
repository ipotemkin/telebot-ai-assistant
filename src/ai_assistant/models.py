"""Конфигурация моделей для AI ассистентов."""

from typing import Any

# Доступные модели (OpenAI через ProxyAPI)
MODELS: dict[str, dict[str, Any]] = {
    "1": {
        "name": "GPT-4o",
        "id": "gpt-4o",
        "provider": "openai",
        "supports_thinking": False,
        "class_name": "OpenAIAssistant",
    },
}


def get_model_config(model_key: str) -> dict[str, Any]:
    """
    Получить конфигурацию модели по ключу.

    Args:
        model_key: Ключ модели ("1")

    Returns:
        Конфигурация модели

    Raises:
        ValueError: Если модель не найдена
    """
    if model_key not in MODELS:
        raise ValueError(f"Неизвестный ключ модели: {model_key}")
    return MODELS[model_key]


def list_models() -> dict[str, dict[str, Any]]:
    """
    Получить список всех доступных моделей.

    Returns:
        Словарь с конфигурациями моделей
    """
    return MODELS.copy()
