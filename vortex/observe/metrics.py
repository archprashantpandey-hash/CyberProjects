"""Collect system metrics for Vortex environments."""

import re
from datetime import datetime, timezone

from vortex.core.incus import require_managed, run_incus


def collect_metrics(environment: str) -> dict:
    """Collect available metrics from a Vortex-managed environment."""

    require_managed(environment)

    output = run_incus("info", environment)

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": environment,
        "status": "UNKNOWN",
        "cpu_usage_seconds": None,
        "memory_usage_bytes": None,
        "memory_peak_bytes": None,
    }

    status_match = re.search(
        r"^\s*Status:\s*(.+)$", output, re.MULTILINE
    )
    if status_match:
        result["status"] = status_match.group(1).strip()

    memory_match = re.search(
        r"^\s*Memory \(current\):\s*(.+)$",
        output,
        re.MULTILINE,
    )
    if memory_match:
        result["memory_usage_text"] = memory_match.group(1).strip()

    return result