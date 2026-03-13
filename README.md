# Telegram AI Assistant

Telegram-бот для диалога с AI (OpenAI-совместимые модели через ProxyAPI). Контекст
диалога хранится в SQLite и восстанавливается после перезапуска. Поддерживаются
персональные настройки по пользователям: модель, температура, max_tokens, размер
контекстного окна.

## Стек

- **aiogram 3** — асинхронный Telegram Bot API
- **aiohttp** — асинхронные HTTP-запросы к ProxyAPI
- **OpenAI-совместимый API** (ProxyAPI) — запросы к модели
- **SQLite** — хранение контекста и пользовательских настроек
- **python-dotenv** — конфигурация из `.env`

## Установка и запуск

1. Клонируйте репозиторий и перейдите в каталог проекта.

2. Создайте виртуальное окружение и установите зависимости:

   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   # или: venv\Scripts\activate  — Windows
   pip install -r requirements.txt
   ```

3. Скопируйте пример конфигурации и заполните переменные:

   ```bash
   cp .env.example .env
   ```

   В `.env` обязательно задайте:
   - `BOT_TOKEN` — токен бота от [@BotFather](https://t.me/BotFather)
   - `PROXYAPI_KEY` (или `OPENAI_API_KEY` / `GENAPI_KEY`) — ключ API

4. Запуск:

   ```bash
   make run
   ```

   Или без Makefile:

   ```bash
   cd src && python main.py
   ```

## Переменные окружения (.env)

| Переменная           | Описание                          | По умолчанию    |
|----------------------|-----------------------------------|-----------------|
| `BOT_TOKEN`          | Токен Telegram-бота               | — (обязательно) |
| `PROXYAPI_KEY`       | Ключ ProxyAPI / OpenAI            | — (обязательно) |
| `OPENAI_MODEL`       | ID модели (напр. gpt-4o)          | gpt-4o          |
| `TEMPERATURE`        | Температура генерации (0.0–2.0)   | 0.7             |
| `MAX_TOKENS`         | Макс. токенов в ответе            | 2048            |
| `CONTEXT_LEN_MESSAGES` | Размер контекстного окна (сообщ.) | 20              |
| `DB_PATH`            | Путь к SQLite (контекст и настройки) | data/context.db |

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и список команд |
| `/help` | Список доступных команд |
| `/config` | Текущие параметры: модель, температура, max_tokens, размер контекста |
| `/model <название>` | Сменить модель (напр. `/model gpt-4o`) |
| `/temp <число>` | Температура модели 0.0–2.0 (напр. `/temp 0.7`) |
| `/max_tokens <число>` | Макс. токенов в ответе |
| `/context_len <число>` | Размер контекстного окна в сообщениях |
| `/clear` или `/reset` | Очистить контекст диалога |

Любой другой текст отправляется в диалог с AI.

Настройки модели, температуры, max_tokens и context_len сохраняются отдельно для
каждого пользователя и применяются при следующих запросах.

## Структура проекта

```
telebot-ai-assistant/
├── .env.example      # Пример переменных окружения
├── Makefile          # make run — запуск бота
├── README.md
├── requirements.txt
├── data/             # SQLite (создаётся при первом запуске, в .gitignore)
└── src/
    ├── main.py       # Точка входа
    ├── bot.py        # Обработчики команд и сообщений (aiogram)
    ├── config.py     # Чтение настроек из .env
    ├── api_client.py # Асинхронный вызов OpenAI-ассистента
    ├── context_manager.py  # Контекст по пользователям + SQLite
    ├── context_storage.py  # Работа с БД (контекст и user_settings)
    └── ai_assistant/      # Модуль запросов к API
        ├── base.py
        ├── openai_assistant.py
        ├── client.py          # Асинхронный HTTP-клиент (aiohttp)
        └── models.py
```

## Логирование

В лог выводятся ошибки и основные параметры запросов (уровень INFO). Для
подробного лога запросов/ответов API можно включить DEBUG для логгеров
`api_client` и `ai_assistant`.
