"""Transfer applications into Vortex environments."""

import uuid
from pathlib import Path, PurePosixPath

from vortex.apps.spec import load_application_spec
from vortex.core.incus import (
    IncusError,
    exec_instance,
    push_instance_path,
)
from vortex.apps.security import (
    ensure_application_user,
    secure_application_tree,
)

APPLICATIONS_DIR = PurePosixPath("/opt/vortex/apps")


def _run_remote(
    environment: str,
    command: list[str],
    error_message: str,
) -> None:
    """Execute a required operation inside an environment."""

    result = exec_instance(
        environment,
        command,
        timeout_seconds=30,
    )

    if result["timed_out"] or result["exit_code"] != 0:
        detail = result.get("stderr") or result.get("stdout") or ""

        raise IncusError(
            f"{error_message}: {detail.strip() or 'operation failed'}"
        )


def load_application(
    specification: str,
    environment: str,
) -> dict:
    """Transfer an application into a managed Incus environment."""

    spec = load_application_spec(specification)

    source = Path(spec["source"])

    application_root = APPLICATIONS_DIR / spec["name"]

    # Never overwrite an existing application.
    _run_remote(
        environment,
        ["test", "!", "-e", application_root.as_posix()],
        "Application destination already exists or cannot be checked",
    )

    security_identity = ensure_application_user(environment)

    if source.is_dir():

        # Incus appends the source directory name during recursive push.
        # Use a temporary destination and move the directory afterward.
        staging_parent = (
            APPLICATIONS_DIR
            / f".vortex-upload-{uuid.uuid4().hex}"
        )

        staged_source = staging_parent / source.name

        push_instance_path(
            environment,
            str(source),
            staging_parent.as_posix(),
        )

        _run_remote(
            environment,
            [
                "mv",
                "--",
                staged_source.as_posix(),
                application_root.as_posix(),
            ],
            "Could not finalize application transfer",
        )

        # Remove the now-empty temporary directory.
        try:
            exec_instance(
                environment,
                ["rmdir", "--", staging_parent.as_posix()],
                timeout_seconds=10,
            )
        except Exception:
            pass

        destination = application_root

    else:

        destination = application_root / source.name

        push_instance_path(
            environment,
            str(source),
            destination.as_posix(),
        )

    working_directory = (
        application_root / spec["working_directory"]
    )

    security_result = secure_application_tree(
        environment,
        spec["name"],
    )

    return {
        "application": spec["name"],
        "environment": environment,
        "source": str(source),
        "destination": destination.as_posix(),
        "working_directory": working_directory.as_posix(),
        "command": spec["command"],
        "repetitions": spec["repetitions"],
        "execution_user": security_identity["username"],
        "execution_uid": security_identity["uid"],
        "execution_gid": security_identity["gid"],
        "security": "Verified",
    }