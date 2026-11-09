"""Run verified experiments in Vortex environments."""

import sys
import time

import typer

from vortex.chaos.network import (
    apply_network_chaos,
    check_network_tools,
    remove_network_chaos,
    verify_network_baseline,
    verify_network_chaos,
    verify_network_cleanup,
)
from vortex.config import load_scenario
from vortex.core.incus import require_active_environment as require_managed
from vortex.lifecycle.locks import environment_lock
from vortex.observe.recorder import EventRecorder
from vortex.scenarios.workload import (
    execute_workload_checks,
    WorkloadCheckError,
)
from vortex.chaos import resources as resource_chaos


def show_step(message: str) -> None:
    """Display a simple operation message."""
    sys.stdout.write(f"  {message:<36} ... ")
    sys.stdout.flush()


def finish_step(status: str) -> None:
    """Display a coloured operation result."""
    color = (
        typer.colors.GREEN
        if status in ("OK", "DONE", "PASSED")
        else typer.colors.RED
    )

    typer.secho(status, fg=color, bold=True)


def record_safely(
    recorder: EventRecorder,
    event: str,
    details: dict,
    errors: list,
) -> None:
    """Record an event without interrupting required cleanup."""

    try:
        recorder.record(event, details)

    except Exception as exc:
        errors.append(exc)

        typer.echo(
            f"Warning: event recording failed: {exc}",
            err=True,
        )


def _run_experiment_locked(
    scenario_path: str,
    environment: str,
) -> None:
    """Run a verified network experiment and restore networking."""

    typer.echo()

    typer.secho(
        "╭────────────────────────────────────────╮",
        fg=typer.colors.CYAN,
        bold=True,
    )
    typer.secho(
        "│           VORTEX EXPERIMENT             │",
        fg=typer.colors.CYAN,
        bold=True,
    )
    typer.secho(
        "╰────────────────────────────────────────╯",
        fg=typer.colors.CYAN,
        bold=True,
    )

    typer.echo()
    typer.echo(f"  Environment : {environment}")

    show_step("Preparing experiment")

    try:
        scenario = load_scenario(scenario_path)
        require_managed(environment)
    except Exception:
        finish_step("FAILED")
        raise

    finish_step("OK")

    typer.echo(f"  Scenario    : {scenario['name']}")
    typer.echo()

    show_step("Checking environment")

    try:
        check_network_tools(environment)
    except Exception:
        finish_step("FAILED")
        raise

    finish_step("OK")

    recorder = EventRecorder(environment)
    network = scenario["network"]

    resources_config = scenario.get("resources", {})
    resources_requested = bool(resources_config)
    resource_baseline = None

    latency = network["latency_ms"]
    packet_loss = network["packet_loss_percent"]

    chaos_requested = latency > 0 or packet_loss > 0

# Capture and validate the original network configuration
    # before starting an experiment that changes networking.
    baseline_qdisc = None

    if chaos_requested:
        show_step("Checking original network")

        try:
            baseline_qdisc = verify_network_baseline(environment)
        except Exception:
            finish_step("FAILED")
            raise

        finish_step("PASSED")

    # Capture original resource settings before experimentation.
    if resources_requested:

        show_step("Checking original resource configuration")

        try:
            resource_baseline = resource_chaos.capture_resource_baseline(
                environment,
                resources_config,
            )
        except Exception:
            finish_step("FAILED")
            raise

        finish_step("PASSED")

    # Do not begin network changes if the initial event cannot be recorded.
    recorder.record(
        "experiment_started",
        {"scenario": scenario["name"]},
    )

    experiment_error = None
    cleanup_error = None
    resource_cleanup_error = None
    recording_errors = []

    try:
        if chaos_requested:

            show_step("Applying network changes")

            try:
                apply_network_chaos(
                    environment,
                    latency,
                    packet_loss,
                )
            except Exception:
                finish_step("FAILED")
                raise

            finish_step("OK")

            record_safely(
                recorder,
                "network_chaos_applied",
                {
                    "latency_ms": latency,
                    "packet_loss_percent": packet_loss,
                },
                recording_errors,
            )

            show_step("Checking network settings")

            try:
                actual_qdisc = verify_network_chaos(
                    environment,
                    latency,
                    packet_loss,
                )
            except Exception:
                finish_step("FAILED")
                raise

            finish_step("PASSED")

            settings = []

            if latency > 0:
                settings.append(f"Added delay: {latency} ms")

            if packet_loss > 0:
                settings.append(f"Packet loss: {packet_loss:g}%")

            for setting in settings:
                typer.echo(f"      {setting}")

            record_safely(
                recorder,
                "network_chaos_verified",
                {"actual_qdisc": actual_qdisc},
                recording_errors,
            )

        else:
            typer.secho(
                "  No network changes requested (normal test).",
                fg=typer.colors.YELLOW,
            )

        typer.echo()

        if resources_requested:

            show_step("Applying CPU and memory restrictions")

            try:
                actual_resources = resource_chaos.apply_resource_chaos(
                    environment,
                    resources_config,
                )
            except Exception:
                finish_step("FAILED")
                raise

            finish_step("PASSED")

            record_safely(
                recorder,
                "resource_chaos_verified",
                {"settings": actual_resources},
                recording_errors,
            )

            for key, value in actual_resources.items():
                typer.echo(f"      {key}: {value}")

        else:
            typer.echo("  No CPU or memory restrictions requested.")

        duration_started = time.monotonic()

        checks = scenario.get("checks", [])

        if checks:

            show_step("Executing application checks")

            try:
                check_results = execute_workload_checks(
                    environment,
                    checks,
                    deadline=(
                        duration_started
                        + scenario["duration_seconds"]
                    ),
                )

            except Exception:
                finish_step("FAILED")
                raise

            # Record every result before determining overall success.
            for result in check_results:

                record_safely(
                    recorder,
                    "application_check_completed",
                    result,
                    recording_errors,
                )

                typer.echo(
                    f"      {result['name']}: "
                    f"{result['status']} "
                    f"({result['duration_seconds']} seconds)"
                )

                if result["stdout"]:
                    typer.echo(
                        f"         stdout: "
                        f"{result['stdout'][:200]}"
                    )

                if result["stderr"]:
                    typer.echo(
                        f"         stderr: "
                        f"{result['stderr'][:200]}"
                    )

            failed_checks = [
                result
                for result in check_results
                if result["status"] != "PASSED"
            ]

            if failed_checks:
                finish_step("FAILED")

                raise WorkloadCheckError(
                    f"{len(failed_checks)} of "
                    f"{len(check_results)} application checks failed."
                )

            finish_step("PASSED")

        else:
            typer.echo(
                "  No application checks configured."
            )

        remaining = max(
            0,
            scenario["duration_seconds"]
            - (time.monotonic() - duration_started),
        )

        show_step(
            f"Completing test window "
            f"({scenario['duration_seconds']} seconds)"
        )

        try:
            if remaining > 0:
                time.sleep(remaining)

        except Exception:
            finish_step("FAILED")
            raise

        finish_step("DONE")

        record_safely(
            recorder,
            "experiment_duration_completed",
            {},
            recording_errors,
        )

    except BaseException as exc:
        experiment_error = exc

        event_name = (
            "experiment_interrupted"
            if isinstance(exc, KeyboardInterrupt)
            else "experiment_failed"
        )

        record_safely(
            recorder,
            event_name,
            {
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
            recording_errors,
        )

    # Network cleanup must be attempted even if the experiment fails.
    if chaos_requested:

        typer.echo()

        try:
            show_step("Restoring normal network")

            try:
                remove_network_chaos(environment)
            except Exception:
                finish_step("FAILED")
                raise

            finish_step("OK")

            show_step("Checking network reset")

            try:
                if baseline_qdisc is None:
                    raise RuntimeError(
                        "Original network baseline was not captured."
                    )

                actual_qdisc = verify_network_cleanup(
                    environment,
                    baseline_qdisc,
                )

            except Exception:
                finish_step("FAILED")
                raise

            finish_step("PASSED")

            record_safely(
                recorder,
                "network_cleanup_verified",
                {"actual_qdisc": actual_qdisc},
                recording_errors,
            )

        except BaseException as exc:
            cleanup_error = exc

            record_safely(
                recorder,
                "cleanup_failed",
                {
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                recording_errors,
            )

    else:
        typer.echo(
            "  Network restoration not needed for this test."
        )

    # Restore resources independently of network cleanup.
    if resources_requested:
        typer.echo()

        try:
            show_step("Restoring original CPU and memory settings")

            resource_chaos.restore_resource_baseline(
                environment,
                resource_baseline,
            )
            finish_step("OK")

            show_step("Verifying resource restoration")

            restored_resources = (
                resource_chaos.verify_resource_restoration(
                    environment,
                    resource_baseline,
                )
            )
            finish_step("PASSED")

            record_safely(
                recorder,
                "resource_cleanup_verified",
                {"settings": restored_resources},
                recording_errors,
            )

        except BaseException as exc:
            finish_step("FAILED")
            resource_cleanup_error = exc

            record_safely(
                recorder,
                "resource_cleanup_failed",
                {
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                recording_errors,
            )

    else:
        typer.echo("  Resource restoration not needed for this test.")

    if cleanup_error is None and resource_cleanup_error is None:
        record_safely(
            recorder,
            "experiment_finished",
            {},
            recording_errors,
        )

    failures = []

    if experiment_error is not None:
        failures.append(experiment_error)

    if cleanup_error is not None:
        failures.append(cleanup_error)

    if resource_cleanup_error is not None:

        failures.append(resource_cleanup_error)

    if recording_errors:
        failures.append(
            RuntimeError(
                "One or more experiment events could not be recorded: "
                + "; ".join(str(error) for error in recording_errors)
            )
        )

    if len(failures) == 1:

        if cleanup_error is not None:
            raise RuntimeError(
                "Experiment ended, but network cleanup could not "
                f"be confirmed: {cleanup_error}"
            ) from cleanup_error

        if resource_cleanup_error is not None:
            raise RuntimeError(
                "Experiment ended, but resource cleanup could not "
                f"be confirmed: {resource_cleanup_error}"
            ) from resource_cleanup_error

        raise failures[0]

    if len(failures) > 1:
        raise BaseExceptionGroup(
            "Multiple experiment errors occurred.",
            failures,
        )

    typer.echo()

    typer.secho(
        "  ✓ EXPERIMENT COMPLETED SUCCESSFULLY",
        fg=typer.colors.GREEN,
        bold=True,
    )

    typer.secho(
        "╰────────────────────────────────────────╯",
        fg=typer.colors.CYAN,
        bold=True,
    )

    typer.echo()

def run_experiment(
    scenario_path: str,
    environment: str,
) -> None:
    """Run an experiment while exclusively locking its environment."""

    with environment_lock(environment):
        _run_experiment_locked(
            scenario_path,
            environment,
        )