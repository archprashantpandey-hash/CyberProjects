"""Generate readable reports from Vortex event logs."""

import json
from datetime import datetime
from pathlib import Path

from vortex.core.incus import validate_name

def _generate_application_report(
    environment: str,
    events: list[dict],

) -> str:
    """Generate a report for the latest application execution."""

    first = events[0]
    details = first.get("details", {})

    executions = [
        event.get("details", {})
        for event in events
        if event.get("event") == "application_execution_completed"
    ]

    passed = sum(
        item.get("status") == "PASSED"
        for item in executions
    )

    failed = len(executions) - passed

    finished_event = next(
        (
            event for event in reversed(events)
            if event.get("event") == "application_run_finished"
        ),
        None,
    )

    failed_event = any(
        event.get("event") == "application_run_failed"
        for event in events
    )

    interrupted_event = any(
        event.get("event") == "application_run_interrupted"
        for event in events
    )

    summary = (
        finished_event.get("details", {})
        if finished_event else {}
    )

    if failed_event:
        status = "FAILED"
    elif interrupted_event:
        status = "INTERRUPTED"
    elif finished_event:
        status = summary.get(
            "status",
            "FAILED" if failed else "PASSED",
        )
    else:
        status = "INCOMPLETE"

    command = details.get("command", [])

    lines = [
        "=" * 55,
        "              VORTEX APPLICATION REPORT",
        "=" * 55,
        "",
        f"Environment:       {environment}",
        f"Application:       {details.get('application', 'Unknown')}",
        f"Status:            {status}",
        f"Command:           {command}",
        f"Execution user:    {details.get('execution_user', 'Unknown')}",
        f"Execution UID:     {details.get('execution_uid', 'Unknown')}",
        f"Execution GID:     {details.get('execution_gid', 'Unknown')}",
        f"Expected exit:     {details.get('expected_exit_code', 'Unknown')}",
        f"Configured runs:   {details.get('repetitions', 'Unknown')}",
        f"Completed runs:    {len(executions)}",
        f"Passed:            {passed}",
        f"Failed:            {failed}",
        f"Total duration:    {summary.get('duration_seconds', 'Unknown')} seconds",
        f"Runtime:           {summary.get('runtime', 'Unknown')}",
        f"Runtime executable: {summary.get('runtime_executable', 'Unknown')}",
        f"Runtime version:   {summary.get('runtime_version', 'Unknown')}",
        f"Runtime provisioned: {summary.get('runtime_provisioned', False)}",
        f"Runtime package: {summary.get('runtime_package') or 'None'}",
        f"Provisioning duration: {summary.get('runtime_provisioning_duration_seconds', 0)} seconds",
        "",
        "APPLICATION EXECUTIONS",
        "-" * 35,
    ]

    if not executions:
        lines.append("No execution results recorded.")

    for item in executions:

        lines.extend([
            "",
            f"Repetition: {item.get('repetition', 'Unknown')}",
            f"Result: {item.get('status', 'UNKNOWN')}",
            f"Exit code: {item.get('exit_code')}",
            f"Expected exit code: {item.get('expected_exit_code')}",
            f"Duration: {item.get('duration_seconds', 0)} seconds",
            f"Timed out: {item.get('timed_out', False)}",
        ])

        if item.get("stdout"):
            lines.append(f"Output: {item['stdout'][:500]}")

        if item.get("stderr"):
            lines.append(f"Error: {item['stderr'][:500]}")

    lines.extend([
        "",
        "EXECUTION TIMELINE",
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
        f"Application status: {status}",
        f"Executions recorded: {len(executions)}",
        f"Successful executions: {passed}",
        f"Failed executions: {failed}",
        "=" * 55,
    ])

    report_text = "\n".join(lines)

    output_path = (
        Path("reports") / f"{environment}-report.txt"
    )

    output_path.write_text(
        report_text + "\n",
        encoding="utf-8",
    )

    return report_text

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
        if event.get("event") in (
            "experiment_started",
            "application_run_started",
        )
    ]

    if not start_indexes:
        raise ValueError(
            "No experiment_started event found in the event log."
        )

    events = events[start_indexes[-1]:]

    # Application reports and experiment reports use
    # different event structures.
    if events[0].get("event") == "application_run_started":
        return _generate_application_report(
            environment,
            events,
        )

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

    comparison_event = next(
        (
            event for event in events
            if event.get("event") == "application_resilience_compared"
        ),
        None,
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

    if comparison_event:
        comparison = comparison_event.get("details", {})
        baseline = comparison.get("baseline", {})
        chaos = comparison.get("chaos", {})

        lines.extend([
            "",
            "APPLICATION RESILIENCE",
            "-" * 35,
            f"Application: {comparison.get('application', 'Unknown')}",
            (
                f"Baseline: {baseline.get('passed', 0)}/"
                f"{baseline.get('runs', 0)} passed"
            ),
            (
                f"Under chaos: {chaos.get('passed', 0)}/"
                f"{chaos.get('runs', 0)} passed"
            ),
            (
                "Baseline average duration: "
                f"{baseline.get('average_duration_seconds', 0):.3f} seconds"
            ),
            (
                "Chaos average duration: "
                f"{chaos.get('average_duration_seconds', 0):.3f} seconds"
            ),
            (
                "Execution time change: "
                f"{comparison.get('average_duration_change_percent', 0):+.2f}%"
            ),
            (
                "Failure rate change: "
                f"{comparison.get('failure_rate_change_percentage_points', 0):+.2f} "
                "percentage points"
            ),
            f"Outcome: {comparison.get('failure_outcome', 'UNKNOWN')}",
        ])

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