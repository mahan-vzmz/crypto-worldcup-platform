"""Tests for the bot's pure search helpers (no Telegram, no network)."""

from datetime import UTC, datetime
from decimal import Decimal

from app.bot.search import clean_query, match_prices, popular_prices
from app.models.crypto import AssetType, CryptoPrice


def _price(
    symbol: str, name: str, asset_type: AssetType = AssetType.CRYPTO
) -> CryptoPrice:
    return CryptoPrice(
        symbol=symbol,
        name=name,
        price_usd=Decimal("1.0"),
        price_toman=Decimal("60000"),
        change_24h=Decimal("0"),
        type=asset_type,
        last_updated=datetime.now(UTC),
    )


PRICES = [
    _price("BTC", "Bitcoin"),
    _price("ETH", "Ethereum"),
    _price("USDT", "Tether", AssetType.FIAT),
    _price("SOL", "Solana"),
    _price("XAUT", "Tether Gold", AssetType.METAL),
    _price("EUR", "Euro", AssetType.FIAT),
    _price("DOGE", "Dogecoin"),
]


class TestCleanQuery:
    def test_strips_filler_and_punctuation(self) -> None:
        assert clean_query("قیمت btc چنده؟") == "btc"

    def test_strips_bot_mention(self) -> None:
        assert clean_query("@MarketPulseBot eth", "MarketPulseBot") == "eth"

    def test_empty_when_only_filler(self) -> None:
        assert clean_query("قیمت چنده") == ""

    def test_ignores_slash_tokens(self) -> None:
        assert clean_query("/price sol") == "sol"


class TestMatchPrices:
    def test_matches_by_symbol(self) -> None:
        result = match_prices(PRICES, "btc")
        assert [p.symbol for p in result] == ["BTC"]

    def test_matches_by_name_substring(self) -> None:
        result = match_prices(PRICES, "ethereum")
        assert [p.symbol for p in result] == ["ETH"]

    def test_matches_persian_alias(self) -> None:
        result = match_prices(PRICES, "بیتکوین")
        assert "BTC" in [p.symbol for p in result]

    def test_alias_within_sentence(self) -> None:
        cleaned = clean_query("قیمت تتر")
        result = match_prices(PRICES, cleaned)
        assert "USDT" in [p.symbol for p in result]

    def test_empty_query_returns_popular(self) -> None:
        result = match_prices(PRICES, "")
        symbols = {p.symbol for p in result}
        assert {"BTC", "ETH", "USDT"} <= symbols

    def test_no_match_returns_empty(self) -> None:
        assert match_prices(PRICES, "NOTACOIN") == []

    def test_limit_is_respected(self) -> None:
        # "T" appears in several symbols/names (BTC, USDT, ETH, Tether...)
        result = match_prices(PRICES, "t", limit=2)
        assert len(result) == 2


class TestPopularPrices:
    def test_returns_known_popular_subset(self) -> None:
        result = popular_prices(PRICES)
        assert {"BTC", "ETH", "USDT"} <= {p.symbol for p in result}

    def test_falls_back_to_first_n_when_no_popular(self) -> None:
        niche = [_price("AAA", "Alpha"), _price("BBB", "Beta")]
        result = popular_prices(niche, limit=1)
        assert len(result) == 1
