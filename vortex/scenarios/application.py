"""Application resilience measurement and comparison."""


def _summarize_phase(results: list[dict], phase: str) -> dict:
    """Calculate execution metrics for one experiment phase."""

    if not results:
        raise ValueError(
            f"{phase} execution results cannot be empty."
        )

    durations = []
    passed = 0

    for index, result in enumerate(results, start=1):

        try:
            duration = float(result["duration_seconds"])

        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid execution duration in {phase} "
                f"result {index}."
            ) from exc

        if duration < 0 or duration != duration or duration == float("inf"):
            raise ValueError(
                f"Invalid execution duration in {phase} "
                f"result {index}."
            )

        durations.append(duration)

        if result.get("status") == "PASSED":
            passed += 1

    total = len(results)
    failed = total - passed
    total_duration = sum(durations)
    average_duration = total_duration / total

    return {
        "runs": total,
        "passed": passed,
        "failed": failed,
        "failure_rate_percent": round(
            failed / total * 100,
            2,
        ),
        "total_duration_seconds": round(
            total_duration,
            3,
        ),
        "average_duration_seconds": round(
            average_duration,
            3,
        ),
    }


def compare_application_phases(
    baseline_results: list[dict],
    chaos_results: list[dict],
) -> dict:
    """Compare normal application behaviour against chaos behaviour."""

    baseline = _summarize_phase(
        baseline_results,
        "Baseline",
    )

    chaos = _summarize_phase(
        chaos_results,
        "Chaos",
    )

    duration_change = (
        chaos["average_duration_seconds"]
        - baseline["average_duration_seconds"]
    )

    duration_change_percent = None

    if baseline["average_duration_seconds"] > 0:

        duration_change_percent = round(
            duration_change
            / baseline["average_duration_seconds"]
            * 100,
            2,
        )

    failure_rate_change = (
        chaos["failure_rate_percent"]
        - baseline["failure_rate_percent"]
    )

    if failure_rate_change > 0:
        failure_outcome = "REGRESSION"

    elif failure_rate_change < 0:
        failure_outcome = "IMPROVEMENT"

    else:
        failure_outcome = "UNCHANGED"

    return {
        "baseline": baseline,
        "chaos": chaos,
        "average_duration_change_seconds": round(
            duration_change,
            3,
        ),
        "average_duration_change_percent": (
            duration_change_percent
        ),
        "failure_rate_change_percentage_points": round(
            failure_rate_change,
            2,
        ),
        "failure_outcome": failure_outcome,
    }