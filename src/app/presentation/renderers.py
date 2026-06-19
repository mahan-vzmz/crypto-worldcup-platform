"""Pure presentation: domain models -> rich renderables.

No business logic, no I/O beyond returning renderables. Every function
here takes typed models and produces something rich can print. This
layer depends only on the models below it.
"""

from decimal import Decimal

from rich.table import Table
from rich.text import Text

from app.models.crypto import CryptoPrice


def _format_change(change_24h: Decimal) -> Text:
    """Colour a 24h change green (up), red (down), or dim (flat)."""
    if change_24h > 0:
        return Text(f"+{change_24h:.2f}%", style="green")
    if change_24h < 0:
        return Text(f"{change_24h:.2f}%", style="red")
    return Text("0.00%", style="dim")


def render_prices(prices: list[CryptoPrice]) -> Table:
    """Build a table of coin prices (USD, Toman, 24h change, updated)."""
    table = Table(title="Market Prices", expand=False)
    table.add_column("Asset", style="bold cyan")
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


def render_price_history(symbol: str, history: list[CryptoPrice]) -> Table:
    """Build a table of a single asset's recorded price snapshots (newest first)."""
    title = f"{symbol} price history ({len(history)} most recent)"
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


    return table
