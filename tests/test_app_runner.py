"""Tests for application execution and runtime provisioning."""

from contextlib import nullcontext

import pytest

from vortex.apps import runner


def prepare_runner(monkeypatch):

    spec = {
        "name": "sample-app",
        "command": ["python3", "app.py"],
        "working_directory": ".",
        "timeout_seconds": 30,
        "expected_exit_code": 0,
        "repetitions": 2,
    }

    monkeypatch.setattr(
        runner,
        "load_application_spec",
        lambda path: spec,
    )

    monkeypatch.setattr(
        runner,
        "environment_lock",
        lambda environment: nullcontext(),
    )

    def checked_remote(environment, command, description):

        if command[:2] == ["id", "-u"]:
            return "10001"

        if command[:2] == ["id", "-g"]:
            return "10001"

        if command[0] == "stat":
            return "10001:10001:750"

        return ""

    monkeypatch.setattr(
        runner,
        "_checked_remote",
        checked_remote,
    )

    class FakeRecorder:

        instances = []

        def __init__(self, environment):
            self.events = []
            self.instances.append(self)

        def record(self, event, details=None):
            self.events.append((event, details or {}))

    monkeypatch.setattr(
        runner,
        "EventRecorder",
        FakeRecorder,
    )

    def fake_execution(environment, command, **kwargs):
        return {
            "exit_code": 0,
            "stdout": "Application completed.",
            "stderr": "",
            "timed_out": False,
            "duration_seconds": 0.1,
        }

    monkeypatch.setattr(
        runner,
        "exec_instance",
        fake_execution,
    )

    return FakeRecorder


def test_missing_runtime_requires_explicit_permission(monkeypatch):

    recorder = prepare_runner(monkeypatch)

    monkeypatch.setattr(
        runner,
        "inspect_runtime",
        lambda environment, command: {
            "runtime": "Python 3",
            "executable": "python3",
            "supported": True,
            "available": False,
            "version": None,
        },
    )

    def unexpected_provision(*args, **kwargs):
        pytest.fail("Provisioning must not happen without explicit permission")

    monkeypatch.setattr(
        runner,
        "provision_runtime",
        unexpected_provision,
    )

    with pytest.raises(
        runner.ApplicationRunError,
        match="--provision-runtime",
    ):
        runner.run_application(
            "application.yaml",
            "test-box",
        )

    events = recorder.instances[-1].events

    assert any(
        event == "application_run_failed"
        for event, details in events
    )


def test_provisions_and_verifies_missing_runtime(monkeypatch):

    recorder = prepare_runner(monkeypatch)

    runtime_results = iter([
        {
            "runtime": "Python 3",
            "executable": "python3",
            "supported": True,
            "available": False,
            "version": None,
        },
        {
            "runtime": "Python 3",
            "executable": "python3",
            "supported": True,
            "available": True,
            "version": "Python 3.11.2",
        },
    ])

    monkeypatch.setattr(
        runner,
        "inspect_runtime",
        lambda environment, command: next(runtime_results),
    )

    provisioning_calls = []

    def fake_provision(environment, command):
        provisioning_calls.append((environment, command))

        return {
            "runtime": "Python 3",
            "executable": "python3",
            "package": "python3",
            "status": "INSTALLED",
            "total_duration_seconds": 2.0,
        }

    monkeypatch.setattr(
        runner,
        "provision_runtime",
        fake_provision,
    )

    result = runner.run_application(
        "application.yaml",
        "test-box",
        provision_missing_runtime=True,
    )

    assert len(provisioning_calls) == 1
    assert result["runtime"] == "Python 3"
    assert result["runtime_version"] == "Python 3.11.2"
    assert result["runtime_provisioned"] is True
    assert result["runtime_package"] == "python3"
    assert result["passed"] == 2
    assert result["failed"] == 0

    events = recorder.instances[-1].events
    event_names = [event for event, details in events]

    assert "application_runtime_provisioned" in event_names
    assert "application_runtime_verified" in event_names
    assert "application_run_finished" in event_names


def test_unsupported_runtime_is_never_auto_provisioned(monkeypatch):

    recorder = prepare_runner(monkeypatch)

    monkeypatch.setattr(
        runner,
        "inspect_runtime",
        lambda environment, command: {
            "runtime": "Unmanaged executable",
            "executable": "custom-program",
            "supported": False,
            "available": False,
            "version": None,
        },
    )

    monkeypatch.setattr(
        runner,
        "provision_runtime",
        lambda *args, **kwargs: pytest.fail(
            "Unsupported runtime must not be provisioned."
        ),
    )

    with pytest.raises(
        runner.ApplicationRunError,
        match="cannot be automatically provisioned",
    ):
        runner.run_application(
            "application.yaml",
            "test-box",
            provision_missing_runtime=True,
        )
