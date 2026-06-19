"""Interactive CLI menu: reads input, dispatches to services, renders.

Thin UI only -- no business logic. Service instances are injected; the
menu never builds them. AppError is caught here (the §5 rule: the user
sees a friendly message, never a raw traceback).
"""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt

from app.presentation.renderers import (
    render_price_history,
    render_prices,
)
from app.services.crypto_service import CryptoService
from app.utils.exceptions import AppError, ConfigError
from app.utils.logger import get_logger
from app.utils.result import Ok

logger = get_logger(__name__)

_MENU = """\
[bold]Crypto & World Cup Platform[/bold]

  [cyan]1[/cyan]  All market prices
  [cyan]2[/cyan]  Single asset price
  [cyan]3[/cyan]  Asset price history
  [cyan]q[/cyan]  Quit"""


class Menu:
    """Drives the interactive loop, dispatching to injected services."""

    def __init__(
        self,
        crypto_service: CryptoService,
        console: Console | None = None,
    ) -> None:
        self._crypto = crypto_service
        self._console = console or Console()

    async def run(self) -> None:
        """Main loop. Returns when the user chooses to quit."""
        self._console.print(Panel(_MENU, border_style="magenta", expand=False))
        while True:
            choice = Prompt.ask(
                "Select", choices=["1", "2", "3", "q"], default="q"
            )
            if choice == "q":
                self._console.print("[dim]Goodbye.[/dim]")
                return
            await self._dispatch(choice)

    async def _dispatch(self, choice: str) -> None:
        """Run one action, translating any AppError into a friendly line."""
        try:
            if choice == "1":
                await self._show_all_prices()
            elif choice == "2":
                await self._show_single_price()
            elif choice == "3":
                await self._show_price_history()
        except ConfigError as exc:
            self._console.print(f"[yellow]Unavailable:[/yellow] {exc}")
        except AppError as exc:
            logger.warning("action %s failed: %s", choice, exc)
            self._console.print(f"[red]Sorry, that didn't work:[/red] {exc}")

    async def _show_all_prices(self) -> None:
        result = await self._crypto.get_prices()
        if isinstance(result, Ok):
            self._console.print(render_prices(result.value))
        else:
            self._handle_error(result.error)

    async def _show_single_price(self) -> None:
        symbol = self._ask_symbol()
        result = await self._crypto.get_prices()
        if isinstance(result, Ok):
            prices = [p for p in result.value if p.symbol == symbol]
            if prices:
                self._console.print(render_prices(prices))
            else:
                self._console.print(f"[red]Asset {symbol} not found.[/red]")
        else:
            self._handle_error(result.error)

    async def _show_price_history(self) -> None:
        symbol = self._ask_symbol()
        limit = IntPrompt.ask("How many records", default=10)
        result = await self._crypto.get_price_history(symbol, limit=limit)
        if isinstance(result, Ok):
            self._console.print(render_price_history(symbol, result.value))
        else:
            self._handle_error(result.error)

    def _handle_error(self, exc: Exception) -> None:
        logger.warning("action failed: %s", exc)
        self._console.print(f"[red]Sorry, that didn't work:[/red] {exc}")

    def _ask_symbol(self) -> str:
        return Prompt.ask("Asset Symbol (e.g. BTC, ETH, USD, GOLD)").upper()
