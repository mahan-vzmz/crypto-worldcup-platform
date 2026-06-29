"""Inline query handlers."""

from typing import cast
from uuid import uuid4

from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import ContextTypes

from app.bot.formatters import format_prices
from app.bot.search import clean_query, match_prices
from app.config.container import Container
from app.utils.result import Ok


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline queries (e.g. ``@botname btc``) from any chat."""
    query = update.inline_query
    if not query:
        return

    container = cast(Container, context.bot_data.get("container"))
    crypto_service = container.crypto_service

    res = await crypto_service.get_prices()
    if not isinstance(res, Ok):
        await query.answer(
            [
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title="⚠️ بازار در دسترس نیست",
                    description="لطفاً چند لحظه بعد دوباره تلاش کنید",
                    input_message_content=InputTextMessageContent(
                        "دریافت اطلاعات بازار موقتاً ممکن نیست."
                    ),
                )
            ],
            cache_time=5,
        )
        return

    cleaned = clean_query(query.query)
    display_prices = match_prices(res.value, cleaned, limit=15)

    results = []
    for p in display_prices:
        msg = format_prices([p], f"{p.symbol} Price")
        desc_usd = f"${p.price_usd:,.4f}" if p.price_usd < 1 else f"${p.price_usd:,.2f}"

        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"{p.symbol} - {p.name}",
                description=f"{desc_usd} | {p.price_toman:,.0f} تومان",
                input_message_content=InputTextMessageContent(msg, parse_mode="HTML"),
                thumbnail_url=p.image_url or None,
            )
        )

    if not results:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="نتیجه‌ای یافت نشد",
                description="یک نماد دیگر امتحان کنید، مثل BTC یا ETH",
                input_message_content=InputTextMessageContent(
                    "نمادی برای این جستجو پیدا نشد. مثال: BTC، ETH، USDT"
                ),
            )
        )

    await query.answer(results[:25], cache_time=30)
