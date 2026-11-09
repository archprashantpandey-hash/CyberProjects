"""Cross-process environment operation locks."""

import fcntl
import os
import re
import tempfile

from contextlib import contextmanager
from pathlib import Path


NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,39}$")


class EnvironmentBusyError(RuntimeError):
    """Raised when another Vortex operation owns an environment."""


@contextmanager
def environment_lock(name):
    """Acquire a non-blocking lock for an environment.

    Linux releases flock locks automatically when the owning
    process exits, including after unexpected termination.
    """

    if not NAME_PATTERN.fullmatch(name):
        raise ValueError("Invalid environment name.")

    directory = (
        Path(tempfile.gettempdir())
        / f"vortex-locks-{os.getuid()}"
    )

    directory.mkdir(
        mode=0o700,
        parents=True,
        exist_ok=True,
    )

    os.chmod(directory, 0o700)

    lock_path = directory / f"{name}.lock"

    descriptor = os.open(
        lock_path,
        os.O_CREAT | os.O_RDWR,
        0o600,
    )

    try:
        try:
            fcntl.flock(
                descriptor,
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )

        except BlockingIOError as exc:
            raise EnvironmentBusyError(
                f"Environment '{name}' is currently being used "
                "by another Vortex operation."
            ) from exc

        yield

    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)