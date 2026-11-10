"""Application preflight inspection."""

from pathlib import Path
from shlex import join

from vortex.apps.spec import load_application_spec


def inspect_application_spec(path: str) -> dict:
    """Validate and inspect an application before execution."""

    spec = load_application_spec(path)

    source = Path(spec["source"])

    source_root = (
        source if source.is_dir()
        else source.parent
    )

    working_directory = (
        source_root / spec["working_directory"]
    ).resolve()

    enabled_resources = [
        resource.upper()
        for resource, enabled in spec["discovery"].items()
        if enabled
    ]

    return {
        "Application": spec["name"],
        "Source type": (
            "Directory" if source.is_dir() else "Single file"
        ),
        "Source path": str(source),
        "Working directory": str(working_directory),
        "Launch command": join(spec["command"]),
        "Execution timeout": f"{spec['timeout_seconds']} seconds",
        "Expected exit code": str(spec["expected_exit_code"]),
        "Workload repetitions": str(spec["repetitions"]),
        "Discovery targets": ", ".join(enabled_resources),
    }