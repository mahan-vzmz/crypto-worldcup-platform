"""Scheduled jobs for the Telegram bot."""

import logging
from typing import cast

from telegram.ext import ContextTypes

from app.bot.formatters import format_prices
from app.config.container import Container
from app.utils.result import Ok

logger = logging.getLogger(__name__)


async def morning_brief(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a daily morning brief to the configured broadcast chat."""
    container = cast(Container, context.bot_data.get("container"))
    settings = container.settings
    chat_id = settings.telegram_broadcast_chat_id

    if not chat_id:
        logger.warning(
            "Morning brief job ran, but TELEGRAM_BROADCAST_CHAT_ID is not set."
        )
        return

    logger.info("Sending morning brief to %s", chat_id)

    # 1. Fetch Market Overview
    crypto_service = container.crypto_service
    res_crypto = await crypto_service.get_prices()

    market_msg = "<b>🌞 Good Morning! Here is your daily update.</b>\n\n"
    if isinstance(res_crypto, Ok):
        # Top assets
        top = [p for p in res_crypto.value if p.symbol in ("BTC", "ETH", "XAU", "EUR")]
        if top:
            market_msg += format_prices(top, "Top Market Movers")
    else:
        market_msg += "⚠️ Market data unavailable.\n"

    market_msg += "\n"

    try:
        await context.bot.send_message(
            chat_id=chat_id, text=market_msg, parse_mode="HTML"
        )
    except Exception as e:
        logger.error("Failed to send morning brief: %s", e)
