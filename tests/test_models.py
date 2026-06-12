"""Tests for the domain models: invariants, happy paths, immutability.

These tests need no mocks, filesystem, or network -- models are the
innermost layer and depend only on the standard library.
"""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime

import pytest

from app.models.crypto import Coin, CryptoPrice
from app.models.football import Match, MatchStatus, Team, Tournament

NOW = datetime(2026, 6, 12, 12, 0, tzinfo=UTC)
NAIVE_NOW = datetime(2026, 6, 12, 12, 0)


def make_match(**overrides: object) -> Match:
    """Build a valid FINISHED match; tests override only what they probe."""
    defaults: dict[str, object] = {
        "home_team": Team(name="Iran", code="IRN"),
        "away_team": Team(name="Spain", code="ESP"),
        "home_score": 1,
        "away_score": 0,
        "kickoff": NOW,
        "status": MatchStatus.FINISHED,
    }
    defaults.update(overrides)
    return Match(**defaults)  # type: ignore[arg-type]


class TestCoinEnum:
    def test_members_carry_symbol_and_full_name(self) -> None:
        assert Coin.BTC.symbol == "BTC"
        assert Coin.BTC.full_name == "Bitcoin"
        assert Coin.ETH.full_name == "Ethereum"
        assert Coin.SOL.full_name == "Solana"

    def test_scope_is_exactly_three_coins(self) -> None:
        assert {coin.symbol for coin in Coin} == {"BTC", "ETH", "SOL"}


class TestCryptoPrice:
    def make_price(self, **overrides: object) -> CryptoPrice:
        defaults: dict[str, object] = {
            "symbol": "BTC",
            "name": "Bitcoin",
            "price_usd": 65_000.0,
            "price_toman": 4_500_000_000.0,
            "change_24h": 2.5,
            "last_updated": NOW,
        }
        defaults.update(overrides)
        return CryptoPrice(**defaults)  # type: ignore[arg-type]

    def test_happy_path_construction(self) -> None:
        price = self.make_price()
        assert price.symbol == "BTC"
        assert price.price_usd == 65_000.0

    def test_negative_change_is_valid(self) -> None:
        assert self.make_price(change_24h=-3.2).change_24h == -3.2

    def test_negative_price_usd_raises(self) -> None:
        with pytest.raises(ValueError):
            self.make_price(price_usd=-10.0)

    def test_negative_price_toman_raises(self) -> None:
        with pytest.raises(ValueError):
            self.make_price(price_toman=-1.0)

    def test_empty_symbol_raises(self) -> None:
        with pytest.raises(ValueError):
            self.make_price(symbol="")

    def test_naive_datetime_raises(self) -> None:
        with pytest.raises(ValueError):
            self.make_price(last_updated=NAIVE_NOW)

    def test_mutation_raises(self) -> None:
        price = self.make_price()
        with pytest.raises(FrozenInstanceError):
            price.price_usd = 200.0  # type: ignore[misc]

    def test_replace_creates_new_valid_object(self) -> None:
        original = self.make_price()
        updated = replace(original, price_usd=70_000.0)
        assert updated.price_usd == 70_000.0
        assert original.price_usd == 65_000.0  # original untouched


class TestTeam:
    def test_happy_path_with_and_without_code(self) -> None:
        assert Team(name="Iran", code="IRN").code == "IRN"
        assert Team(name="Iran").code is None

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError):
            Team(name="")

    def test_wrong_length_code_raises(self) -> None:
        with pytest.raises(ValueError):
            Team(name="Iran", code="IR")

    def test_mutation_raises(self) -> None:
        team = Team(name="Iran", code="IRN")
        with pytest.raises(FrozenInstanceError):
            team.name = "Persia"  # type: ignore[misc]


class TestMatch:
    def test_happy_path_finished(self) -> None:
        match = make_match()
        assert match.status is MatchStatus.FINISHED
        assert (match.home_score, match.away_score) == (1, 0)

    def test_happy_path_scheduled_without_scores(self) -> None:
        match = make_match(
            home_score=None, away_score=None, status=MatchStatus.SCHEDULED
        )
        assert match.home_score is None

    def test_scheduled_with_scores_raises(self) -> None:
        with pytest.raises(ValueError):
            make_match(status=MatchStatus.SCHEDULED)

    def test_finished_without_scores_raises(self) -> None:
        with pytest.raises(ValueError):
            make_match(home_score=None, away_score=None)

    def test_live_without_scores_raises(self) -> None:
        with pytest.raises(ValueError):
            make_match(home_score=None, away_score=None, status=MatchStatus.LIVE)

    def test_negative_score_raises(self) -> None:
        with pytest.raises(ValueError):
            make_match(home_score=-1)

    def test_naive_kickoff_raises(self) -> None:
        with pytest.raises(ValueError):
            make_match(kickoff=NAIVE_NOW)


class TestTournament:
    def test_happy_path(self) -> None:
        tournament = Tournament(
            name="World Cup 2026",
            matches=(make_match(),),
            current_stage="Group Stage",
        )
        assert tournament.name == "World Cup 2026"
        assert len(tournament.matches) == 1

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError):
            Tournament(name="", matches=(), current_stage="Group Stage")

    def test_empty_stage_raises(self) -> None:
        with pytest.raises(ValueError):
            Tournament(name="World Cup 2026", matches=(), current_stage="")
