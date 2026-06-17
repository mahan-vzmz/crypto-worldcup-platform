"""Inline query handlers."""

import asyncio
from typing import cast
from uuid import uuid4

from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import ContextTypes

from app.bot.formatters import format_prices
from app.config.container import Container
from app.utils.result import Ok


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline queries (e.g. @botname btc)."""
    query = update.inline_query
    if not query:
        return

    text = query.query.strip().upper()

    container = cast(Container, context.bot_data.get("container"))
    crypto_service = container.crypto_service

    res = await asyncio.to_thread(crypto_service.get_prices)
    if not isinstance(res, Ok):
        return

    all_prices = res.value
    results = []

    # If text is empty, show some popular items
    if not text:
        display_prices = [
            p for p in all_prices if p.symbol in ("BTC", "ETH", "USDT", "XAU", "EUR")
        ]
        if not display_prices:
            display_prices = all_prices[:5]
    else:
        # Match symbol or name
        display_prices = [
            p for p in all_prices
            if text in p.symbol.upper() or text in p.name.upper()
        ]

    for p in display_prices:
        msg = format_prices([p], f"{p.symbol} Price")
        # Format preview description safely
        desc_usd = f"${p.price_usd:,.4f}" if p.price_usd < 1 else f"${p.price_usd:,.2f}"
        
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"{p.symbol} - {p.name}",
                description=f"{desc_usd} | {p.price_toman:,.0f} T",
                input_message_content=InputTextMessageContent(
                    msg, parse_mode="HTML"
                ),
            )
        )

    await query.answer(results[:10], cache_time=30)
