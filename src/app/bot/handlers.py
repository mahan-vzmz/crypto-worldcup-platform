"""Telegram bot command and query handlers."""

import asyncio
from typing import cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.bot.formatters import format_prices, format_tournament
from app.config.container import Container
from app.utils.result import Ok


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    welcome_text = (
        "👋 <b>Welcome to the Market & Football Bot!</b>\n\n"
        "I can provide live prices for Cryptocurrencies, Fiat, and Precious Metals, "
        "as well as live football scores.\n\n"
        "<b>Available Commands:</b>\n"
        "/market - View live market prices\n"
        "/football - View today's football matches\n"
        "/price &lt;symbol&gt; - Get the price of a specific asset (e.g. /price BTC)\n"
    )
    if update.message:
        await update.message.reply_html(welcome_text)


async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the market menu with an inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🪙 Crypto", callback_data="market_crypto"),
            InlineKeyboardButton("💵 Fiat", callback_data="market_fiat"),
        ],
        [
            InlineKeyboardButton("🥇 Metals", callback_data="market_metal"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "📊 <b>Select a market to view live prices:</b>"
    if update.message:
        await update.message.reply_html(text, reply_markup=reply_markup)


async def market_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle market category button clicks."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    container = cast(Container, context.bot_data.get("container"))
    crypto_service = container.crypto_service

    # Run asynchronous fetch
    res = await crypto_service.get_prices()

    if not isinstance(res, Ok):
        await query.edit_message_text(
            "⚠️ Failed to fetch market data. Please try again."
        )
        return

    all_prices = res.value
    category = query.data.split("_")[1]  # e.g. "crypto"

    # Filter by category and limit to prevent Message_too_long errors
    filtered = [p for p in all_prices if p.type.value == category]

    # Telegram max message length is 4096 chars. 30 items is safe.
    if len(filtered) > 30:
        filtered = filtered[:30]

    titles = {
        "crypto": "Cryptocurrency Prices",
        "fiat": "Fiat Exchange Rates",
        "metal": "Precious Metals",
    }

    msg = format_prices(filtered, titles.get(category, "Market Prices"))

    # Persist the keyboard so they can switch easily
    keyboard = [
        [
            InlineKeyboardButton("🪙 Crypto", callback_data="market_crypto"),
            InlineKeyboardButton("💵 Fiat", callback_data="market_fiat"),
        ],
        [
            InlineKeyboardButton("🥇 Metals", callback_data="market_metal"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)


async def football_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show football matches."""
    container = cast(Container, context.bot_data.get("container"))
    football_service = container.football_service

    # Optional: check if they passed a competition code, e.g. /football PL
    code = "WC"
    if context.args:
        code = context.args[0].upper()

    res = await football_service.get_tournament(code)

    if not isinstance(res, Ok):
        msg = f"⚠️ Failed to fetch football data for {code}."
    else:
        msg = format_tournament(res.value)

    if update.message:
        await update.message.reply_html(msg)


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get the price of a specific symbol."""
    if not context.args:
        if update.message:
            await update.message.reply_text(
                "Please provide a symbol. Example: /price BTC"
            )
        return

    symbol = context.args[0].upper()

    container = cast(Container, context.bot_data.get("container"))
    crypto_service = container.crypto_service

    res = await crypto_service.get_prices()
    if not isinstance(res, Ok):
        if update.message:
            await update.message.reply_text("⚠️ Failed to fetch market data.")
        return

    price = next((p for p in res.value if p.symbol.upper() == symbol), None)

    if not price:
        if update.message:
            await update.message.reply_text(f"❌ Symbol {symbol} not found.")
        return

    msg = format_prices([price], f"{symbol} Price")
    if update.message:
        await update.message.reply_html(msg)
