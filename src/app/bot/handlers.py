"""Telegram bot command and query handlers."""

from typing import cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.bot.formatters import format_prices
from app.bot.search import clean_query, match_prices
from app.config.container import Container
from app.utils.result import Ok

#: Shown when the bot is added to a group, or on /help inside a group.
GROUP_HELP_TEXT = (
    "👋 <b>ربات مارکت پالس</b> به جمع شما اضافه شد!\n\n"
    "در گروه می‌توانید از این روش‌ها قیمت بگیرید:\n"
    "• دستور <code>/price btc</code> یا مخفف <code>/p eth</code>\n"
    "• من را منشن کنید: <code>@{username} بیتکوین</code>\n"
    "• به پیام من ریپلای کنید و نماد را بنویسید\n"
    "• <code>/market</code> برای نمای کلی بازار\n\n"
    "<i>برای کار روان‌تر در گروه، Privacy Mode ربات را در BotFather خاموش "
    "نگه دارید تا به متن آزاد هم پاسخ دهم.</i>"
)


def _build_watch_keyboard(symbol: str, in_watchlist: bool) -> InlineKeyboardMarkup:
    """Build the refresh + watchlist toggle keyboard for a single asset."""
    keyboard = [[InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"price_{symbol}")]]
    if in_watchlist:
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
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    welcome_text = (
        "👋 <b>به ربات بازارهای مالی خوش آمدید!</b>\n\n"
        "من می‌توانم قیمت لحظه‌ای رمزارزها، ارزهای فیات، فلزات گران‌بها "
        "و بورس را به شما نشان دهم.\n\n"
        "/market - مشاهده قیمت‌های بازار\n"
        "/price &lt;نماد&gt; - دریافت قیمت یک دارایی خاص\n"
        "/watchlist - مشاهده واچ‌لیست شخصی شما\n\n"
        "💡 می‌توانید مرا به گروه خود اضافه کنید و با منشن یا "
        "دستور <code>/price</code> قیمت بگیرید."
    )
    if update.message:
        await update.message.reply_html(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show context-aware help (group vs. private)."""
    msg = update.message
    if not msg:
        return
    if msg.chat.type in ("group", "supergroup"):
        username = context.bot.username or "MarketPulseBot"
        await msg.reply_html(GROUP_HELP_TEXT.format(username=username))
    else:
        await start_command(update, context)


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
            await update.message.reply_text("لطفاً یک نماد وارد کنید. مثال: /price BTC")
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
    reply_markup = _build_watch_keyboard(symbol, symbol in watchlist)

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
                "از دستور /market یا /price برای یافتن دارایی‌ها "
                "و افزودن آنها استفاده کنید."
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


def _bot_is_addressed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """In a group, decide whether a plain text message is meant for the bot.

    True when the bot is @mentioned or the message replies to one of the bot's
    own messages. In private chats every message is for the bot.
    """
    msg = update.message
    if not msg:
        return False
    if msg.chat.type not in ("group", "supergroup"):
        return True

    username = (context.bot.username or "").lower()
    text = (msg.text or "").lower()
    mentioned = bool(username) and f"@{username}" in text

    replied_to_bot = bool(
        msg.reply_to_message
        and msg.reply_to_message.from_user
        and msg.reply_to_message.from_user.id == context.bot.id
    )
    return mentioned or replied_to_bot


async def text_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Answer free-text price queries via mention, reply, or private message.

    Examples: ``@MarketPulseBot بیتکوین``, a reply with ``eth``, or ``btc`` in
    a private chat. Stays silent on unrelated group chatter.
    """
    msg = update.message
    if not msg or not msg.text:
        return
    if not _bot_is_addressed(update, context):
        return

    is_group = msg.chat.type in ("group", "supergroup")
    query_text = clean_query(msg.text, context.bot.username)

    container = cast(Container, context.bot_data.get("container"))
    res = await container.crypto_service.get_prices()
    if not isinstance(res, Ok):
        await msg.reply_text("⚠️ دریافت اطلاعات بازار با خطا مواجه شد.")
        return

    matches = match_prices(res.value, query_text, limit=5)
    if not matches:
        # Avoid noise in groups; gently guide users in private chats.
        if not is_group:
            await msg.reply_text(
                "نمادی پیدا نشد. مثال: <code>btc</code> یا «قیمت اتریوم».",
                parse_mode="HTML",
            )
        return

    if len(matches) == 1:
        price = matches[0]
        text = format_prices([price], f"قیمت {price.symbol}")
        await msg.reply_html(
            text, reply_markup=_build_watch_keyboard(price.symbol, False)
        )
    else:
        await msg.reply_html(format_prices(matches, "نتایج جستجو"))


async def on_added_to_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Greet a group with usage instructions when the bot joins it."""
    member_update = update.my_chat_member
    if not member_update:
        return

    new_status = member_update.new_chat_member.status
    if member_update.new_chat_member.user.id != context.bot.id:
        return
    if new_status not in ("member", "administrator"):
        return

    username = context.bot.username or "MarketPulseBot"
    await context.bot.send_message(
        chat_id=member_update.chat.id,
        text=GROUP_HELP_TEXT.format(username=username),
        parse_mode="HTML",
    )
