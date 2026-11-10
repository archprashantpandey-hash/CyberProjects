"""Runtime detection and verification for Vortex applications."""

from pathlib import PurePosixPath

from vortex.core.incus import exec_instance

from vortex.apps.security import (
    APPLICATION_UID,
    APPLICATION_GID,
)


RUNTIME_PROFILES = {
    "python3": {
        "name": "Python 3",
        "package": "python3",
        "version_command": ["python3", "--version"],
    },
    "node": {
        "name": "Node.js",
        "package": "nodejs",
        "version_command": ["node", "--version"],
    },
    "npm": {
        "name": "npm",
        "package": "npm",
        "version_command": ["npm", "--version"],
    },
    "java": {
        "name": "Java",
        "package": "default-jre-headless",
        "version_command": ["java", "-version"],
    },
}


class RuntimeDetectionError(RuntimeError):
    """Raised when runtime verification fails."""


def identify_runtime(command: list[str]) -> dict | None:
    """Identify a supported runtime from the application command."""

    if not isinstance(command, list) or not command:
        raise RuntimeDetectionError(
            "Cannot identify runtime from an empty command."
        )

    executable = PurePosixPath(command[0]).name

    profile = RUNTIME_PROFILES.get(executable)

    if profile is None:
        return None

    return {
        "executable": executable,
        **profile,
    }


def _execute_as_application(
    environment: str,
    command: list[str],
) -> dict:
    """Execute a runtime check under the unprivileged identity."""

    return exec_instance(
        environment,
        command,
        timeout_seconds=15,
        user=APPLICATION_UID,
        group=APPLICATION_GID,
    )


def inspect_runtime(
    environment: str,
    command: list[str],
) -> dict:
    """Detect and inspect the application's required runtime."""

    profile = identify_runtime(command)

    executable = command[0]

    # Check executable availability without constructing
    # a shell command from application-controlled input.
    probe = _execute_as_application(
        environment,
        [
            "sh",
            "-c",
            'command -v "$1" >/dev/null 2>&1',
            "vortex-runtime-check",
            executable,
        ],
    )

    available = (
        not probe["timed_out"]
        and probe["exit_code"] == 0
    )

    result = {
        "executable": executable,
        "runtime": (
            profile["name"]
            if profile
            else "Unmanaged executable"
        ),
        "supported": profile is not None,
        "available": available,
        "version": None,
    }

    if not available:
        return result

    if profile is not None:

        version_result = _execute_as_application(
            environment,
            profile["version_command"],
        )

        if version_result["timed_out"]:
            raise RuntimeDetectionError(
                f"Runtime version check timed out: "
                f"{profile['name']}"
            )

        if version_result["exit_code"] != 0:
            raise RuntimeDetectionError(
                f"Could not determine runtime version: "
                f"{profile['name']}"
            )

        result["version"] = (
            version_result["stdout"].strip()
            or version_result["stderr"].strip()
        )

    return result