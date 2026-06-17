"""Formatters for Telegram messages using HTML parse mode."""

import html
from collections.abc import Sequence

from app.models.crypto import CryptoPrice
from app.models.football import MatchStatus, Tournament


def format_prices(prices: Sequence[CryptoPrice], title: str = "Market Prices") -> str:
    """Format a list of prices into an HTML message."""
    if not prices:
        return f"<b>{html.escape(title)}</b>\n\nNo data available."

    lines = [f"📊 <b>{html.escape(title)}</b>\n"]
    for p in prices:
        symbol = html.escape(p.symbol)
        name = html.escape(p.name)

        # Handle small numbers gracefully (like SHIB)
        usd = f"${p.price_usd:,.4f}" if p.price_usd < 1 else f"${p.price_usd:,.2f}"
        toman = f"{p.price_toman:,.0f} T"

        change = p.change_24h
        if change > 0:
            trend = f"🟢 +{change:.2f}%"
        elif change < 0:
            trend = f"🔴 {change:.2f}%"
        else:
            trend = "⚪ 0.00%"

        lines.append(
            f"🔹 <b>{symbol}</b> ({name})\n💵 {usd} | 🇮🇷 {toman}\n📈 24h: {trend}\n"
        )

    lines.append("\n<i>Showing top results. Use /price &lt;symbol&gt; for others.</i>")

    return "\n".join(lines)


def format_tournament(tournament: Tournament) -> str:
    """Format a tournament and its matches into an HTML message."""
    name = html.escape(tournament.name)
    stage = html.escape(tournament.current_stage)

    lines = [f"⚽ <b>{name}</b> ({stage})\n"]

    if not tournament.matches:
        lines.append("No matches scheduled.")
        return "\n".join(lines)

    for m in tournament.matches:
        home = html.escape(m.home_team.name)
        away = html.escape(m.away_team.name)

        if m.status == MatchStatus.SCHEDULED:
            score = "vs"
            status_icon = "📅"
        elif m.status == MatchStatus.LIVE:
            score = f"{m.home_score} - {m.away_score}"
            status_icon = "🔴 LIVE"
        else:
            score = f"{m.home_score} - {m.away_score}"
            status_icon = "✅ FT"

        time_str = m.kickoff.strftime("%H:%M UTC")

        lines.append(f"{status_icon} <b>{home}</b> {score} <b>{away}</b> 🕒 {time_str}")

    return "\n".join(lines)
