"""Tests for controlled application runtime provisioning."""

import pytest

from vortex.apps import provisioner, runtime


def successful_result():
    return {
        "exit_code": 0,
        "stdout": "",
        "stderr": "",
        "timed_out": False,
        "duration_seconds": 1.0,
    }


def test_provisions_python_runtime(monkeypatch):

    calls = []

    def fake_exec(environment, command, **kwargs):
        calls.append((command, kwargs))
        return successful_result()

    monkeypatch.setattr(
        provisioner,
        "exec_instance",
        fake_exec,
    )

    result = provisioner.provision_runtime(
        "test-box",
        ["python3", "app.py"],
    )

    assert result["runtime"] == "Python 3"
    assert result["package"] == "python3"
    assert result["status"] == "INSTALLED"

    assert len(calls) == 3

    assert calls[1][0] == ["apt-get", "update"]

    assert calls[2][0] == [
        "env",
        "DEBIAN_FRONTEND=noninteractive",
        "apt-get",
        "install",
        "-y",
        "--no-install-recommends",
        "python3",
    ]

    # Provisioning operations execute as container root.
    assert all(
        "user" not in kwargs and "group" not in kwargs
        for _, kwargs in calls
    )


def test_rejects_unsupported_runtime():

    with pytest.raises(
        provisioner.RuntimeProvisioningError,
        match="not supported",
    ):
        provisioner.provision_runtime(
            "test-box",
            ["custom-program", "app"],
        )


def test_rejects_unapproved_package(monkeypatch):

    monkeypatch.setitem(
        runtime.RUNTIME_PROFILES["python3"],
        "package",
        "unapproved-package",
    )

    with pytest.raises(
        provisioner.RuntimeProvisioningError,
        match="not approved",
    ):
        provisioner.provision_runtime(
            "test-box",
            ["python3", "app.py"],
        )


def test_fails_when_apt_is_unavailable(monkeypatch):

    def fake_exec(environment, command, **kwargs):
        return {
            **successful_result(),
            "exit_code": 1,
        }

    monkeypatch.setattr(
        provisioner,
        "exec_instance",
        fake_exec,
    )

    with pytest.raises(
        provisioner.RuntimeProvisioningError,
        match="does not support apt-get",
    ):
        provisioner.provision_runtime(
            "test-box",
            ["python3", "app.py"],
        )


def test_stops_when_package_update_fails(monkeypatch):

    calls = []

    def fake_exec(environment, command, **kwargs):
        calls.append(command)

        if command == ["apt-get", "update"]:
            return {
                **successful_result(),
                "exit_code": 1,
                "stderr": "Network unavailable",
            }

        return successful_result()

    monkeypatch.setattr(
        provisioner,
        "exec_instance",
        fake_exec,
    )

    with pytest.raises(
        provisioner.RuntimeProvisioningError,
        match="Package index update failed",
    ):
        provisioner.provision_runtime(
            "test-box",
            ["python3", "app.py"],
        )

    assert len(calls) == 2


def test_rejects_timed_out_installation(monkeypatch):

    calls = []

    def fake_exec(environment, command, **kwargs):
        calls.append(command)

        if command[0] == "env":
            return {
                **successful_result(),
                "timed_out": True,
            }

        return successful_result()

    monkeypatch.setattr(
        provisioner,
        "exec_instance",
        fake_exec,
    )

    with pytest.raises(
        provisioner.RuntimeProvisioningError,
        match="timed out",
    ):
        provisioner.provision_runtime(
            "test-box",
            ["python3", "app.py"],
        )

    assert len(calls) == 3