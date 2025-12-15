"""
Главный файл запуска телеграм бота
"""
import os
import sys
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настраиваем логгер ДО всех импортов
from logger_config import setup_logger

setup_logger()

from bot_handlers import (
    BOT_NAME, DEVELOPER_ID,
    start_command, handle_text, help_command,
    menu_command, myid_command, error_handler
)

import logging
from telegram import Update  # Добавлен импорт Update

logger = logging.getLogger(__name__)


def main():
    """Основная функция запуска бота"""
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN не найден в переменных окружения!")
        sys.exit(1)

    # Создаем приложение
    app = Application.builder().token(token).build()

    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("myid", myid_command))

    # Обработчик текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Обработчик ошибок
    app.add_error_handler(error_handler)

    logger.info("🤖 Бот запущен и готов к работе!")

    # Запуск бота
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()