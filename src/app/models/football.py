"""Domain models for football (World Cup) data.

Pure value objects for teams, matches, and tournaments. The status
enum makes the match lifecycle explicit so invalid string states from
external APIs cannot leak inward.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MatchStatus(Enum):
    """Lifecycle state of a match. A closed set: no other values exist."""

    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"


@dataclass(frozen=True, slots=True)
class Team:
    """A team identified by name, with an optional short code (e.g. FIFA)."""

    name: str
    code: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must be a non-empty string")
        if self.code is not None and len(self.code) != 3:
            raise ValueError(
                f"code must be a 3-letter code when provided, got {self.code!r}"
            )


@dataclass(frozen=True, slots=True)
class Match:
    """A snapshot of a single match.

    Invariant: scores exist if and only if the match has started
    (LIVE or FINISHED). A SCHEDULED match has no scores yet.
    Scores are explicit (no defaults) so a caller must consciously
    pass ``None`` for an unplayed match.
    """

    home_team: Team
    away_team: Team
    home_score: int | None
    away_score: int | None
    kickoff: datetime
    status: MatchStatus

    def __post_init__(self) -> None:
        if self.kickoff.tzinfo is None:
            raise ValueError("kickoff must be timezone-aware (use UTC)")
        if self.home_score is not None and self.home_score < 0:
            raise ValueError("home_score must be non-negative")
        if self.away_score is not None and self.away_score < 0:
            raise ValueError("away_score must be non-negative")

        has_scores = (
            self.home_score is not None and self.away_score is not None
        )
        if self.status is MatchStatus.SCHEDULED and has_scores:
            raise ValueError("a SCHEDULED match cannot have scores")
        if self.status is not MatchStatus.SCHEDULED and not has_scores:
            raise ValueError(
                f"a {self.status.name} match must have both scores"
            )


@dataclass(frozen=True, slots=True)
class Tournament:
    """A tournament snapshot: its matches and current progress.

    ``matches`` is a tuple (not a list) so the frozen guarantee is
    honest: the container cannot be mutated after construction.
    """

    name: str
    matches: tuple[Match, ...]
    current_stage: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must be a non-empty string")
        if not self.current_stage:
            raise ValueError("current_stage must be a non-empty string")