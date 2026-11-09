"""Shared terminal interface for Vortex CLI."""

from collections.abc import Callable
from typing import TypeVar

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme


T = TypeVar("T")


VORTEX_THEME = Theme({
    "vortex.brand": "bold bright_cyan",
    "vortex.success": "bold green",
    "vortex.warning": "bold yellow",
    "vortex.error": "bold red",
    "vortex.muted": "dim",
    "vortex.value": "bold white",
})


console = Console(
    theme=VORTEX_THEME,
    highlight=False,
)


def show_header(
    section: str,
    details: list[tuple[str, str]] | None = None,
) -> None:
    """Display a consistent Vortex section header."""

    content = Table.grid(padding=(0, 2))
    content.add_column(
        style="vortex.muted",
        justify="right",
    )
    content.add_column(style="vortex.value")

    if details:
        for label, value in details:
            content.add_row(
                Text(label.upper()),
                Text(str(value)),
            )
    else:
        content.add_row(
            "",
            Text("Linux environment orchestration", style="vortex.muted"),
        )

    title = Text.assemble(
        ("VORTEX", "bold cyan"),
        ("  /  ", "dim"),
        (section.upper(), "bold white"),
    )

    console.print()

    console.print(
        Panel(
            content,
            title=title,
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    console.print()


def run_action(
    message: str,
    operation: Callable[..., T],
    *args,
    **kwargs,
) -> T:
    """Execute a real operation with a live terminal spinner."""

    try:
        with console.status(
            f"[vortex.brand]{message}...[/]",
            spinner="dots",
        ):
            result = operation(*args, **kwargs)

    except BaseException:
        console.print(
            Text(f"  ✗ {message} failed", style="vortex.error")
        )
        raise

    show_success(message)

    return result


def show_success(message: str) -> None:
    """Display a successful operation."""

    console.print(
        Text(f"  ✓ {message}", style="vortex.success")
    )


def show_warning(message: str) -> None:
    """Display a warning."""

    console.print(
        Text(f"  ⚠ {message}", style="vortex.warning")
    )


def show_error(message: str) -> None:
    """Display an error."""

    console.print(
        Text(f"  ✗ {message}", style="vortex.error")
    )


def show_info(message: str) -> None:
    """Display additional information."""

    console.print(
        Text(f"  {message}", style="vortex.muted")
    )


def show_panel(
    title: str,
    content: str,
    border_style: str = "cyan",
) -> None:
    """Display information inside a Vortex panel."""

    console.print(
        Panel(
            Text(content),
            title=title,
            border_style=border_style,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )