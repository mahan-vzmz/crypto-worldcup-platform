"""Entry point for the Telegram bot."""

import logging
import datetime

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    InlineQueryHandler,
)

from app.bot.handlers import (
    football_command,
    market_callback,
    market_command,
    price_command,
    start_command,
)
from app.bot.inline import inline_query
from app.bot.jobs import morning_brief
from app.config.container import Container

logger = logging.getLogger(__name__)


def run_bot(container: Container) -> None:
    """Run the Telegram bot polling loop."""
    settings = container.settings
    token = settings.telegram_bot_token

    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Bot cannot start.")
        return

    logger.info("Starting Telegram bot...")

    application = ApplicationBuilder().token(token).build()

    # Inject the container so handlers can use the services
    application.bot_data["container"] = container

    # Command Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", start_command))
    application.add_handler(CommandHandler("market", market_command))
    application.add_handler(CommandHandler("football", football_command))
    application.add_handler(CommandHandler("price", price_command))

    # Callback Query Handlers (for Inline Keyboards)
    application.add_handler(CallbackQueryHandler(market_callback, pattern="^market_"))

    # Inline Query Handler
    application.add_handler(InlineQueryHandler(inline_query))

    # Start Polling
    if application.job_queue:
        time_8am = datetime.time(hour=8, minute=0, tzinfo=datetime.timezone.utc)
        application.job_queue.run_daily(morning_brief, time=time_8am)
        logger.info("Morning brief scheduled for 08:00 UTC daily.")

    logger.info("Bot is polling for updates...")
    application.run_polling()
