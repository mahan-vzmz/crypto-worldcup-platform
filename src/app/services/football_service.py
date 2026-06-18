"""Football orchestration: cache-then-fetch with TTL and offline fallback.

Same policy as the crypto service (ADR-006), applied to a Tournament. V2: the
repository owns the model<->row mapping, so this service is now pure
orchestration -- the heavy serialization that lived here in V1 is gone.
"""

from app.clients.protocols import FootballClientProtocol
from app.models.football import Tournament
from app.services.cache_strategy import CacheStrategyProtocol
from app.storage.base_repository import BaseRepository
from app.utils.exceptions import APIError
from app.utils.logger import get_logger
from app.utils.result import Err, Ok, Result

logger = get_logger(__name__)


class FootballService:
    """Coordinates the football client and the storage repository."""

    def __init__(
        self,
        client: FootballClientProtocol,
        repository: BaseRepository,
        cache_strategy: CacheStrategyProtocol,
    ) -> None:
        self._client = client
        self._repository = repository
        self._cache_strategy = cache_strategy

    async def get_tournament(
        self, competition_code: str = "WC"
    ) -> Result[Tournament, APIError]:
        """Return the tournament, preferring fresh cache, then API, then stale.

        Returns an Ok with the Tournament on success, or an Err with an APIError
        if the API fails and no cache exists at all.
        """
        cached = await self._repository.load_tournament(competition_code)
        if cached is not None and self._cache_strategy.is_fresh(cached.fetched_at):
            logger.debug(f"football cache hit for {competition_code} (fresh)")
            return Ok(cached.data)

        try:
            tournament = await self._client.fetch_tournament(competition_code)
        except APIError as exc:
            if cached is not None:
                logger.warning(
                    f"football API unavailable; serving stale cache "
                    f"for {competition_code}"
                )
                return Ok(cached.data)
            logger.error("football API unavailable and no cache to fall back on")
            return Err(exc)

        await self._repository.save_tournament(tournament)
        logger.debug(f"football cache refreshed from API for {competition_code}")
        return Ok(tournament)
