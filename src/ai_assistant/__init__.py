"""Пакет AI ассистентов для работы с OpenAI через ProxyAPI."""

from .base import BaseAssistant, Assistant
from .openai_assistant import OpenAIAssistant
from .models import MODELS, get_model_config, list_models

__all__ = [
    "BaseAssistant",
    "Assistant",
    "OpenAIAssistant",
    "MODELS",
    "get_model_config",
    "list_models",
]

__version__ = "1.0.0"
