"""Interactive CLI menu: reads input, dispatches to services, renders.

Thin UI only -- no business logic. Service instances are injected; the
menu never builds them. AppError is caught here (the §5 rule: the user
sees a friendly message, never a raw traceback).
"""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from app.models.crypto import Coin
from app.presentation.renderers import render_prices, render_tournament
from app.services.crypto_service import CryptoService
from app.services.football_service import FootballService
from app.utils.exceptions import AppError, ConfigError
from app.utils.logger import get_logger

logger = get_logger(__name__)

_MENU = """\
[bold]Crypto & World Cup Platform[/bold]

  [cyan]1[/cyan]  All coin prices
  [cyan]2[/cyan]  Single coin price
  [cyan]3[/cyan]  World Cup matches
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
            choice = Prompt.ask("Select", choices=["1", "2", "3", "q"], default="q")
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
                self._show_world_cup()
        except ConfigError as exc:
            self._console.print(f"[yellow]Unavailable:[/yellow] {exc}")
        except AppError as exc:
            logger.warning("action %s failed: %s", choice, exc)
            self._console.print(f"[red]Sorry, that didn't work:[/red] {exc}")

    def _show_all_coins(self) -> None:
        prices = self._crypto.get_prices(list(Coin))
        self._console.print(render_prices(prices))

    def _show_single_coin(self) -> None:
        symbol = Prompt.ask("Coin", choices=[c.symbol for c in Coin])
        coin = next(c for c in Coin if c.symbol == symbol)
        prices = self._crypto.get_prices([coin])
        self._console.print(render_prices(prices))

    def _show_world_cup(self) -> None:
        tournament = self._football.get_tournament()
        self._console.print(render_tournament(tournament))
