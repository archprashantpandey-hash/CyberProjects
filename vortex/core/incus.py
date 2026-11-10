"""Incus backend for Vortex CLI."""

import json
import re
import shutil
import subprocess
import time

from vortex.lifecycle.locks import environment_lock
from vortex.lifecycle.ttl import (
    expiration_from_ttl,
    is_expired,
    utc_now,
)
from pathlib import Path, PurePosixPath


IMAGE = "images:debian/12"

MANAGED_KEY = "user.vortex.managed"
CREATED_AT_KEY = "user.vortex.created_at"
EXPIRES_AT_KEY = "user.vortex.expires_at"

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
        raise IncusError(
            f"Could not execute Incus: {exc}"
        ) from exc

    if result.returncode != 0:
        raise IncusError(
            result.stderr.strip() or "Incus command failed."
        )

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

    instances = json.loads(
        run_incus("list", "--format=json") or "[]"
    )

    return any(
        item.get("name") == name
        for item in instances
    )


def is_managed(name: str) -> bool:
    """Check whether Vortex owns an instance."""

    if not instance_exists(name):
        return False

    try:
        return (
            run_incus(
                "config",
                "get",
                name,
                MANAGED_KEY,
            ).lower()
            == "true"
        )

    except IncusError:
        return False


def require_managed(name: str) -> None:
    """Reject missing or unmanaged instances."""

    validate_name(name)

    if not instance_exists(name):
        raise IncusError(
            f"Environment '{name}' does not exist."
        )

    if not is_managed(name):
        raise IncusError(
            f"'{name}' is not Vortex-managed. "
            "Refusing to modify it."
        )


def _read_expiration(name: str):
    """Read stored expiration metadata."""

    value = run_incus(
        "config",
        "get",
        name,
        EXPIRES_AT_KEY,
    )

    return value.strip() or None


def get_instance_expiration(name: str):
    """Read expiration metadata from a managed instance."""

    require_managed(name)

    return _read_expiration(name)


def require_active_environment(name: str) -> None:
    """Reject expired environments before starting experiments."""

    require_managed(name)

    expiration = _read_expiration(name)

    if expiration:
        try:
            expired = is_expired(expiration)

        except ValueError as exc:
            raise IncusError(
                f"Environment '{name}' has invalid TTL metadata."
            ) from exc

        if expired:
            raise IncusError(
                f"Environment '{name}' has expired. "
                "Run 'vortex cleanup' to remove it."
            )


def create_instance(
    name: str,
    ttl_seconds: int | None = None,
) -> str:
    """Create a managed Debian container with optional TTL."""

    validate_name(name)

    # Validate TTL before creating anything.
    if ttl_seconds is not None:
        expiration_from_ttl(ttl_seconds)

    with environment_lock(name):

        if instance_exists(name):
            raise IncusError(
                f"Instance '{name}' already exists."
            )

        run_incus(
            "launch",
            IMAGE,
            name,
        )

        try:
            created_at = utc_now()

            expires_at = expiration_from_ttl(
                ttl_seconds,
                created_at,
            )

            run_incus(
                "config",
                "set",
                name,
                MANAGED_KEY,
                "true",
            )

            run_incus(
                "config",
                "set",
                name,
                CREATED_AT_KEY,
                created_at.isoformat(timespec="seconds"),
            )

            if expires_at:
                run_incus(
                    "config",
                    "set",
                    name,
                    EXPIRES_AT_KEY,
                    expires_at,
                )

        except Exception:

            try:
                run_incus(
                    "delete",
                    "--force",
                    name,
                )

            except IncusError:
                pass

            raise

        return run_incus("info", name)


def list_instances() -> list[dict]:
    """List Vortex-managed instances with expiration metadata."""

    instances = json.loads(
        run_incus("list", "--format=json") or "[]"
    )

    result = []

    for item in instances:

        name = item.get("name", "")

        if not name or not is_managed(name):
            continue

        expiration = _read_expiration(name)

        result.append({
            "name": name,
            "state": item.get("status", "UNKNOWN"),
            "type": item.get("type", "unknown"),
            "expires_at": expiration,
        })

    return result


def inspect_instance(name: str) -> str:
    require_managed(name)

    return run_incus("info", name)


def start_instance(name: str) -> str:

    with environment_lock(name):

        require_active_environment(name)

        run_incus("start", name)

        return inspect_instance(name)


def stop_instance(name: str) -> str:

    with environment_lock(name):

        require_managed(name)

        run_incus("stop", name)

        return inspect_instance(name)


def destroy_instance(
    name: str,
    *,
    lock_held: bool = False,
) -> None:
    """Delete only a Vortex-managed environment."""

    def perform_destroy():

        require_managed(name)

        run_incus(
            "delete",
            "--force",
            name,
        )

    if lock_held:
        perform_destroy()

    else:
        with environment_lock(name):
            perform_destroy()

def push_instance_path(
    name: str,
    source: str,
    target: str,
) -> None:
    """Safely transfer a local file or directory into a managed instance."""

    require_active_environment(name)

    try:
        source_path = Path(source).expanduser().resolve(strict=True)

    except OSError as exc:
        raise IncusError(
            f"Application source could not be accessed: {exc}"
        ) from exc

    if not source_path.is_file() and not source_path.is_dir():
        raise IncusError(
            "Application source must be a regular file or directory."
        )

    target_path = PurePosixPath(target)

    if (
        not target_path.is_absolute()
        or ".." in target_path.parts
        or target_path == PurePosixPath("/")
    ):
        raise IncusError(
            "Invalid application destination path."
        )

    arguments = [
        "file",
        "push",
        "--create-dirs",
    ]

    if source_path.is_dir():
        arguments.append("--recursive")

    arguments.extend([
        str(source_path),
        f"{name}/{target_path.as_posix().lstrip('/')}",
    ])

    run_incus(*arguments)

def _output_text(value) -> str:
    """Convert subprocess output into text."""

    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    return str(value)


def exec_instance(
    name: str,
    command: list[str],
    timeout_seconds: float = 10,
    *,
    user: int | None = None,
    group: int | None = None,
    cwd: str | None = None,
) -> dict:
    """Execute a command inside a managed container."""

    require_active_environment(name)

    if (
        not isinstance(command, list)
        or not command
        or any(
            not isinstance(part, str)
            or not part
            or "\x00" in part
            for part in command
        )
    ):
        raise IncusError("Invalid container command.")

    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not 0 < timeout_seconds <= 300
    ):
        raise IncusError("Invalid command timeout.")

    if (user is None) != (group is None):
        raise IncusError(
            "User and group must be specified together."
        )

    for label, value in (
        ("user", user),
        ("group", group),
    ):
        if value is not None and (
            type(value) is not int or value < 0
        ):
            raise IncusError(
                f"Invalid execution {label} ID."
            )

    if cwd is not None:

        if not isinstance(cwd, str) or "\x00" in cwd:
            raise IncusError("Invalid working directory.")

        cwd_path = PurePosixPath(cwd)

        if (
            not cwd_path.is_absolute()
            or ".." in cwd_path.parts
        ):
            raise IncusError(
                "Working directory must be an absolute safe path."
            )

    arguments = [
        INCUS,
        "exec",
        name,
    ]

    if user is not None:
        arguments.extend(["--user", str(user)])

    if group is not None:
        arguments.extend(["--group", str(group)])

    if cwd is not None:
        arguments.extend(["--cwd", cwd])

    arguments.extend([
        "--",
        *command,
    ])

    started = time.monotonic()

    try:
        result = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )

        return {
            "exit_code": result.returncode,
            "stdout": result.stdout[:4000],
            "stderr": result.stderr[:4000],
            "timed_out": False,
            "duration_seconds": round(
                time.monotonic() - started,
                3,
            ),
        }

    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": None,
            "stdout": _output_text(exc.stdout)[:4000],
            "stderr": _output_text(exc.stderr)[:4000],
            "timed_out": True,
            "duration_seconds": round(
                time.monotonic() - started,
                3,
            ),
        }

    except FileNotFoundError as exc:
        raise IncusError(
            "Incus executable could not be found."
        ) from exc
