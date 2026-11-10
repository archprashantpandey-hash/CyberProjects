"""Controlled runtime provisioning inside Vortex environments."""

from time import monotonic

from vortex.apps.runtime import identify_runtime
from vortex.core.incus import exec_instance


ALLOWED_PACKAGES = {
    "python3",
    "nodejs",
    "npm",
    "default-jre-headless",
}

PACKAGE_MANAGER = "apt-get"

PROVISION_TIMEOUT = 300


class RuntimeProvisioningError(RuntimeError):
    """Raised when a runtime cannot be provisioned."""


def _run_root(
    environment: str,
    command: list[str],
    description: str,
    timeout_seconds: int = PROVISION_TIMEOUT,
) -> dict:
    """Execute a provisioning operation as container root."""

    try:
        result = exec_instance(
            environment,
            command,
            timeout_seconds=timeout_seconds,
        )

    except Exception as exc:
        raise RuntimeProvisioningError(
            f"{description}: {exc}"
        ) from exc

    if result["timed_out"]:
        raise RuntimeProvisioningError(
            f"{description}: operation timed out."
        )

    if result["exit_code"] != 0:
        detail = (
            result.get("stderr")
            or result.get("stdout")
            or "unknown error"
        )

        raise RuntimeProvisioningError(
            f"{description}: {detail.strip()[:1000]}"
        )

    return result


def provision_runtime(
    environment: str,
    command: list[str],
) -> dict:
    """Install a supported runtime using the container package manager."""

    profile = identify_runtime(command)

    if profile is None:
        raise RuntimeProvisioningError(
            f"Cannot automatically provision executable "
            f"'{command[0]}'. Its runtime is not supported."
        )

    package = profile["package"]

    # Never allow application specifications to choose
    # arbitrary system packages.
    if package not in ALLOWED_PACKAGES:
        raise RuntimeProvisioningError(
            f"Package '{package}' is not approved for provisioning."
        )

    started = monotonic()

    # Verify that apt-get is available inside the container.
    _run_root(
        environment,
        [
            "sh",
            "-c",
            "command -v apt-get >/dev/null 2>&1",
        ],
        "The environment does not support apt-get provisioning",
        timeout_seconds=15,
    )

    # Refresh package metadata.
    update = _run_root(
        environment,
        [
            PACKAGE_MANAGER,
            "update",
        ],
        "Package index update failed",
    )

    # Install only the predefined runtime package.
    installation = _run_root(
        environment,
        [
            "env",
            "DEBIAN_FRONTEND=noninteractive",
            PACKAGE_MANAGER,
            "install",
            "-y",
            "--no-install-recommends",
            package,
        ],
        f"Installation of {profile['name']} failed",
    )

    return {
        "runtime": profile["name"],
        "executable": profile["executable"],
        "package": package,
        "package_manager": PACKAGE_MANAGER,
        "update_duration_seconds": update["duration_seconds"],
        "installation_duration_seconds": (
            installation["duration_seconds"]
        ),
        "total_duration_seconds": round(
            monotonic() - started,
            3,
        ),
        "status": "INSTALLED",
    }