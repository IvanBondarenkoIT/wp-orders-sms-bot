"""Entry point: long-polling Telegram bot."""

from __future__ import annotations

import logging
import sys

from telegram.ext import Application, MessageHandler, filters

from .config import get_settings
from .handlers import build_bot_data, handle_order_message

logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is required")
        sys.exit(1)
    if not settings.allowed_chat_ids:
        logger.warning("ALLOWED_CHAT_IDS is empty — bot will ignore all chats")

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )
    app.bot_data.update(build_bot_data(settings))
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP,
            handle_order_message,
        )
    )

    logger.info(
        "Starting wp-orders-sms-bot (dry_run=%s, chats=%s)",
        settings.dry_run,
        settings.allowed_chat_ids,
    )
    app.run_polling(allowed_updates=["message", "channel_post"])


if __name__ == "__main__":
    main()
