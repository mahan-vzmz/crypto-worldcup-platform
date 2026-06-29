"""Entry point for the Telegram bot."""

import datetime
import logging

from telegram import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from app.bot.handlers import (
    help_command,
    market_callback,
    market_command,
    on_added_to_chat,
    price_callback,
    price_command,
    start_command,
    text_query_handler,
    watch_add_callback,
    watch_refresh_callback,
    watch_remove_callback,
    watchlist_command,
)
from app.bot.inline import inline_query
from app.bot.jobs import morning_brief
from app.config.container import Container

logger = logging.getLogger(__name__)

#: Commands advertised in Telegram's UI menu (private chats and groups).
_BOT_COMMANDS = [
    BotCommand("market", "نمای کلی بازار"),
    BotCommand("price", "قیمت یک نماد (مثال: /price btc)"),
    BotCommand("watchlist", "واچ‌لیست شخصی شما"),
    BotCommand("help", "راهنمای استفاده"),
]


async def _post_init(application: Application) -> None:  # type: ignore[type-arg]
    """Register the slash-command menu once the bot is initialized."""
    await application.bot.set_my_commands(
        _BOT_COMMANDS, scope=BotCommandScopeAllPrivateChats()
    )
    await application.bot.set_my_commands(
        _BOT_COMMANDS, scope=BotCommandScopeAllGroupChats()
    )
    logger.info("Bot command menu registered.")


def run_bot(container: Container) -> None:
    """Run the Telegram bot polling loop."""
    settings = container.settings
    token = settings.telegram_bot_token

    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Bot cannot start.")
        return

    logger.info("Starting Telegram bot...")

    application = ApplicationBuilder().token(token).post_init(_post_init).build()

    # Inject the container so handlers can use the services
    application.bot_data["container"] = container

    # Command Handlers (work in private chats and groups alike)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("market", market_command))

    # /price and the short /p alias
    application.add_handler(CommandHandler(["price", "p"], price_command))
    application.add_handler(CommandHandler("watchlist", watchlist_command))

    # Callback Query Handlers (for Inline Keyboards)
    application.add_handler(
        CallbackQueryHandler(market_callback, pattern="^(market|refresh)_")
    )
    application.add_handler(CallbackQueryHandler(price_callback, pattern="^price_"))
    application.add_handler(
        CallbackQueryHandler(watch_add_callback, pattern="^watch_add_")
    )
    application.add_handler(
        CallbackQueryHandler(watch_remove_callback, pattern="^watch_remove_")
    )
    application.add_handler(
        CallbackQueryHandler(watch_refresh_callback, pattern="^watch_refresh$")
    )

    # Inline Query Handler
    application.add_handler(InlineQueryHandler(inline_query))

    # Greet groups when the bot is added to them
    application.add_handler(
        ChatMemberHandler(on_added_to_chat, ChatMemberHandler.MY_CHAT_MEMBER)
    )

    # Free-text price queries (mention/reply in groups, any text in private).
    # Registered last so explicit commands take precedence.
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_query_handler)
    )

    # Start Polling
    if application.job_queue:
        time_8am = datetime.time(hour=8, minute=0, tzinfo=datetime.UTC)
        application.job_queue.run_daily(morning_brief, time=time_8am)
        logger.info("Morning brief scheduled for 08:00 UTC daily.")

    logger.info("Bot is polling for updates...")
    application.run_polling()
