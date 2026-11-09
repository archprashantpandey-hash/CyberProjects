"""Generate readable reports from Vortex event logs."""

import json
from datetime import datetime
from pathlib import Path

from vortex.core.incus import validate_name


def generate_report(environment: str) -> str:
    """Read experiment events and produce a detailed text report."""

    validate_name(environment)

    log_path = Path("reports") / f"{environment}.jsonl"

    if not log_path.is_file():
        raise FileNotFoundError(
            f"No event log found for '{environment}'."
        )

    events = []

    with log_path.open("r", encoding="utf-8") as file:

        for line_number, line in enumerate(file, start=1):

            if not line.strip():
                continue

            try:
                event = json.loads(line)

            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}."
                ) from exc

            events.append(event)

    if not events:
        raise ValueError("The event log is empty.")

    start_indexes = [
        index
        for index, event in enumerate(events)
        if event.get("event") == "experiment_started"
    ]

    if not start_indexes:
        raise ValueError(
            "No experiment_started event found in the event log."
        )

    events = events[start_indexes[-1]:]

    first = events[0]
    details = first.get("details", {})
    scenario = details.get("scenario", "Unknown")

    applied = next(
        (
            event for event in events
            if event.get("event") == "network_chaos_applied"
        ),
        None,
    )

    completed = any(
        event.get("event") == "experiment_duration_completed"
        for event in events
    )

    failed = any(
        event.get("event") in (
            "experiment_failed",
            "cleanup_failed",
        )
        for event in events
    )

    check_events = [
        event
        for event in events
        if event.get("event") == "application_check_completed"
    ]

    failed_checks = [
        event
        for event in check_events
        if event.get("details", {}).get("status") != "PASSED"
    ]

    if failed or failed_checks:
        status = "FAILED"
    elif completed:
        status = "COMPLETED"
    else:
        status = "INCOMPLETE"

    lines = [
        "=" * 55,
        "                    VORTEX REPORT",
        "=" * 55,
        "",
        f"Environment: {environment}",
        f"Scenario:    {scenario}",
        f"Status:      {status}",
        "",
        "NETWORK CONDITIONS",
        "-" * 35,
    ]

    if applied:

        network = applied.get("details", {})

        lines.extend([
            f"Configured latency:       {network.get('latency_ms', 0)} ms",
            f"Configured packet loss:   {network.get('packet_loss_percent', 0)}%",
        ])

    else:
        lines.append("No successful network impairment recorded.")

    lines.extend([
        "",
        "APPLICATION HEALTH CHECKS",
        "-" * 35,
    ])

    if not check_events:
        lines.append("No application checks recorded.")

    for event in check_events:

        check = event.get("details", {})

        lines.extend([
            f"Check: {check.get('name', 'Unknown')}",
            f"Result: {check.get('status', 'UNKNOWN')}",
            f"Exit code: {check.get('exit_code')}",
            f"Expected exit code: {check.get('expected_exit_code')}",
            f"Execution time: {check.get('duration_seconds', 0)} seconds",
            f"Timed out: {check.get('timed_out', False)}",
        ])

        if check.get("stdout"):
            lines.append(
                f"Output: {check['stdout'][:500]}"
            )

        if check.get("stderr"):
            lines.append(
                f"Error output: {check['stderr'][:500]}"
            )

        lines.append("")

    lines.extend([
        "EXPERIMENT TIMELINE",
        "-" * 35,
    ])

    for event in events:

        timestamp = event.get("timestamp", "")
        name = event.get("event", "unknown_event")

        try:
            time_text = datetime.fromisoformat(
                timestamp
            ).strftime("%H:%M:%S")

        except (ValueError, TypeError):
            time_text = "Unknown time"

        lines.append(
            f"{time_text}  {name.replace('_', ' ').title()}"
        )

    lines.extend([
        "",
        "RESULT",
        "-" * 35,
        f"Experiment status: {status}",
        f"Events recorded: {len(events)}",
        f"Application checks: {len(check_events)}",
        f"Failed checks: {len(failed_checks)}",
        "=" * 55,
    ])

    report_text = "\n".join(lines)

    output_path = Path("reports") / f"{environment}-report.txt"

    output_path.write_text(
        report_text + "\n",
        encoding="utf-8",
    )

    return report_text