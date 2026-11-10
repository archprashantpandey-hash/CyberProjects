"""Security identity and permissions for application execution."""

import re

from vortex.core.incus import exec_instance


APPLICATION_USER = "vortex-app"
APPLICATION_GROUP = "vortex-app"

APPLICATION_UID = 10001
APPLICATION_GID = 10001

APPLICATION_ROOT = "/opt/vortex/apps"

APPLICATION_SHELL = "/usr/sbin/nologin"


class ApplicationSecurityError(RuntimeError):
    """Raised when application security setup fails."""


ACCOUNT_SETUP_SCRIPT = r"""
set -eu

# Check or create the dedicated group.

if getent group vortex-app >/dev/null 2>&1; then

    actual_gid=$(getent group vortex-app | cut -d: -f3)

    if [ "$actual_gid" != "10001" ]; then
        echo "The vortex-app group has an unexpected GID." >&2
        exit 1
    fi

elif getent group 10001 >/dev/null 2>&1; then

    echo "GID 10001 is already assigned to another group." >&2
    exit 1

else

    groupadd --gid 10001 vortex-app

fi

# Check or create the dedicated application user.

if getent passwd vortex-app >/dev/null 2>&1; then

    entry=$(getent passwd vortex-app)

    actual_uid=$(printf '%s\n' "$entry" | cut -d: -f3)
    actual_gid=$(printf '%s\n' "$entry" | cut -d: -f4)
    actual_home=$(printf '%s\n' "$entry" | cut -d: -f6)
    actual_shell=$(printf '%s\n' "$entry" | cut -d: -f7)

    [ "$actual_uid" = "10001" ] || {
        echo "Unexpected application UID." >&2
        exit 1
    }

    [ "$actual_gid" = "10001" ] || {
        echo "Unexpected application GID." >&2
        exit 1
    }

    [ "$actual_home" = "/nonexistent" ] || {
        echo "Unexpected application home directory." >&2
        exit 1
    }

    [ "$actual_shell" = "/usr/sbin/nologin" ] || {
        echo "Application account must use nologin." >&2
        exit 1
    }

elif getent passwd 10001 >/dev/null 2>&1; then

    echo "UID 10001 is already assigned to another user." >&2
    exit 1

else

    test -x /usr/sbin/nologin || {
        echo "nologin executable is unavailable." >&2
        exit 1
    }

    useradd \
        --uid 10001 \
        --gid 10001 \
        --home-dir /nonexistent \
        --no-create-home \
        --shell /usr/sbin/nologin \
        --comment "Vortex application account" \
        vortex-app

fi

# Verify the resulting identity and supplementary groups.

[ "$(id -u vortex-app)" = "10001" ]
[ "$(id -g vortex-app)" = "10001" ]
[ "$(id -G vortex-app)" = "10001" ]

echo "Application account verified."
"""


def _checked_exec(
    environment: str,
    command: list[str],
) -> str:
    """Execute a required administrative command as root."""

    result = exec_instance(
        environment,
        command,
        timeout_seconds=30,
    )

    if result["timed_out"] or result["exit_code"] != 0:

        detail = (
            result.get("stderr")
            or result.get("stdout")
            or "Unknown error"
        )

        raise ApplicationSecurityError(
            detail.strip()
        )

    return result.get("stdout", "").strip()


def ensure_application_user(environment: str) -> dict:
    """Create or verify the dedicated unprivileged account."""

    output = _checked_exec(
        environment,
        [
            "/bin/sh",
            "-eu",
            "-c",
            ACCOUNT_SETUP_SCRIPT,
        ],
    )

    return {
        "username": APPLICATION_USER,
        "uid": APPLICATION_UID,
        "group": APPLICATION_GROUP,
        "gid": APPLICATION_GID,
        "shell": APPLICATION_SHELL,
        "result": output,
    }


def secure_application_tree(
    environment: str,
    application_name: str,
) -> dict:
    """Assign application files exclusively to the application account."""

    if not re.fullmatch(
        r"[a-z][a-z0-9-]{0,39}",
        application_name,
    ):
        raise ApplicationSecurityError(
            "Invalid application name."
        )

    destination = (
        f"{APPLICATION_ROOT}/{application_name}"
    )

    _checked_exec(
        environment,
        ["test", "-d", destination],
    )

    _checked_exec(
        environment,
        [
            "chown",
            "-R",
            "-P",
            "--",
            f"{APPLICATION_UID}:{APPLICATION_GID}",
            destination,
        ],
    )

    _checked_exec(
        environment,
        [
            "chmod",
            "-R",
            "--",
            "u=rwX,g=rX,o=",
            destination,
        ],
    )

    ownership = _checked_exec(
        environment,
        [
            "stat",
            "-c",
            "%u:%g:%a",
            destination,
        ],
    )

    if not ownership.startswith("10001:10001:"):
        raise ApplicationSecurityError(
            "Application ownership verification failed."
        )

    return {
        "application": application_name,
        "owner": APPLICATION_USER,
        "uid": APPLICATION_UID,
        "gid": APPLICATION_GID,
        "ownership": ownership,
    }