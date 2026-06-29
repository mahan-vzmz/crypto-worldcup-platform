"""SQLAlchemy implementation of the repository contract."""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import ColumnDefault, delete, desc, func, inspect, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql.schema import Column

from app.models.crypto import AssetType, CryptoPrice
from app.storage.base_repository import BaseRepository, Cached
from app.storage.models import Base, PriceHistoryModel
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
                # Lightweight migration: add columns introduced after a table was
                # first created (no Alembic). Idempotent — runs every startup.
                await conn.run_sync(self._add_missing_columns)
        except Exception as exc:
            raise StorageError("failed to initialise the database schema") from exc

    @staticmethod
    def _column_default_literal(column: Column[object]) -> str | None:
        """Render a column's Python default as a SQL literal, if it is scalar.

        Existing rows need a value when a NOT NULL column is added, so the
        ALTER must carry the same default the model declares.
        """
        default = column.default
        if not isinstance(default, ColumnDefault) or not default.is_scalar:
            return None
        value = default.arg
        if isinstance(value, str):
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        if isinstance(value, bool):
            return "1" if value else "0"
        return str(value)

    def _add_missing_columns(self, connection: Connection) -> None:
        """Add any model columns missing from existing tables (ADD COLUMN)."""
        inspector = inspect(connection)
        for table in Base.metadata.tables.values():
            if not inspector.has_table(table.name):
                continue
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                col_type = column.type.compile(dialect=connection.dialect)
                ddl = (
                    f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}'
                )
                default_literal = self._column_default_literal(column)
                if default_literal is not None:
                    ddl += f" DEFAULT {default_literal}"
                connection.execute(text(ddl))
                logger.info(
                    "schema migration: added column %s.%s",
                    table.name,
                    column.name,
                )

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
                image_url=p.image_url,
                market_cap=float(p.market_cap),
                volume_24h=float(p.volume_24h),
                rank=p.rank,
                sparkline=json.dumps(list(p.sparkline)),
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

    @staticmethod
    def _model_to_price(model: PriceHistoryModel) -> CryptoPrice:
        lu = (
            model.last_updated
            if model.last_updated.tzinfo
            else model.last_updated.replace(tzinfo=UTC)
        )
        try:
            sparkline = tuple(float(x) for x in json.loads(model.sparkline or "[]"))
        except (ValueError, TypeError):
            sparkline = ()
        return CryptoPrice(
            symbol=model.symbol,
            name=model.name,
            price_usd=Decimal(str(model.price_usd)),
            price_toman=Decimal(str(model.price_toman)),
            change_24h=Decimal(str(model.change_24h)),
            type=AssetType(model.asset_type),
            last_updated=lu,
            image_url=model.image_url or "",
            market_cap=Decimal(str(model.market_cap)),
            volume_24h=Decimal(str(model.volume_24h)),
            rank=model.rank,
            sparkline=sparkline,
        )

    # ---- user & watchlist ----

    async def get_or_create_user(
        self, telegram_id: int, username: str | None, first_name: str | None
    ) -> None:
        try:
            from app.storage.models import UserModel

            async with self._session() as session:
                result = await session.execute(
                    select(UserModel).where(UserModel.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()
                if not user:
                    user = UserModel(
                        telegram_id=telegram_id,
                        username=username,
                        first_name=first_name,
                        joined_at=datetime.now(UTC),
                    )
                    session.add(user)
                else:
                    # Update info if changed
                    user.username = username
                    user.first_name = first_name
        except Exception as exc:
            raise StorageError("failed to get or create user") from exc

    async def get_watchlist(self, telegram_id: int) -> list[str]:
        try:
            from app.storage.models import UserModel, WatchlistModel

            async with self._session() as session:
                result = await session.execute(
                    select(WatchlistModel.symbol)
                    .join(UserModel)
                    .where(UserModel.telegram_id == telegram_id)
                    .order_by(WatchlistModel.added_at)
                )
                return list(result.scalars().all())
        except Exception as exc:
            raise StorageError("failed to get watchlist") from exc

    async def add_to_watchlist(self, telegram_id: int, symbol: str) -> bool:
        symbol = symbol.upper()
        try:
            from app.storage.models import UserModel, WatchlistModel

            async with self._session() as session:
                result = await session.execute(
                    select(UserModel).where(UserModel.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()
                if not user:
                    user = UserModel(
                        telegram_id=telegram_id,
                        joined_at=datetime.now(UTC),
                    )
                    session.add(user)
                    await session.flush()

                # Check if exists
                existing = await session.execute(
                    select(WatchlistModel).where(
                        WatchlistModel.user_id == user.id,
                        WatchlistModel.symbol == symbol,
                    )
                )
                if existing.scalar_one_or_none():
                    return False  # Already in watchlist

                w = WatchlistModel(
                    user_id=user.id,
                    symbol=symbol,
                    added_at=datetime.now(UTC),
                )
                session.add(w)
                return True
        except Exception as exc:
            raise StorageError("failed to add to watchlist") from exc

    async def remove_from_watchlist(self, telegram_id: int, symbol: str) -> bool:
        symbol = symbol.upper()
        try:
            from app.storage.models import UserModel, WatchlistModel

            async with self._session() as session:
                result = await session.execute(
                    select(UserModel.id).where(UserModel.telegram_id == telegram_id)
                )
                user_id = result.scalar_one_or_none()
                if not user_id:
                    return False

                result = await session.execute(
                    delete(WatchlistModel).where(
                        WatchlistModel.user_id == user_id,
                        WatchlistModel.symbol == symbol,
                    )
                )
                return result.rowcount > 0  # type: ignore[attr-defined,no-any-return]
        except Exception as exc:
            raise StorageError("failed to remove from watchlist") from exc
