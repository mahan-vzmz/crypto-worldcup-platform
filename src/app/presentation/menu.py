"""Interactive CLI menu: reads input, dispatches to services, renders.

Thin UI only -- no business logic. Service instances are injected; the
menu never builds them. AppError is caught here (the §5 rule: the user
sees a friendly message, never a raw traceback).
"""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt

from app.models.crypto import Coin
from app.presentation.renderers import (
    render_price_history,
    render_prices,
    render_tournament,
)
from app.services.crypto_service import CryptoService
from app.services.football_service import FootballService
from app.utils.exceptions import AppError, ConfigError
from app.utils.logger import get_logger
from app.utils.result import Ok

logger = get_logger(__name__)

_MENU = """\
[bold]Crypto & World Cup Platform[/bold]

  [cyan]1[/cyan]  All coin prices
  [cyan]2[/cyan]  Single coin price
  [cyan]3[/cyan]  Coin price history
  [cyan]4[/cyan]  World Cup matches
  [cyan]q[/cyan]  Quit"""


class Menu:
    """Drives the interactive loop, dispatching to injected services."""

    def __init__(
        self,
        crypto_service: CryptoService,
        football_service: FootballService,
        console: Console | None = None,
    ) -> None:
        self._crypto = crypto_service
        self._football = football_service
        self._console = console or Console()

    def run(self) -> None:
        """Main loop. Returns when the user chooses to quit."""
        self._console.print(Panel(_MENU, border_style="magenta", expand=False))
        while True:
            choice = Prompt.ask(
                "Select", choices=["1", "2", "3", "4", "q"], default="q"
            )
            if choice == "q":
                self._console.print("[dim]Goodbye.[/dim]")
                return
            self._dispatch(choice)

    def _dispatch(self, choice: str) -> None:
        """Run one action, translating any AppError into a friendly line."""
        try:
            if choice == "1":
                self._show_all_coins()
            elif choice == "2":
                self._show_single_coin()
            elif choice == "3":
                self._show_price_history()
            elif choice == "4":
                self._show_world_cup()
        except ConfigError as exc:
            self._console.print(f"[yellow]Unavailable:[/yellow] {exc}")
        except AppError as exc:
            logger.warning("action %s failed: %s", choice, exc)
            self._console.print(f"[red]Sorry, that didn't work:[/red] {exc}")

    def _show_all_coins(self) -> None:
        result = self._crypto.get_prices(list(Coin))
        if isinstance(result, Ok):
            self._console.print(render_prices(result.value))
        else:
            self._handle_error(result.error)

    def _show_single_coin(self) -> None:
        coin = self._ask_coin()
        result = self._crypto.get_prices([coin])
        if isinstance(result, Ok):
            self._console.print(render_prices(result.value))
        else:
            self._handle_error(result.error)

    def _show_price_history(self) -> None:
        coin = self._ask_coin()
        limit = IntPrompt.ask("How many records", default=10)
        result = self._crypto.get_price_history(coin, limit=limit)
        if isinstance(result, Ok):
            self._console.print(render_price_history(coin, result.value))
        else:
            self._handle_error(result.error)

    def _show_world_cup(self) -> None:
        result = self._football.get_tournament()
        if isinstance(result, Ok):
            self._console.print(render_tournament(result.value))
        else:
            self._handle_error(result.error)

    def _handle_error(self, exc: Exception) -> None:
        logger.warning("action failed: %s", exc)
        self._console.print(f"[red]Sorry, that didn't work:[/red] {exc}")

    def _ask_coin(self) -> Coin:
        symbol = Prompt.ask("Coin", choices=[c.symbol for c in Coin])
        return next(c for c in Coin if c.symbol == symbol)
