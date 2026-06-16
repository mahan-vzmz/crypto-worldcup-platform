"""Pure presentation: domain models -> rich renderables.

No business logic, no I/O beyond returning renderables. Every function
here takes typed models and produces something rich can print. This
layer depends only on the models below it.
"""

from decimal import Decimal

from rich.table import Table
from rich.text import Text

from app.models.crypto import Coin, CryptoPrice
from app.models.football import Match, MatchStatus, Tournament


def _format_change(change_24h: Decimal) -> Text:
    """Colour a 24h change green (up), red (down), or dim (flat)."""
    if change_24h > 0:
        return Text(f"+{change_24h:.2f}%", style="green")
    if change_24h < 0:
        return Text(f"{change_24h:.2f}%", style="red")
    return Text("0.00%", style="dim")


def render_prices(prices: list[CryptoPrice]) -> Table:
    """Build a table of coin prices (USD, Toman, 24h change, updated)."""
    table = Table(title="Cryptocurrency Prices", expand=False)
    table.add_column("Coin", style="bold cyan")
    table.add_column("USD", justify="right")
    table.add_column("Toman", justify="right")
    table.add_column("24h", justify="right")
    table.add_column("Updated (UTC)", style="dim")

    for price in prices:
        table.add_row(
            f"{price.symbol}  {price.name}",
            f"${price.price_usd:,.2f}",
            f"{price.price_toman:,.0f}",
            _format_change(price.change_24h),
            price.last_updated.strftime("%Y-%m-%d %H:%M"),
        )
    return table


def render_price_history(coin: Coin, history: list[CryptoPrice]) -> Table:
    """Build a table of a single coin's recorded price snapshots (newest first)."""
    title = f"{coin.symbol} price history ({len(history)} most recent)"
    table = Table(title=title, expand=False)
    table.add_column("Updated (UTC)", style="dim")
    table.add_column("USD", justify="right")
    table.add_column("Toman", justify="right")
    table.add_column("24h", justify="right")

    if not history:
        table.add_row("[dim]no history recorded yet[/dim]", "", "", "")
        return table

    for price in history:
        table.add_row(
            price.last_updated.strftime("%Y-%m-%d %H:%M"),
            f"${price.price_usd:,.2f}",
            f"{price.price_toman:,.0f}",
            _format_change(price.change_24h),
        )
    return table


def _format_score(match: Match) -> str:
    """Render the score, or a dash for a match that has not started."""
    if match.home_score is None or match.away_score is None:
        return "-"
    return f"{match.home_score} - {match.away_score}"


def render_tournament(tournament: Tournament) -> Table:
    """Build a table of matches for the tournament."""
    table = Table(
        title=f"{tournament.name}  ({tournament.current_stage})",
        expand=False,
    )
    table.add_column("Kickoff (UTC)", style="dim")
    table.add_column("Home", justify="right", style="bold")
    table.add_column("Score", justify="center")
    table.add_column("Away", style="bold")
    table.add_column("Status")

    status_styles = {
        MatchStatus.LIVE: "bold green",
        MatchStatus.FINISHED: "dim",
        MatchStatus.SCHEDULED: "yellow",
    }
    for match in tournament.matches:
        table.add_row(
            match.kickoff.strftime("%Y-%m-%d %H:%M"),
            match.home_team.name,
            _format_score(match),
            match.away_team.name,
            Text(
                match.status.value.title(),
                style=status_styles[match.status],
            ),
        )
    return table
