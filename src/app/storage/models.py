"""SQLAlchemy declarative models for the application."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.models.crypto import AssetType


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""

    pass


class PriceHistoryModel(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    price_usd: Mapped[float] = mapped_column(Float)
    price_toman: Mapped[float] = mapped_column(Float)
    change_24h: Mapped[float] = mapped_column(Float)
    asset_type: Mapped[str] = mapped_column(String, default=AssetType.CRYPTO.value)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class UserModel(Base):
    __tablename__ = "bot_user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String)
    first_name: Mapped[str | None] = mapped_column(String)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    watchlists: Mapped[list["WatchlistModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class WatchlistModel(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("bot_user.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String, index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped["UserModel"] = relationship(back_populates="watchlists")
