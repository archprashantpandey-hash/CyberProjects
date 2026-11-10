"""Execute applications inside isolated Vortex environments."""

import time
from pathlib import PurePosixPath

from vortex.apps.security import (
    APPLICATION_GID,
    APPLICATION_UID,
    APPLICATION_USER,
    APPLICATION_ROOT,
)
from vortex.apps.spec import load_application_spec
from vortex.core.incus import exec_instance
from vortex.lifecycle.locks import environment_lock
from vortex.observe.recorder import EventRecorder
from vortex.apps.runtime import inspect_runtime
from vortex.apps.provisioner import provision_runtime


class ApplicationRunError(RuntimeError):
    """Raised when an application cannot be executed safely."""


def _checked_remote(
    environment: str,
    command: list[str],
    description: str,
) -> str:
    """Execute and validate a required remote check."""

    result = exec_instance(
        environment,
        command,
        timeout_seconds=10,
    )

    if result["timed_out"] or result["exit_code"] != 0:
        detail = (
            result.get("stderr")
            or result.get("stdout")
            or "operation failed"
        )

        raise ApplicationRunError(
            f"{description}: {detail.strip()}"
        )

    return result["stdout"].strip()


def run_application(
    specification: str,
    environment: str,
    *,
    provision_missing_runtime: bool = False,
) -> dict:
    """Execute an application according to its specification."""

    spec = load_application_spec(specification)

    application_root = (
        PurePosixPath(APPLICATION_ROOT) / spec["name"]
    )

    relative_working_directory = PurePosixPath(
        spec["working_directory"]
    )

    if (
        relative_working_directory.is_absolute()
        or ".." in relative_working_directory.parts
    ):
        raise ApplicationRunError(
            "Unsafe application working directory."
        )

    working_directory = (
        application_root / relative_working_directory
    )

    results = []
    started = time.monotonic()

    with environment_lock(environment):

        # Verify that the application is actually loaded.
        _checked_remote(
            environment,
            ["test", "-d", application_root.as_posix()],
            "Application is not loaded in this environment",
        )

        _checked_remote(
            environment,
            ["test", "-d", working_directory.as_posix()],
            "Application working directory is missing",
        )

        # Verify the dedicated application identity.
        uid = _checked_remote(
            environment,
            ["id", "-u", APPLICATION_USER],
            "Could not verify application UID",
        )

        gid = _checked_remote(
            environment,
            ["id", "-g", APPLICATION_USER],
            "Could not verify application GID",
        )

        if (
            uid != str(APPLICATION_UID)
            or gid != str(APPLICATION_GID)
        ):
            raise ApplicationRunError(
                "Application execution identity does not match "
                "the configured security identity."
            )

        ownership = _checked_remote(
            environment,
            [
                "stat",
                "-c",
                "%u:%g:%a",
                application_root.as_posix(),
            ],
            "Could not verify application directory ownership",
        )

        if ownership != (
            f"{APPLICATION_UID}:{APPLICATION_GID}:750"
        ):
            raise ApplicationRunError(
                "Application directory ownership or permissions "
                "have changed."
            )

        recorder = EventRecorder(environment)

        start_details = {
            "application": spec["name"],
            "command": spec["command"],
            "repetitions": spec["repetitions"],
            "timeout_seconds": spec["timeout_seconds"],
            "expected_exit_code": spec["expected_exit_code"],
            "execution_user": APPLICATION_USER,
            "execution_uid": APPLICATION_UID,
            "execution_gid": APPLICATION_GID,
        }

        recorder.record(
            "application_run_started",
            start_details,
        )

        runtime_info = None
        provisioning_info = None

        try:

            # Detect the required runtime.
            runtime_info = inspect_runtime(
                environment,
                spec["command"],
            )

            recorder.record(
                "application_runtime_detected",
                {
                    "application": spec["name"],
                    **runtime_info,
                },
            )

            # Handle missing runtimes.
            if not runtime_info["available"]:

                if not runtime_info["supported"]:
                    raise ApplicationRunError(
                        f"Executable '{runtime_info['executable']}' "
                        "is unavailable and cannot be automatically "
                        "provisioned."
                    )

                if not provision_missing_runtime:
                    raise ApplicationRunError(
                        f"Required runtime '{runtime_info['runtime']}' "
                        "is missing. Use --provision-runtime "
                        "to install it."
                    )

                # Explicitly authorised provisioning.
                provisioning_info = provision_runtime(
                    environment,
                    spec["command"],
                )

                recorder.record(
                    "application_runtime_provisioned",
                    {
                        "application": spec["name"],
                        **provisioning_info,
                    },
                )

                # Verify the actual installation.
                runtime_info = inspect_runtime(
                    environment,
                    spec["command"],
                )

                recorder.record(
                    "application_runtime_verified",
                    {
                        "application": spec["name"],
                        **runtime_info,
                    },
                )

                if not runtime_info["available"]:
                    raise ApplicationRunError(
                        "Runtime installation completed, but "
                        "runtime verification failed."
                    )

            # Keep the existing repetition loop immediately below.

            # Execute the application only after runtime verification.
            for repetition in range(
                1,
                spec["repetitions"] + 1,
            ):

                execution = exec_instance(
                    environment,
                    spec["command"],
                    timeout_seconds=spec["timeout_seconds"],
                    user=APPLICATION_UID,
                    group=APPLICATION_GID,
                    cwd=working_directory.as_posix(),
                )

                passed = (
                    not execution["timed_out"]
                    and execution["exit_code"]
                    == spec["expected_exit_code"]
                )

                result = {
                    "repetition": repetition,
                    "command": spec["command"],
                    "expected_exit_code": (
                        spec["expected_exit_code"]
                    ),
                    **execution,
                    "status": (
                        "PASSED" if passed else
                        "TIMEOUT" if execution["timed_out"] else
                        "FAILED"
                    ),
                }

                results.append(result)

                recorder.record(
                    "application_execution_completed",
                    {
                        "application": spec["name"],
                        **result,
                    },
                )

        except KeyboardInterrupt:

            recorder.record(
                "application_run_interrupted",
                {
                    "application": spec["name"],
                    "completed_repetitions": len(results),
                },
            )

            raise

        except Exception as error:

            recorder.record(
                "application_run_failed",
                {
                    "application": spec["name"],
                    "error": str(error),
                    "error_type": type(error).__name__,
                },
            )

            raise

        passed_count = sum(
            result["status"] == "PASSED"
            for result in results
        )

        failed_count = len(results) - passed_count

        summary = {
            "application": spec["name"],
            "environment": environment,
            "execution_user": APPLICATION_USER,
            "execution_uid": APPLICATION_UID,
            "execution_gid": APPLICATION_GID,
            "repetitions": len(results),
            "passed": passed_count,
            "failed": failed_count,
            "status": (
                "PASSED" if failed_count == 0 else "FAILED"
            ),
            "duration_seconds": round(
                time.monotonic() - started,
                3,
            ),
            "runtime": runtime_info["runtime"],
            "runtime_executable": runtime_info["executable"],
            "runtime_version": runtime_info["version"],
            "runtime_provisioned": provisioning_info is not None,
            "runtime_package": (
                provisioning_info["package"]
                if provisioning_info else None
            ),
            "runtime_provisioning_duration_seconds": (
                provisioning_info["total_duration_seconds"]
                if provisioning_info else 0
            ),
        }

        recorder.record(
            "application_run_finished",
            summary,
        )

        return {
            **summary,
            "command": spec["command"],
            "results": results,
        }