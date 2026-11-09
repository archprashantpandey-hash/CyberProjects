"""Generate readable reports from Vortex event logs."""

import json
from datetime import datetime
from pathlib import Path
from vortex.core.incus import validate_name


def generate_report(environment: str) -> str:
    """Read experiment events and produce a text report."""

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

    # Each experiment starts with an experiment_started event.
    # Only analyse events belonging to the latest run.
    start_indexes = [
        index
        for index, event in enumerate(events)
        if event.get("event") == "experiment_started"
    ]

    if not start_indexes:
        raise ValueError(
            "No experiment_started event found in the event log."
        )

    latest_start = start_indexes[-1]
    events = events[latest_start:]

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
        event.get("event") == "experiment_failed"
        for event in events
    )

    if failed:
        status = "FAILED"
    elif completed:
        status = "COMPLETED"
    else:
        status = "INCOMPLETE"

    lines = [
        "=" * 50,
        "                 VORTEX REPORT",
        "=" * 50,
        "",
        f"Environment: {environment}",
        f"Scenario:    {scenario}",
        f"Status:      {status}",
        "",
        "NETWORK CONDITIONS",
        "-" * 30,
    ]

    if applied:
        network = applied.get("details", {})
        lines.extend([
            f"Configured latency:       {network.get('latency_ms', 0)} ms",
            f"Configured packet loss:   {network.get('packet_loss_percent', 0)}%",
        ])
    else:
        lines.append("No successful application event recorded.")

    lines.extend([
        "",
        "EXPERIMENT TIMELINE",
        "-" * 30,
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

        lines.append(f"{time_text}  {name.replace('_', ' ').title()}")

    lines.extend([
        "",
        "RESULT",
        "-" * 30,
        f"Experiment status: {status}",
        f"Events recorded: {len(events)}",
        "=" * 50,
    ])

    report_text = "\n".join(lines)

    output_path = Path("reports") / f"{environment}-report.txt"
    output_path.write_text(report_text + "\n", encoding="utf-8")

    return report_text