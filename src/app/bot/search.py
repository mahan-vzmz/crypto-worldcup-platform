"""Shared, pure search helpers for the Telegram bot.

Both the inline query handler and the in-chat text/mention handler need to turn
a free-form user query ("btc", "قیمت بیتکوین", "@MarketPulseBot eth") into a
list of matching assets. Keeping this logic here — free of any Telegram or
network types — makes it trivially unit-testable.
"""

import re
from collections.abc import Sequence

from app.models.crypto import CryptoPrice

#: Popular assets shown when the user gives no query.
POPULAR_SYMBOLS: tuple[str, ...] = ("BTC", "ETH", "USDT", "SOL", "XAUT", "EUR")

#: Common Persian/colloquial names mapped to their canonical symbol.
ALIASES: dict[str, str] = {
    "بیتکوین": "BTC",
    "بیت‌کوین": "BTC",
    "بیت کوین": "BTC",
    "اتریوم": "ETH",
    "اتر": "ETH",
    "تتر": "USDT",
    "دلار": "USDT",
    "یورو": "EUR",
    "پوند": "GBP",
    "طلا": "XAUT",
    "سولانا": "SOL",
    "ریپل": "XRP",
    "دوج": "DOGE",
}

#: Filler words stripped from a query so "قیمت btc چنده" reduces to "btc".
_FILLER_WORDS: frozenset[str] = frozenset(
    {
        "قیمت",
        "نرخ",
        "چنده",
        "چقدره",
        "چقدر",
        "چند",
        "لطفا",
        "لطفاً",
        "بات",
        "ربات",
        "price",
        "rate",
        "of",
        "the",
    }
)


def clean_query(text: str, bot_username: str | None = None) -> str:
    """Strip a bot @mention, filler words and punctuation from raw *text*.

    Returns the residual query (possibly empty) ready for :func:`match_prices`.
    """
    cleaned = text
    if bot_username:
        cleaned = re.sub(rf"@{re.escape(bot_username)}", " ", cleaned, flags=re.I)

    # Drop punctuation that users sprinkle around the query.
    cleaned = re.sub(r"[?؟،.,!:]+", " ", cleaned)

    tokens = [
        tok
        for tok in cleaned.split()
        if tok and not tok.startswith("/") and tok.lower() not in _FILLER_WORDS
    ]
    return " ".join(tokens).strip()


def popular_prices(
    prices: Sequence[CryptoPrice], *, limit: int = 6
) -> list[CryptoPrice]:
    """Return a short list of popular assets for an empty query."""
    chosen = [p for p in prices if p.symbol.upper() in POPULAR_SYMBOLS]
    if not chosen:
        chosen = list(prices[:limit])
    return chosen[:limit]


def match_prices(
    prices: Sequence[CryptoPrice], query: str, *, limit: int = 10
) -> list[CryptoPrice]:
    """Find assets matching *query* by symbol, name, or a known alias.

    An empty query yields the popular set. Matching is case-insensitive and
    substring-based, mirroring what users expect from a quick lookup.
    """
    cleaned = query.strip()
    if not cleaned:
        return popular_prices(prices, limit=limit)

    needle = cleaned.upper()

    # Build the set of target symbols/terms: the raw query plus any aliases
    # whose Persian key appears in the original text.
    targets: set[str] = {needle}
    for alias, symbol in ALIASES.items():
        if alias in cleaned:
            targets.add(symbol)

    matches: list[CryptoPrice] = []
    for p in prices:
        symbol_u = p.symbol.upper()
        name_u = p.name.upper()
        if any(t == symbol_u or t in symbol_u or t in name_u for t in targets):
            matches.append(p)

    return matches[:limit]
