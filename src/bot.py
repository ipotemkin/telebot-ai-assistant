"""Telegram-бот: диалог через OpenAIAssistant, контекст в памяти."""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from api_client import send_user_message
from config import (
    get_bot_token,
    get_context_len_messages,
    get_db_path,
    get_max_tokens,
    get_openai_api_key,
    get_openai_model,
    get_temperature,
)
from context_manager import ContextManager

# Логирование: ошибки и параметры запросов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Уровень DEBUG для отправляемых параметров (можно включить в .env)
if logging.getLogger("api_client").level == logging.NOTSET:
    logging.getLogger("api_client").setLevel(logging.INFO)
if logging.getLogger("ai_assistant").level == logging.NOTSET:
    logging.getLogger("ai_assistant").setLevel(logging.INFO)

dp = Dispatcher()
context_manager: ContextManager | None = None

# Текст со списком команд для /start и /help
HELP_TEXT = """Команды бота:

/start — приветствие и список команд
/help — этот список команд
/config — показать параметры конфигурации (модель, температура, токены, контекст)

/model <название> — сменить модель (например: /model gpt-4o)
/temp <число> — температура модели 0.0–2.0 (например: /temp 0.7)
/max_tokens <число> — макс. токенов в ответе (например: /max_tokens 1024)
/context_len <число> — размер контекстного окна в сообщениях (например: /context_len 30)
/clear или /reset — очистить контекст диалога

Любой другой текст — сообщение в диалог с AI."""


async def on_startup() -> None:
    """Инициализация при запуске бота."""
    global context_manager
    api_key = get_openai_api_key()
    db_path = get_db_path()
    context_manager = ContextManager(
        api_key=api_key,
        model_id=get_openai_model(),
        temperature=get_temperature(),
        max_tokens=get_max_tokens(),
        context_len_messages=get_context_len_messages(),
        db_path=db_path,
    )
    model = context_manager.get_model_info()
    logger.info(
        "Бот запущен, модель: %s (%s), контекст: %s сообщений",
        model["name"],
        model["id"],
        get_context_len_messages(),
    )


def _user_id(message: Message) -> int:
    """ID пользователя из сообщения."""
    return message.from_user.id if message.from_user else 0


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Команда /start: приветствие и список команд."""
    uid = _user_id(message)
    logger.info("Команда /start от user_id=%s", uid)
    await message.answer(
        "Привет! Я бот с AI-ассистентом (OpenAI). "
        "Пиши сообщения для диалога.\n\n" + HELP_TEXT
    )


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Команда /help: список доступных команд."""
    logger.info("Команда /help от user_id=%s", _user_id(message))
    await message.answer(HELP_TEXT)


@dp.message(Command("config"))
async def cmd_config(message: Message) -> None:
    """Команда /config: параметры конфигурации (модель, температура, токены, контекст)."""
    if not context_manager:
        await message.answer("Ошибка: бот не инициализирован.")
        return
    uid = _user_id(message)
    info = await context_manager.get_user_model_info(uid)
    text = (
        "Параметры конфигурации:\n\n"
        f"Модель: {info['id']}\n"
        f"Температура: {info['temperature']}\n"
        f"Макс. токенов в ответе: {info['max_tokens']}\n"
        f"Размер контекстного окна: {info['context_len_messages']} сообщ."
    )
    await message.answer(text)


@dp.message(Command("temp"))
async def cmd_temp(message: Message) -> None:
    """Команда /temp <число> — температура модели (0.0–2.0)."""
    if not context_manager:
        await message.answer("Ошибка: бот не инициализирован.")
        return
    uid = _user_id(message)
    args = (message.text or "").strip().split(maxsplit=1)
    if len(args) < 2:
        info = await context_manager.get_user_model_info(uid)
        await message.answer(
            f"Сейчас температура: {info['temperature']}. "
            "Укажите число от 0.0 до 2.0: /temp <число>"
        )
        return
    try:
        t = float(args[1].strip().replace(",", "."))
        if t < 0.0 or t > 2.0:
            await message.answer("Укажите число от 0.0 до 2.0.")
            return
    except ValueError:
        await message.answer("Укажите число: /temp 0.7")
        return
    await context_manager.set_user_setting(uid, "temperature", str(t))
    logger.info("user_id=%s установил temperature: %s", uid, t)
    await message.answer(f"Температура установлена: {t}")


@dp.message(Command("model"))
async def cmd_model(message: Message) -> None:
    """Команда /model <название> — указать модель."""
    if not context_manager:
        await message.answer("Ошибка: бот не инициализирован.")
        return
    uid = _user_id(message)
    args = (message.text or "").strip().split(maxsplit=1)
    if len(args) < 2:
        info = await context_manager.get_user_model_info(uid)
        await message.answer(
            f"Текущая модель: {info['id']}. "
            "Укажите новую: /model <название>, например /model gpt-4o"
        )
        return
    model_id = args[1].strip()
    await context_manager.set_user_setting(uid, "model_id", model_id)
    logger.info("user_id=%s установил модель: %s", uid, model_id)
    await message.answer(f"Модель установлена: {model_id}")


@dp.message(Command("max_tokens"))
async def cmd_max_tokens(message: Message) -> None:
    """Команда /max_tokens <число> — макс. токенов в ответе."""
    if not context_manager:
        await message.answer("Ошибка: бот не инициализирован.")
        return
    uid = _user_id(message)
    args = (message.text or "").strip().split(maxsplit=1)
    if len(args) < 2:
        info = await context_manager.get_user_model_info(uid)
        await message.answer(
            f"Сейчас max_tokens: {info['max_tokens']}. "
            "Укажите число: /max_tokens <число>"
        )
        return
    try:
        n = int(args[1].strip())
        if n < 1 or n > 128000:
            await message.answer("Укажите число от 1 до 128000.")
            return
    except ValueError:
        await message.answer("Укажите целое число: /max_tokens 2048")
        return
    await context_manager.set_user_setting(uid, "max_tokens", str(n))
    logger.info("user_id=%s установил max_tokens: %s", uid, n)
    await message.answer(f"max_tokens установлено: {n}")


@dp.message(Command("context_len"))
async def cmd_context_len(message: Message) -> None:
    """Команда /context_len <число> — размер контекстного окна."""
    if not context_manager:
        await message.answer("Ошибка: бот не инициализирован.")
        return
    uid = _user_id(message)
    args = (message.text or "").strip().split(maxsplit=1)
    if len(args) < 2:
        info = await context_manager.get_user_model_info(uid)
        await message.answer(
            f"Сейчас контекст: {info['context_len_messages']} сообщений. "
            "Укажите число: /context_len <число>"
        )
        return
    try:
        n = int(args[1].strip())
        if n < 2 or n > 500:
            await message.answer("Укажите число от 2 до 500.")
            return
    except ValueError:
        await message.answer("Укажите целое число: /context_len 20")
        return
    await context_manager.set_user_setting(
        uid, "context_len_messages", str(n)
    )
    logger.info("user_id=%s установил context_len: %s", uid, n)
    await message.answer(f"Размер контекста установлен: {n} сообщений.")


@dp.message(Command("clear"))
@dp.message(Command("reset"))
async def cmd_clear_context(message: Message) -> None:
    """Команды /clear и /reset: очистить контекст диалога."""
    if not context_manager:
        await message.answer("Ошибка: бот не инициализирован.")
        return
    uid = _user_id(message)
    await context_manager.clear_context(uid)
    logger.info("Контекст сброшен для user_id=%s", uid)
    await message.answer("Контекст очищен. Можем начать диалог заново.")


@dp.message()
async def handle_message(message: Message) -> None:
    """Обычный диалог: текст пользователя отправляется в API, ответ — в чат."""
    if not context_manager:
        logger.error("context_manager не инициализирован")
        await message.answer("Внутренняя ошибка. Попробуйте позже.")
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer("Отправьте текстовое сообщение.")
        return

    user_id = message.from_user.id if message.from_user else 0
    logger.info("Входящее сообщение: user_id=%s, len=%s", user_id, len(text))
    logger.debug("Параметры (текст): %s", text[:300])

    sent = await message.answer("Думаю…")
    try:
        reply = await send_user_message(
            context_manager, user_id, text
        )
        # Telegram лимит ~4096 символов на сообщение
        if len(reply) > 4000:
            reply = reply[:3997] + "..."
        await sent.edit_text(reply)
    except Exception as e:
        logger.error("Ошибка при обработке сообщения: %s", e, exc_info=True)
        await sent.edit_text(
            f"Произошла ошибка при запросе к API: {e!s}. "
            "Попробуйте ещё раз или /reset."
        )


async def main() -> None:
    """Точка входа: запуск polling."""
    await on_startup()
    token = get_bot_token()
    bot = Bot(token=token)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
