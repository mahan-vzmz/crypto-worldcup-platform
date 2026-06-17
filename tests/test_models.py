"""Tests for the domain models: invariants, happy paths, immutability (#24).

No mocks, filesystem, or network -- models are the innermost layer and
depend only on the standard library.
"""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.crypto import AssetType, CryptoPrice
from app.models.football import Match, MatchStatus, Team, Tournament

NOW = datetime(2026, 6, 12, 12, 0, tzinfo=UTC)
NAIVE_NOW = datetime(2026, 6, 12, 12, 0)


def make_price(**overrides: object) -> CryptoPrice:
    """Build a valid CryptoPrice; tests override only what they probe."""
    defaults: dict[str, object] = {
        "symbol": "BTC",
        "name": "Bitcoin",
        "price_usd": Decimal("65000.0"),
        "price_toman": Decimal("4500000000.0"),
        "change_24h": Decimal("2.5"),
        "type": AssetType.CRYPTO,
        "last_updated": NOW,
    }
    defaults.update(overrides)
    return CryptoPrice(**defaults)  # type: ignore[arg-type]


def make_match(**overrides: object) -> Match:
    """Build a valid FINISHED match; tests override only the deviation."""
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


class TestCryptoPrice:
    def test_happy_path_construction(self) -> None:
        price = make_price()
        assert price.symbol == "BTC"
        assert price.price_usd == Decimal("65000.0")

    def test_negative_change_is_valid(self) -> None:
        assert make_price(change_24h=Decimal("-3.2")).change_24h == Decimal("-3.2")

    def test_negative_price_usd_raises(self) -> None:
        with pytest.raises(ValueError):
            make_price(price_usd=Decimal("-10.0"))

    def test_negative_price_toman_raises(self) -> None:
        with pytest.raises(ValueError):
            make_price(price_toman=Decimal("-1.0"))

    def test_empty_symbol_raises(self) -> None:
        with pytest.raises(ValueError):
            make_price(symbol="")

    def test_naive_datetime_raises(self) -> None:
        with pytest.raises(ValueError):
            make_price(last_updated=NAIVE_NOW)

    def test_mutation_raises(self) -> None:
        price = make_price()
        with pytest.raises(FrozenInstanceError):
            price.price_usd = Decimal("200.0")  # type: ignore[misc]

    def test_replace_creates_new_valid_object(self) -> None:
        original = make_price()
        updated = replace(original, price_usd=Decimal("70000.0"))
        assert updated.price_usd == Decimal("70000.0")
        assert original.price_usd == Decimal("65000.0")


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
            code="WC26",
            matches=(make_match(),),
            current_stage="Group Stage",
        )
        assert tournament.name == "World Cup 2026"
        assert tournament.code == "WC26"
        assert len(tournament.matches) == 1

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError):
            Tournament(name="", code="WC26", matches=(), current_stage="Group Stage")

    def test_empty_code_raises(self) -> None:
        with pytest.raises(ValueError):
            Tournament(
                name="World Cup 2026", code="", matches=(), current_stage="Group Stage"
            )

    def test_empty_stage_raises(self) -> None:
        with pytest.raises(ValueError):
            Tournament(name="World Cup 2026", code="WC26", matches=(), current_stage="")
