"""Command-line interface for Vortex CLI."""

import re
from pathlib import Path

import typer
from rich import box
from rich.table import Table
from rich.text import Text

from vortex.core.incus import (
    create_instance,
    destroy_instance,
    inspect_instance,
    list_instances,
    start_instance,
    stop_instance,
)

from vortex.scenarios.runner import run_experiment
from vortex.observe.report import generate_report
from vortex.observe.metrics import collect_metrics

from vortex.ui import (
    console,
    run_action,
    show_error,
    show_header,
    show_info,
    show_panel,
    show_success,
    show_warning,
)


app = typer.Typer(
    name="vortex",
    help="Create and manage temporary Linux testing environments.",
    no_args_is_help=True,
)

SCENARIO_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,39}$")


def execute_action(message, operation, *args, **kwargs):
    """Execute an operation with the shared Vortex interface."""

    try:
        return run_action(message, operation, *args, **kwargs)

    except KeyboardInterrupt:
        show_warning(
            "Experiment interrupted. Network cleanup was attempted."
        )
        raise typer.Exit(code=130)

    except BaseExceptionGroup as error:
        show_error(str(error))
        raise typer.Exit(code=1) from error

    except Exception as error:
        show_error(str(error))
        raise typer.Exit(code=1) from error


def resolve_scenario(scenario: str) -> Path:
    """Resolve a scenario name or explicitly supplied YAML file."""

    supplied_path = Path(scenario).expanduser()

    if supplied_path.is_file():
        return supplied_path.resolve()

    if "/" in scenario or "\\" in scenario:
        raise FileNotFoundError(
            f"Scenario file not found: {scenario}"
        )

    suffix = supplied_path.suffix.lower()

    if suffix not in ("", ".yaml", ".yml"):
        raise ValueError(
            "Provide a scenario name or a .yaml/.yml file."
        )

    name = supplied_path.stem if suffix else scenario

    if not SCENARIO_PATTERN.fullmatch(name):
        raise ValueError(
            "Scenario names must use lowercase letters, "
            "numbers and hyphens."
        )

    examples_dir = (
        Path(__file__).resolve().parent.parent
        / "scenarios"
        / "examples"
    )

    for extension in (".yaml", ".yml"):
        candidate = examples_dir / f"{name}{extension}"

        if candidate.is_file():
            return candidate

    raise FileNotFoundError(
        f"Scenario '{name}' was not found."
    )


def environment_table(environments):
    """Build a formatted environment table."""

    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold cyan",
        expand=True,
    )

    table.add_column("ENVIRONMENT", style="bold white")
    table.add_column("STATUS")
    table.add_column("TYPE")

    for env in environments:
        state = env["state"].upper()

        status_style = (
            "green"
            if state == "RUNNING"
            else "yellow"
        )

        table.add_row(
            env["name"],
            Text(f"● {state}", style=status_style),
            env["type"],
        )

    return table


@app.command()
def version() -> None:
    """Display the Vortex version."""

    show_header(
        "VERSION",
        [
            ("Application", "Vortex CLI"),
            ("Version", "0.1.0"),
        ],
    )

    show_success("Vortex is installed and ready.")


@app.command()
def status() -> None:
    """Display Vortex backend and feature status."""

    show_header("SYSTEM STATUS")

    content = (
        "BACKEND\n"
        "  Incus container engine\n\n"
        "AVAILABLE FEATURES\n"
        "  Environment management\n"
        "  Network chaos testing\n"
        "  Event recording\n"
        "  Experiment verification\n"
        "  Experiment reports\n"
        "  Environment metrics"
    )

    show_panel("VORTEX CAPABILITIES", content)


@app.command()
def create(
    name: str = typer.Argument(
        ...,
        help="Name for the new environment",
    ),
) -> None:
    """Create a temporary Debian Linux environment."""

    show_header(
        "CREATE",
        [
            ("Environment", name),
            ("Operating system", "Debian 12"),
            ("Isolation", "Incus container"),
        ],
    )

    execute_action(
        "Creating Linux environment",
        create_instance,
        name,
    )

    show_panel(
        "ENVIRONMENT READY",
        f"Environment: {name}\n"
        "Operating system: Debian 12\n"
        "Status: Created successfully",
        "green",
    )


@app.command("list")
def list_environments() -> None:
    """Display all Vortex-managed environments."""

    show_header("ENVIRONMENTS")

    environments = execute_action(
        "Loading environments",
        list_instances,
    )

    if not environments:
        show_warning("No Vortex environments found.")
        return

    console.print(environment_table(environments))

    running = sum(
        env["state"].upper() == "RUNNING"
        for env in environments
    )

    console.print()

    show_info(
        f"{len(environments)} environments  |  "
        f"{running} running  |  "
        f"{len(environments) - running} stopped"
    )


@app.command()
def inspect(
    name: str = typer.Argument(..., help="Environment name"),
) -> None:
    """Display detailed environment information."""

    show_header(
        "INSPECT",
        [("Environment", name)],
    )

    information = execute_action(
        "Reading environment information",
        inspect_instance,
        name,
    )

    show_panel(
        "ENVIRONMENT DETAILS",
        information,
    )


@app.command()
def start(
    name: str = typer.Argument(..., help="Environment name"),
) -> None:
    """Start a stopped environment."""

    show_header(
        "START",
        [("Environment", name)],
    )

    execute_action(
        "Starting Linux environment",
        start_instance,
        name,
    )

    show_panel(
        "ENVIRONMENT ACTIVE",
        f"{name} is now running.",
        "green",
    )


@app.command()
def stop(
    name: str = typer.Argument(..., help="Environment name"),
) -> None:
    """Stop a running environment."""

    show_header(
        "STOP",
        [("Environment", name)],
    )

    execute_action(
        "Stopping Linux environment",
        stop_instance,
        name,
    )

    show_panel(
        "ENVIRONMENT STOPPED",
        f"{name} has been stopped.",
        "yellow",
    )


@app.command()
def destroy(
    name: str = typer.Argument(..., help="Environment name"),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip deletion confirmation.",
    ),
) -> None:
    """Permanently delete a Vortex-managed environment."""

    show_header(
        "DESTROY",
        [("Environment", name)],
    )

    show_warning(
        "This operation permanently deletes the environment."
    )

    if not yes:
        confirmed = typer.confirm(
            f"Delete environment '{name}'?"
        )

        if not confirmed:
            show_warning("Deletion cancelled.")
            raise typer.Exit()

    execute_action(
        "Deleting Linux environment",
        destroy_instance,
        name,
    )

    show_success(f"Environment '{name}' deleted.")


@app.command()
def run(
    scenario: str = typer.Argument(
        ...,
        help="Scenario name or YAML file path",
    ),
    environment: str = typer.Argument(
        ...,
        help="Target environment",
    ),
) -> None:
    """Run a verified network experiment."""

    try:
        scenario_path = resolve_scenario(scenario)

        run_experiment(
            str(scenario_path),
            environment,
        )

    except Exception as error:
        show_error(str(error))
        raise typer.Exit(code=1) from error


@app.command()
def report(
    environment: str = typer.Argument(
        ...,
        help="Environment name",
    ),
) -> None:
    """Generate an experiment report."""

    show_header(
        "REPORT",
        [("Environment", environment)],
    )

    report_text = execute_action(
        "Generating experiment report",
        generate_report,
        environment,
    )

    show_panel(
        "EXPERIMENT REPORT",
        report_text,
        "cyan",
    )


@app.command()
def metrics(
    environment: str = typer.Argument(
        ...,
        help="Environment name",
    ),
) -> None:
    """Display environment metrics."""

    show_header(
        "METRICS",
        [("Environment", environment)],
    )

    data = execute_action(
        "Collecting environment metrics",
        collect_metrics,
        environment,
    )

    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold cyan",
    )

    table.add_column("METRIC", style="white")
    table.add_column("VALUE", style="bold")

    table.add_row("Environment", data["environment"])
    table.add_row("Status", data["status"])
    table.add_row("Timestamp", data["timestamp"])

    table.add_row(
        "Memory usage",
        data.get("memory_usage_text", "Unavailable"),
    )

    cpu = data["cpu_usage_seconds"]

    table.add_row(
        "CPU usage",
        f"{cpu} seconds" if cpu is not None else "Unavailable",
    )

    memory_peak = data["memory_peak_bytes"]

    table.add_row(
        "Memory peak",
        f"{memory_peak} bytes"
        if memory_peak is not None
        else "Unavailable",
    )

    console.print(table)

    show_info(
        "Unavailable measurements are not currently exposed "
        "by the metrics collector."
    )


if __name__ == "__main__":
    app()