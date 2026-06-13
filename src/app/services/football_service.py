"""Football orchestration: cache-then-fetch with TTL and offline fallback.

Same policy as the crypto service (ADR-006), applied to a Tournament.
The serialization boundary is heavier here: a Tournament nests Teams,
an enum, and optional scores, so the mappers are correspondingly larger
-- but the decision tree is identical.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from app.clients.football_client import FootballClient
from app.config.settings import Settings
from app.models.football import Match, MatchStatus, Team, Tournament
from app.storage.base_repository import BaseRepository
from app.utils.exceptions import APIError
from app.utils.logger import get_logger

logger = get_logger(__name__)

CACHE_KEY = "football_worldcup"


class FootballService:
    """Coordinates the football client and the cache repository."""

    def __init__(
        self,
        client: FootballClient,
        repository: BaseRepository,
        settings: Settings,
    ) -> None:
        self._client = client
        self._repository = repository
        self._settings = settings

    def get_tournament(self) -> Tournament:
        """Return the tournament, preferring fresh cache, then API, then stale.

        Raises:
            APIError: only when the API fails and no cache exists at all.
        """
        envelope = self._repository.load(CACHE_KEY)

        if envelope is not None and self._is_fresh(envelope):
            logger.debug("football cache hit (fresh)")
            return self._deserialize(envelope["data"])

        try:
            tournament = self._client.fetch_world_cup()
        except APIError:
            if envelope is not None:
                logger.warning("football API unavailable; serving stale cache")
                return self._deserialize(envelope["data"])
            logger.error("football API unavailable and no cache to fall back on")
            raise

        self._repository.save(CACHE_KEY, self._serialize(tournament))
        logger.debug("football cache refreshed from API")
        return tournament

    def _is_fresh(self, envelope: dict[str, Any]) -> bool:
        """True if the cache timestamp is within the configured TTL.

        A missing or unparseable timestamp is treated as stale.
        """
        raw = envelope.get("fetched_at")
        if not isinstance(raw, str):
            return False
        try:
            fetched_at = datetime.fromisoformat(raw)
        except ValueError:
            return False
        ttl = timedelta(seconds=self._settings.cache_ttl_seconds)
        return datetime.now(UTC) - fetched_at <= ttl

    @staticmethod
    def _serialize(tournament: Tournament) -> dict[str, Any]:
        """Map a Tournament to a JSON-safe payload."""
        return {
            "name": tournament.name,
            "current_stage": tournament.current_stage,
            "matches": [
                {
                    "home_team": {
                        "name": m.home_team.name,
                        "code": m.home_team.code,
                    },
                    "away_team": {
                        "name": m.away_team.name,
                        "code": m.away_team.code,
                    },
                    "home_score": m.home_score,
                    "away_score": m.away_score,
                    "kickoff": m.kickoff.isoformat(),
                    "status": m.status.value,
                }
                for m in tournament.matches
            ],
        }

    @staticmethod
    def _deserialize(data: dict[str, Any]) -> Tournament:
        """Map a cached payload back to a validated Tournament."""
        matches = tuple(
            Match(
                home_team=Team(
                    name=m["home_team"]["name"], code=m["home_team"]["code"]
                ),
                away_team=Team(
                    name=m["away_team"]["name"], code=m["away_team"]["code"]
                ),
                home_score=m["home_score"],
                away_score=m["away_score"],
                kickoff=datetime.fromisoformat(m["kickoff"]),
                status=MatchStatus(m["status"]),
            )
            for m in data["matches"]
        )
        return Tournament(
            name=data["name"],
            matches=matches,
            current_stage=data["current_stage"],
        )
