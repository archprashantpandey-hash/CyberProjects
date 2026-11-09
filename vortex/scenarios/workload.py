"""Application workload and health-check execution."""

import time

from vortex.core.incus import exec_instance


class WorkloadCheckError(RuntimeError):
    """Raised when one or more application checks fail."""


def execute_workload_checks(
    environment: str,
    checks: list[dict],
    deadline: float,
) -> list[dict]:
    """Execute application checks within an experiment time window."""

    results = []

    for check in checks:

        started = time.monotonic()

        remaining = deadline - started

        if remaining <= 0:
            result = {
                "name": check["name"],
                "command": check["command"],
                "expected_exit_code": check["expected_exit_code"],
                "exit_code": None,
                "stdout": "",
                "stderr": "Experiment time limit reached before execution.",
                "timed_out": True,
                "duration_seconds": 0,
                "status": "TIMEOUT",
            }

            results.append(result)
            continue

        allowed_timeout = min(
            check["timeout_seconds"],
            remaining,
        )

        execution = exec_instance(
            environment,
            check["command"],
            timeout_seconds=allowed_timeout,
        )

        exit_code = execution["exit_code"]
        timed_out = execution["timed_out"]

        passed = (
            not timed_out
            and exit_code == check["expected_exit_code"]
        )

        status = (
            "PASSED"
            if passed
            else "TIMEOUT"
            if timed_out
            else "FAILED"
        )

        result = {
            "name": check["name"],
            "command": check["command"],
            "expected_exit_code": check["expected_exit_code"],
            "timeout_seconds": check["timeout_seconds"],
            **execution,
            "status": status,
        }

        results.append(result)

    return results