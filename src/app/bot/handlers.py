"""Telegram bot command and query handlers."""

from typing import cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.bot.formatters import format_prices
from app.config.container import Container
from app.utils.result import Ok


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    welcome_text = (
        "👋 <b>به ربات بازارهای مالی خوش آمدید!</b>\n\n"
        "من می‌توانم قیمت لحظه‌ای رمزارزها، ارزهای فیات، فلزات گران‌بها و بورس را به شما نشان دهم.\n\n"
        "/market - مشاهده قیمت‌های بازار\n"
        "/price &lt;نماد&gt; - دریافت قیمت یک دارایی خاص\n"
        "/watchlist - مشاهده واچ‌لیست شخصی شما\n"
    )
    if update.message:
        await update.message.reply_html(welcome_text)


async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the market menu with an inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🪙 رمزارزها", callback_data="market_crypto"),
            InlineKeyboardButton("💵 ارزهای فیات", callback_data="market_fiat"),
        ],
        [
            InlineKeyboardButton("🥇 فلزات", callback_data="market_metal"),
            InlineKeyboardButton("📈 بورس", callback_data="market_bourse"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "📊 <b>یک بازار را برای مشاهده قیمت‌ها انتخاب کنید:</b>"
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
            "⚠️ دریافت اطلاعات بازار با خطا مواجه شد. لطفاً دوباره تلاش کنید."
        )
        return

    all_prices = res.value
    parts = query.data.split("_")
    category = parts[1]  # e.g. "crypto"

    # Filter by category and limit to prevent Message_too_long errors
    filtered = [p for p in all_prices if p.type.value == category]

    # Telegram max message length is 4096 chars. 30 items is safe.
    if len(filtered) > 30:
        filtered = filtered[:30]

    titles = {
        "crypto": "🪙 قیمت رمزارزها",
        "fiat": "💵 نرخ ارزهای فیات",
        "metal": "🥇 فلزات گران‌بها",
        "bourse": "📈 بورس و شاخص‌های جهانی",
    }

    msg = format_prices(filtered, titles.get(category, "قیمت‌های بازار"))

    keyboard = [
        [
            InlineKeyboardButton("🪙 رمزارزها", callback_data="market_crypto"),
            InlineKeyboardButton("💵 ارزهای فیات", callback_data="market_fiat"),
        ],
        [
            InlineKeyboardButton("🥇 فلزات", callback_data="market_metal"),
            InlineKeyboardButton("📈 بورس", callback_data="market_bourse"),
        ],
        [
            InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"refresh_{category}"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # If it's a refresh, we might get a MessageNotModified error if data hasn't changed.
    # We can append a timestamp or just catch the exception.
    from telegram.error import BadRequest

    try:
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise



async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get the price of a specific symbol."""
    if not context.args:
        if update.message:
            await update.message.reply_text(
                "لطفاً یک نماد وارد کنید. مثال: /price BTC"
            )
        return

    symbol = context.args[0].upper()

    container = cast(Container, context.bot_data.get("container"))
    crypto_service = container.crypto_service
    repo = container.repository

    res = await crypto_service.get_prices()
    if not isinstance(res, Ok):
        if update.message:
            await update.message.reply_text("⚠️ دریافت اطلاعات بازار با خطا مواجه شد.")
        return

    price = next((p for p in res.value if p.symbol.upper() == symbol), None)

    if not price:
        if update.message:
            await update.message.reply_text(f"❌ نماد {symbol} یافت نشد.")
        return

    user = update.message.from_user if update.message else None
    watchlist = []
    if user:
        await repo.get_or_create_user(user.id, user.username, user.first_name)
        watchlist = await repo.get_watchlist(user.id)

    msg = format_prices([price], f"قیمت {symbol}")

    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"price_{symbol}")],
    ]
    if symbol in watchlist:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "❌ حذف از واچ‌لیست", callback_data=f"watch_remove_{symbol}"
                )
            ]
        )
    else:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "⭐ افزودن به واچ‌لیست", callback_data=f"watch_add_{symbol}"
                )
            ]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_html(msg, reply_markup=reply_markup)


async def price_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle refresh button clicks for specific prices."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    symbol = query.data.split("_")[1]

    container = cast(Container, context.bot_data.get("container"))
    crypto_service = container.crypto_service
    repo = container.repository

    res = await crypto_service.get_prices()
    if not isinstance(res, Ok):
        await query.edit_message_text("⚠️ دریافت اطلاعات بازار با خطا مواجه شد.")
        return

    price = next((p for p in res.value if p.symbol.upper() == symbol), None)
    if not price:
        await query.edit_message_text(f"❌ نماد {symbol} دیگر یافت نشد.")
        return

    user = query.from_user
    await repo.get_or_create_user(user.id, user.username, user.first_name)
    watchlist = await repo.get_watchlist(user.id)

    msg = format_prices([price], f"قیمت {symbol}")

    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"price_{symbol}")],
    ]
    if symbol in watchlist:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "❌ حذف از واچ‌لیست", callback_data=f"watch_remove_{symbol}"
                )
            ]
        )
    else:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "⭐ افزودن به واچ‌لیست", callback_data=f"watch_add_{symbol}"
                )
            ]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)

    from telegram.error import BadRequest

    try:
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View user's watchlist."""
    user = update.message.from_user if update.message else None
    if not user:
        return

    container = cast(Container, context.bot_data.get("container"))
    crypto_service = container.crypto_service
    repo = container.repository

    await repo.get_or_create_user(user.id, user.username, user.first_name)
    watchlist = await repo.get_watchlist(user.id)

    if not watchlist:
        if update.message:
            await update.message.reply_text(
                "⭐ واچ‌لیست شما خالی است!\n"
                "از دستور /market یا /price برای یافتن دارایی‌ها و افزودن آنها استفاده کنید."
            )
        return

    res = await crypto_service.get_prices()
    if not isinstance(res, Ok):
        if update.message:
            await update.message.reply_text("⚠️ دریافت اطلاعات بازار با خطا مواجه شد.")
        return

    prices = [p for p in res.value if p.symbol.upper() in watchlist]
    msg = format_prices(prices, "⭐ واچ‌لیست من")

    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی واچ‌لیست", callback_data="watch_refresh")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_html(msg, reply_markup=reply_markup)


async def watch_add_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Add a symbol to watchlist."""
    query = update.callback_query
    if not query or not query.data:
        return

    symbol = query.data.split("_")[2]
    user = query.from_user

    container = cast(Container, context.bot_data.get("container"))
    repo = container.repository

    await repo.get_or_create_user(user.id, user.username, user.first_name)
    await repo.add_to_watchlist(user.id, symbol)

    await query.answer(f"⭐ {symbol} به واچ‌لیست اضافه شد!")

    # Update the keyboard to show 'Remove'
    query.data = f"price_{symbol}"
    await price_callback(update, context)


async def watch_remove_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Remove a symbol from watchlist."""
    query = update.callback_query
    if not query or not query.data:
        return

    symbol = query.data.split("_")[2]
    user = query.from_user

    container = cast(Container, context.bot_data.get("container"))
    repo = container.repository

    await repo.get_or_create_user(user.id, user.username, user.first_name)
    await repo.remove_from_watchlist(user.id, symbol)

    await query.answer(f"❌ {symbol} از واچ‌لیست حذف شد.")

    query.data = f"price_{symbol}"
    await price_callback(update, context)


async def watch_refresh_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Refresh the watchlist message."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    user = query.from_user
    container = cast(Container, context.bot_data.get("container"))
    repo = container.repository
    crypto_service = container.crypto_service

    watchlist = await repo.get_watchlist(user.id)
    if not watchlist:
        await query.edit_message_text("⭐ واچ‌لیست شما خالی است!")
        return

    res = await crypto_service.get_prices()
    if not isinstance(res, Ok):
        await query.edit_message_text("⚠️ دریافت اطلاعات بازار با خطا مواجه شد.")
        return

    prices = [p for p in res.value if p.symbol.upper() in watchlist]
    msg = format_prices(prices, "⭐ واچ‌لیست من")

    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی واچ‌لیست", callback_data="watch_refresh")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    from telegram.error import BadRequest

    try:
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise
