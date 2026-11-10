"""Application-oriented Vortex commands."""

import typer

from rich import box
from rich.table import Table

from vortex.apps.inspection import inspect_application_spec
from vortex.apps.spec import ApplicationSpecError
from vortex.ui import console, show_error
from vortex.apps.loader import load_application
from vortex.apps.runner import run_application


app = typer.Typer(
    name="app",
    help="Inspect and prepare applications for testing.",
    no_args_is_help=True,
)


@app.command("inspect")
def inspect_application(
    specification: str = typer.Argument(
        ...,
        help="Path to the application YAML specification.",
    ),
) -> None:
    """Inspect an application specification without executing it."""

    try:
        details = inspect_application_spec(specification)

    except ApplicationSpecError as error:
        show_error(str(error))
        raise typer.Exit(code=1) from error

    table = Table(
        title="APPLICATION INSPECTION",
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold cyan",
        expand=True,
    )

    table.add_column("PROPERTY", style="bold white")
    table.add_column("VALUE", overflow="fold")

    for key, value in details.items():
        table.add_row(key, str(value))

    console.print()
    console.print(table)
    console.print()

@app.command("load")
def load_application_command(
    specification: str = typer.Argument(
        ...,
        help="Application specification YAML file.",
    ),
    environment: str = typer.Argument(
        ...,
        help="Target Vortex environment.",
    ),
) -> None:
    """Transfer an application into a Vortex environment."""

    try:
        result = load_application(
            specification,
            environment,
        )

    except Exception as error:
        show_error(str(error))
        raise typer.Exit(code=1) from error

    table = Table(
        title="APPLICATION LOADED",
        box=box.ROUNDED,
        border_style="green",
        header_style="bold green",
    )

    table.add_column("PROPERTY")
    table.add_column("VALUE", overflow="fold")

    for key, value in result.items():
        table.add_row(key.replace("_", " ").title(), str(value))

    console.print()
    console.print(table)

@app.command("run")
def run_application_command(
    specification: str = typer.Argument(
        ...,
        help="Application specification YAML file.",
    ),
    environment: str = typer.Argument(
        ...,
        help="Target Vortex environment.",
    ),
    provision_runtime: bool = typer.Option(
        False,
        "--provision-runtime",
        help="Install a missing supported runtime inside the container.",
    ),
) -> None:
    """Execute an application inside a Vortex environment."""

    try:
        result = run_application(
            specification,
            environment,
            provision_missing_runtime=provision_runtime,
        )

    except Exception as error:
        show_error(str(error))
        raise typer.Exit(code=1) from error

    table = Table(
        title="APPLICATION EXECUTION",
        box=box.ROUNDED,
        border_style="green" if result["status"] == "PASSED" else "red",
        header_style="bold cyan",
    )

    table.add_column("PROPERTY")
    table.add_column("VALUE", overflow="fold")

    for key in (
        "application",
        "environment",
        "execution_user",
        "execution_uid",
        "execution_gid",
        "repetitions",
        "passed",
        "failed",
        "status",
        "duration_seconds",
        "runtime",
        "runtime_executable",
        "runtime_version",
        "runtime_provisioned",
        "runtime_package",
        "runtime_provisioning_duration_seconds",
    ):
        table.add_row(
            key.replace("_", " ").title(),
            str(result[key]),
        )

    console.print()
    console.print(table)

    for item in result["results"]:

        console.print(
            f"\nRepetition {item['repetition']}: "
            f"{item['status']} "
            f"({item['duration_seconds']} seconds)"
        )

        if item["stdout"]:
            console.print(f"  stdout: {item['stdout']}")

        if item["stderr"]:
            console.print(f"  stderr: {item['stderr']}")

    if result["status"] != "PASSED":
        show_error("One or more application executions failed.")
        raise typer.Exit(code=1)