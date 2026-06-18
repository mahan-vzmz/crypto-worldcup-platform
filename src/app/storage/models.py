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


class TournamentModel(Base):
    __tablename__ = "tournament"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)
    code: Mapped[str] = mapped_column(String, default="WC", index=True)
    current_stage: Mapped[str] = mapped_column(String)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    matches: Mapped[list["MatchModel"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )


class MatchModel(Base):
    __tablename__ = "match"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournament.id", ondelete="CASCADE")
    )
    home_name: Mapped[str] = mapped_column(String)
    home_code: Mapped[str | None] = mapped_column(String)
    away_name: Mapped[str] = mapped_column(String)
    away_code: Mapped[str | None] = mapped_column(String)
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    kickoff: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String)

    tournament: Mapped["TournamentModel"] = relationship(back_populates="matches")
