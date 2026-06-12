import sys
from rich.console import Console
from rich.panel import Panel

console = Console()


def main() -> None:
    """Entry point for the Crypto & World Cup Information Platform."""
    banner_text = (
        "[bold cyan]Crypto & World Cup Platform[/bold cyan]\n"
        "[green]Phase 0: Bootstrap Completed Successfully![/green]\n\n"
        f"Python Version: {sys.version.split()[0]}"
    )
    console.print(Panel(banner_text, border_style="bold magenta", expand=False))


if __name__ == "__main__":
    main()