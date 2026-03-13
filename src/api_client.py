"""Асинхронный клиент для диалога через OpenAIAssistant."""

import asyncio
import logging

from context_manager import ContextManager

logger = logging.getLogger(__name__)

# Блокировка по user_id: только один запрос к API на пользователя в момент
# времени, чтобы история диалога не портилась при быстрых подряд сообщениях
_user_locks: dict[int, asyncio.Lock] = {}
_locks_lock = asyncio.Lock()


async def _get_or_create_user_lock(user_id: int) -> asyncio.Lock:
    async with _locks_lock:
        if user_id not in _user_locks:
            _user_locks[user_id] = asyncio.Lock()
        return _user_locks[user_id]


async def send_user_message(
    context_manager: ContextManager,
    user_id: int,
    text: str,
) -> str:
    """
    Отправить сообщение пользователя в API и вернуть ответ ассистента.

    Запросы одного пользователя выполняются строго по очереди, чтобы
    сохранялся контекст диалога.

    Args:
        context_manager: Менеджер контекста (история по user_id).
        user_id: ID пользователя Telegram.
        text: Текст сообщения пользователя.

    Returns:
        Текст ответа ассистента.

    Raises:
        Exception: При ошибке API (пробрасывается из ассистента).
    """
    user_lock = await _get_or_create_user_lock(user_id)
    async with user_lock:
        assistant = await context_manager.get_assistant(user_id)
        model_info = context_manager.get_model_info()
        logger.info(
            "Отправка в API: user_id=%s, len=%s, model=%s, history_len=%s",
            user_id,
            len(text),
            model_info.get("id", "?"),
            len(assistant.conversation_history),
        )
        logger.debug("Параметры запроса: user_message=%s", text[:200])

        try:
            reply, _thinking = await assistant.send_message(text)
            logger.info(
                "Ответ получен: user_id=%s, reply_len=%s",
                user_id,
                len(reply),
            )
            logger.debug("Ответ API: %s", reply[:200] if reply else "")
            await context_manager.persist_context(user_id)
            return reply
        except Exception as e:
            logger.error(
                "Ошибка API для user_id=%s: %s",
                user_id,
                e,
                exc_info=True,
            )
            raise
