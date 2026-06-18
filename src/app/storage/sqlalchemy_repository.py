"""SQLAlchemy implementation of the repository contract."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.models.crypto import AssetType, CryptoPrice
from app.models.football import Match, MatchStatus, Team, Tournament
from app.storage.base_repository import BaseRepository, Cached
from app.storage.models import Base, MatchModel, PriceHistoryModel, TournamentModel
from app.utils.exceptions import StorageError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SQLAlchemyRepository(BaseRepository):
    """SQLAlchemy storage honouring the BaseRepository contract."""

    def __init__(self, database_url: str) -> None:
        self._engine = create_async_engine(database_url, echo=False)
        self._session_factory = async_sessionmaker(
            bind=self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def initialize(self) -> None:
        try:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as exc:
            raise StorageError("failed to initialise the database schema") from exc

    @asynccontextmanager
    async def _session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def save_prices(self, prices: list[CryptoPrice]) -> None:
        fetched_at = datetime.now(UTC)
        models = [
            PriceHistoryModel(
                symbol=p.symbol,
                name=p.name,
                price_usd=float(p.price_usd),
                price_toman=float(p.price_toman),
                change_24h=float(p.change_24h),
                asset_type=p.type.value,
                last_updated=p.last_updated,
                fetched_at=fetched_at,
            )
            for p in prices
        ]
        try:
            async with self._session() as session:
                session.add_all(models)
        except Exception as exc:
            raise StorageError("failed to save prices") from exc
        logger.debug("saved %d price rows", len(prices))

    async def load_latest_prices(self) -> Cached[list[CryptoPrice]] | None:
        try:
            async with self._session() as session:
                result = await session.execute(
                    select(func.max(PriceHistoryModel.fetched_at))
                )
                latest = result.scalar()
                if latest is None:
                    return None

                rows_result = await session.execute(
                    select(PriceHistoryModel)
                    .where(PriceHistoryModel.fetched_at == latest)
                    .order_by(PriceHistoryModel.id)
                )
                models = rows_result.scalars().all()
        except Exception as exc:
            raise StorageError("failed to load latest prices") from exc

        prices = [self._model_to_price(m) for m in models]
        # In case the database doesn't return aware datetime, ensure it has UTC tzinfo
        dt = latest if latest.tzinfo else latest.replace(tzinfo=UTC)
        return Cached(data=prices, fetched_at=dt)

    async def get_price_history(self, symbol: str, *, limit: int) -> list[CryptoPrice]:
        if limit <= 0:
            return []
        try:
            async with self._session() as session:
                result = await session.execute(
                    select(PriceHistoryModel)
                    .where(PriceHistoryModel.symbol == symbol)
                    .order_by(
                        desc(PriceHistoryModel.fetched_at), desc(PriceHistoryModel.id)
                    )
                    .limit(limit)
                )
                models = result.scalars().all()
        except Exception as exc:
            raise StorageError(f"failed to load history for {symbol!r}") from exc
        return [self._model_to_price(m) for m in models]

    async def save_tournament(self, tournament: Tournament) -> None:
        fetched_at = datetime.now(UTC)
        try:
            async with self._session() as session:
                old_ids_result = await session.execute(
                    select(TournamentModel.id).where(
                        TournamentModel.code == tournament.code
                    )
                )
                old_ids = old_ids_result.scalars().all()
                if old_ids:
                    await session.execute(
                        delete(MatchModel).where(MatchModel.tournament_id.in_(old_ids))
                    )
                    await session.execute(
                        delete(TournamentModel).where(TournamentModel.id.in_(old_ids))
                    )

                t_model = TournamentModel(
                    name=tournament.name,
                    code=tournament.code,
                    current_stage=tournament.current_stage,
                    fetched_at=fetched_at,
                )
                m_models = [
                    MatchModel(
                        home_name=m.home_team.name,
                        home_code=m.home_team.code,
                        away_name=m.away_team.name,
                        away_code=m.away_team.code,
                        home_score=m.home_score,
                        away_score=m.away_score,
                        kickoff=m.kickoff,
                        status=m.status.value,
                        tournament=t_model,
                    )
                    for m in tournament.matches
                ]
                session.add(t_model)
                session.add_all(m_models)
        except Exception as exc:
            raise StorageError("failed to save tournament") from exc
        logger.debug("saved tournament with %d matches", len(tournament.matches))

    async def load_tournament(self, name: str) -> Cached[Tournament] | None:
        try:
            async with self._session() as session:
                result = await session.execute(
                    select(TournamentModel)
                    .options(selectinload(TournamentModel.matches))
                    .where(TournamentModel.code == name)
                    .order_by(
                        desc(TournamentModel.fetched_at), desc(TournamentModel.id)
                    )
                    .limit(1)
                )
                t_model = result.scalar_one_or_none()
                if t_model is None:
                    return None
        except Exception as exc:
            raise StorageError("failed to load tournament") from exc

        tournament = Tournament(
            name=t_model.name,
            code=t_model.code,
            matches=tuple(self._model_to_match(m) for m in t_model.matches),
            current_stage=t_model.current_stage,
        )
        dt = (
            t_model.fetched_at
            if t_model.fetched_at.tzinfo
            else t_model.fetched_at.replace(tzinfo=UTC)
        )
        return Cached(data=tournament, fetched_at=dt)

    @staticmethod
    def _model_to_price(model: PriceHistoryModel) -> CryptoPrice:
        lu = (
            model.last_updated
            if model.last_updated.tzinfo
            else model.last_updated.replace(tzinfo=UTC)
        )
        return CryptoPrice(
            symbol=model.symbol,
            name=model.name,
            price_usd=Decimal(str(model.price_usd)),
            price_toman=Decimal(str(model.price_toman)),
            change_24h=Decimal(str(model.change_24h)),
            type=AssetType(model.asset_type),
            last_updated=lu,
        )

    @staticmethod
    def _model_to_match(model: MatchModel) -> Match:
        ko = (
            model.kickoff if model.kickoff.tzinfo else model.kickoff.replace(tzinfo=UTC)
        )
        return Match(
            home_team=Team(name=model.home_name, code=model.home_code),
            away_team=Team(name=model.away_name, code=model.away_code),
            home_score=model.home_score,
            away_score=model.away_score,
            kickoff=ko,
            status=MatchStatus(model.status),
        )
