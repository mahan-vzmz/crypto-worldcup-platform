"""football-data.org adapter: fetches World Cup data as a Tournament.

PROVISIONAL SPEC ASSUMPTIONS (verify against docs/taskbook.md):
- Provider is football-data.org v4; competition code ``WC``; API key
  sent via the ``X-Auth-Token`` header (matches FOOTBALL_API_KEY in
  Settings).
"""

from datetime import datetime
from typing import Any

from app.clients.base_client import DEFAULT_TIMEOUT, BaseAPIClient
from app.models.football import Match, MatchStatus, Team, Tournament
from app.utils.exceptions import APIError, ConfigError
from app.utils.logger import get_logger

logger = get_logger(__name__)

FOOTBALL_BASE_URL = "https://api.football-data.org/v4"

#: The provider's match states -> our three-state domain enum.
#: Anything not listed here is unrepresentable in V1 and is skipped.
_STATUS_MAP: dict[str, MatchStatus] = {
    "SCHEDULED": MatchStatus.SCHEDULED,
    "TIMED": MatchStatus.SCHEDULED,
    "POSTPONED": MatchStatus.SCHEDULED,
    "IN_PLAY": MatchStatus.LIVE,
    "PAUSED": MatchStatus.LIVE,
    "FINISHED": MatchStatus.FINISHED,
    "AWARDED": MatchStatus.FINISHED,
}


class FootballClient(BaseAPIClient):
    """Fetches and maps World Cup data into domain models."""

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ) -> None:
        # Point-of-use key validation (deferred from Settings by design).
        if not api_key:
            raise ConfigError(
                "FOOTBALL_API_KEY is not set; football data is unavailable"
            )
        super().__init__(
            FOOTBALL_BASE_URL,
            timeout=timeout,
            max_retries=max_retries,
            headers={"X-Auth-Token": api_key},
        )

    async def fetch_tournament(self, competition_code: str) -> Tournament:
        """Fetch all matches for a specific competition and assemble
        a Tournament snapshot.

        Raises:
            APIError: on transport failure or a malformed payload.
        """
        payload = await self.get_json(f"/competitions/{competition_code}/matches")
        if not isinstance(payload, dict):
            raise APIError("football API returned an unexpected payload shape")

        raw_matches = payload.get("matches")
        if not isinstance(raw_matches, list):
            raise APIError("football API response is missing 'matches'")

        matches: list[Match] = []
        for raw in raw_matches:
            match = self._parse_match(raw)
            if match is not None:
                matches.append(match)

        competition = payload.get("competition")
        name = (
            competition.get("name", competition_code)
            if isinstance(competition, dict)
            else competition_code
        )
        return Tournament(
            name=name,
            code=competition_code,
            matches=tuple(matches),
            current_stage=self._derive_stage(raw_matches),
        )

    def _parse_match(self, raw: Any) -> Match | None:
        """Map one provider match into the domain, or None if unmappable.

        A single odd match must not sink the whole tournament: matches in
        states our domain cannot represent are skipped with a warning.
        Structurally broken entries, however, indicate a contract change
        and raise APIError.
        """
        if not isinstance(raw, dict):
            raise APIError("football API returned a non-object match entry")

        status = _STATUS_MAP.get(raw.get("status", ""))
        if status is None:
            logger.warning(
                "skipping match with unsupported status %r", raw.get("status")
            )
            return None

        try:
            kickoff = datetime.fromisoformat(raw["utcDate"])
            home_team = self._parse_team(raw["homeTeam"])
            away_team = self._parse_team(raw["awayTeam"])
            full_time = raw.get("score", {}).get("fullTime", {})
            home_score = full_time.get("home")
            away_score = full_time.get("away")
        except (KeyError, TypeError, ValueError) as exc:
            raise APIError("football API match entry is malformed") from exc

        if status is MatchStatus.SCHEDULED:
            home_score = away_score = None  # enforce the domain invariant
        elif home_score is None or away_score is None:
            logger.warning(
                "skipping %s match without scores: %s vs %s",
                status.name,
                home_team.name,
                away_team.name,
            )
            return None

        return Match(
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            kickoff=kickoff,
            status=status,
        )

    @staticmethod
    def _parse_team(raw: Any) -> Team:
        if not isinstance(raw, dict):
            raise APIError("football API returned a non-object team entry")
        # Knockout slots may have a null name before qualification.
        name = raw.get("name") or "TBD"
        code = raw.get("tla")
        return Team(name=name, code=code if isinstance(code, str) else None)

    @staticmethod
    def _derive_stage(raw_matches: list[Any]) -> str:
        """Best-effort current stage: first match still to be decided."""
        stage = None
        for raw in raw_matches:
            if isinstance(raw, dict) and raw.get("status") not in (
                "FINISHED",
                "AWARDED",
            ):
                stage = raw.get("stage")
                break
        if stage is None and raw_matches and isinstance(raw_matches[-1], dict):
            stage = raw_matches[-1].get("stage")
        if not isinstance(stage, str) or not stage:
            return "Unknown"
        return stage.replace("_", " ").title()
