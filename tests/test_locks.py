import pytest

from vortex.lifecycle.locks import (
    environment_lock,
    EnvironmentBusyError,
)


def test_environment_lock_prevents_concurrent_access():

    with environment_lock("lock-test"):

        with pytest.raises(EnvironmentBusyError):

            with environment_lock("lock-test"):
                pass


def test_environment_lock_releases_after_exit():

    with environment_lock("release-test"):
        pass

    with environment_lock("release-test"):
        pass