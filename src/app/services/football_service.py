"""Football orchestration: cache-then-fetch with TTL and offline fallback.

Same policy as the crypto service (ADR-006), applied to a Tournament. V2: the
repository owns the model<->row mapping, so this service is now pure
orchestration -- the heavy serialization that lived here in V1 is gone.
"""

from app.clients.protocols import FootballClientProtocol
from app.config.settings import Settings
from app.models.football import Tournament
from app.services.cache_policy import is_fresh
from app.storage.base_repository import BaseRepository
from app.utils.exceptions import APIError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FootballService:
    """Coordinates the football client and the storage repository."""

    def __init__(
        self,
        client: FootballClientProtocol,
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
        cached = self._repository.load_latest_tournament()
        if cached is not None and is_fresh(
            cached.fetched_at, self._settings.cache_ttl_seconds
        ):
            logger.debug("football cache hit (fresh)")
            return cached.data

        try:
            tournament = self._client.fetch_world_cup()
        except APIError:
            if cached is not None:
                logger.warning("football API unavailable; serving stale cache")
                return cached.data
            logger.error("football API unavailable and no cache to fall back on")
            raise

        self._repository.save_tournament(tournament)
        logger.debug("football cache refreshed from API")
        return tournament
