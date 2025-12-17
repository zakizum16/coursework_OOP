import os
import sys
from dotenv import load_dotenv

load_dotenv()

from logger_config import setup_logger

setup_logger()

# импорты обработчиков
from bot_handlers import (
    BOT_NAME, DEVELOPER_ID,
    start_command, handle_text, help_command,
    menu_command, myid_command, error_handler
)

import logging
from telegram import Update

logger = logging.getLogger(__name__)


def main():
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN не найден в переменных окружения!")
        sys.exit(1)

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("myid", myid_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.add_error_handler(error_handler)

    logger.info("🤖 Бот запущен и готов к работе!")

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()