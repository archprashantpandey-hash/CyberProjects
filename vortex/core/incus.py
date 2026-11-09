"""Incus backend for Vortex CLI."""

import json
import re
import shutil
import subprocess

IMAGE = "images:debian/12"
MANAGED_KEY = "user.vortex.managed"
INCUS = shutil.which("incus") or "incus"

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,39}$")


class IncusError(RuntimeError):
    """Raised when an Incus operation fails."""


def run_incus(*args: str) -> str:
    """Execute an Incus command safely."""
    try:
        result = subprocess.run(
            [INCUS, *args],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise IncusError(f"Could not execute Incus: {exc}") from exc

    if result.returncode != 0:
        raise IncusError(result.stderr.strip() or "Incus command failed.")

    return result.stdout.strip()


def validate_name(name: str) -> None:
    """Validate an environment name."""
    if not NAME_PATTERN.fullmatch(name):
        raise IncusError(
            "Use 1-40 lowercase letters, numbers, or hyphens. "
            "The name must start with a letter."
        )


def instance_exists(name: str) -> bool:
    """Check whether an Incus instance exists."""
    instances = json.loads(run_incus("list", "--format=json") or "[]")
    return any(item.get("name") == name for item in instances)


def is_managed(name: str) -> bool:
    """Check whether Vortex owns an instance."""
    if not instance_exists(name):
        return False

    try:
        return (
            run_incus("config", "get", name, MANAGED_KEY).lower()
            == "true"
        )
    except IncusError:
        return False


def require_managed(name: str) -> None:
    """Reject missing or unmanaged instances."""
    validate_name(name)

    if not instance_exists(name):
        raise IncusError(f"Environment '{name}' does not exist.")

    if not is_managed(name):
        raise IncusError(
            f"'{name}' is not Vortex-managed. Refusing to modify it."
        )


def create_instance(name: str) -> str:
    """Create a managed Debian container."""
    validate_name(name)

    if instance_exists(name):
        raise IncusError(f"Instance '{name}' already exists.")

    run_incus("launch", IMAGE, name)

    try:
        run_incus("config", "set", name, MANAGED_KEY, "true")
    except IncusError:
        try:
            run_incus("delete", "--force", name)
        except IncusError:
            pass
        raise

    return run_incus("info", name)


def list_instances() -> list[dict[str, str]]:
    """List Vortex-managed instances."""
    instances = json.loads(run_incus("list", "--format=json") or "[]")
    result = []

    for item in instances:
        name = item.get("name", "")
        if name and is_managed(name):
            result.append({
                "name": name,
                "state": item.get("status", "UNKNOWN"),
                "type": item.get("type", "unknown"),
            })

    return result


def inspect_instance(name: str) -> str:
    require_managed(name)
    return run_incus("info", name)


def start_instance(name: str) -> str:
    require_managed(name)
    run_incus("start", name)
    return inspect_instance(name)


def stop_instance(name: str) -> str:
    require_managed(name)
    run_incus("stop", name)
    return inspect_instance(name)


def destroy_instance(name: str) -> None:
    require_managed(name)
    run_incus("delete", "--force", name)