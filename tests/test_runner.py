"""Tests for the Vortex experiment runner."""

import pytest

import vortex.scenarios.runner as runner


@pytest.fixture
def setup_runner(monkeypatch):
    """Prepare an isolated experiment without calling Incus."""

    events = []
    calls = []

    scenario = {
        "name": "test-network",
        "duration_seconds": 5,
        "network": {
            "latency_ms": 100,
            "packet_loss_percent": 2,
        },
    }

    class FakeRecorder:
        def __init__(self, environment):
            self.environment = environment

        def record(self, event, details=None):
            events.append((event, details or {}))

    monkeypatch.setattr(runner, "load_scenario", lambda path: scenario)
    monkeypatch.setattr(runner, "require_managed", lambda name: None)
    monkeypatch.setattr(runner, "EventRecorder", FakeRecorder)
    monkeypatch.setattr(
        runner,
        "check_network_tools",
        lambda name: calls.append(("check", name)),
    )
    monkeypatch.setattr(
        runner,
        "apply_network_chaos",
        lambda name, latency, loss: calls.append(
            ("apply", name, latency, loss)
        ),
    )
    monkeypatch.setattr(
        runner,
        "remove_network_chaos",
        lambda name: calls.append(("remove", name)),
    )
    monkeypatch.setattr(runner.time, "sleep", lambda seconds: None)

    baseline = "qdisc noqueue 0: root refcnt 2"

    monkeypatch.setattr(
        runner,
        "verify_network_baseline",
        lambda name: baseline,
    )

    monkeypatch.setattr(
        runner,
        "verify_network_chaos",
        lambda name, latency, loss: (
            "qdisc netem root delay 100ms loss 2%"
        ),
    )

    monkeypatch.setattr(
        runner,
        "verify_network_cleanup",
        lambda name, expected_baseline: (
            "qdisc noqueue 0: root refcnt 2"
        ),
    )

    return events, calls


def test_successful_experiment_applies_and_cleans_up(setup_runner):
    events, calls = setup_runner

    runner.run_experiment("unused.yaml", "test-box")

    assert ("apply", "test-box", 100, 2) in calls
    assert ("remove", "test-box") in calls
    assert ("experiment_duration_completed", {}) in events
    assert ("experiment_finished", {}) in events


def test_experiment_uses_configured_duration(setup_runner, monkeypatch):
    events, calls = setup_runner
    durations = []

    monkeypatch.setattr(
        runner.time,
        "sleep",
        lambda seconds: durations.append(seconds),
    )

    runner.run_experiment("unused.yaml", "test-box")

    assert len(durations) == 1
    assert durations[0] == pytest.approx(5, abs=0.01)


def test_cleanup_is_attempted_when_chaos_application_fails(
    setup_runner, monkeypatch
):
    events, calls = setup_runner

    def fail_apply(name, latency, loss):
        raise RuntimeError("simulated application failure")

    monkeypatch.setattr(runner, "apply_network_chaos", fail_apply)

    with pytest.raises(
        RuntimeError, match="simulated application failure"
    ):
        runner.run_experiment("unused.yaml", "test-box")

    assert ("remove", "test-box") in calls
    assert any(event == "experiment_failed" for event, _ in events)
    assert any(event == "experiment_finished" for event, _ in events)


def test_cleanup_failure_is_reported(setup_runner, monkeypatch):
    events, calls = setup_runner

    def fail_cleanup(name):
        raise RuntimeError("simulated cleanup failure")

    monkeypatch.setattr(
        runner, "remove_network_chaos", fail_cleanup
    )

    with pytest.raises(
        RuntimeError, match="network cleanup could not be confirmed"
    ):
        runner.run_experiment("unused.yaml", "test-box")

    assert any(event == "cleanup_failed" for event, _ in events)


def test_zero_chaos_does_not_apply_or_remove_network_rules(
    setup_runner, monkeypatch
):
    events, calls = setup_runner

    scenario = {
        "name": "baseline",
        "duration_seconds": 1,
        "network": {
            "latency_ms": 0,
            "packet_loss_percent": 0,
        },
    }

    monkeypatch.setattr(runner, "load_scenario", lambda path: scenario)

    runner.run_experiment("unused.yaml", "test-box")

    assert not any(call[0] == "apply" for call in calls)
    assert not any(call[0] == "remove" for call in calls)
    assert ("experiment_duration_completed", {}) in events


def test_both_experiment_and_cleanup_failures_are_preserved(
    setup_runner, monkeypatch
):
    events, calls = setup_runner

    def fail_experiment(seconds):
        raise RuntimeError("simulated experiment failure")

    def fail_cleanup(name):
        raise RuntimeError("simulated cleanup failure")

    monkeypatch.setattr(runner.time, "sleep", fail_experiment)
    monkeypatch.setattr(
        runner, "remove_network_chaos", fail_cleanup
    )

    with pytest.raises(ExceptionGroup) as exc_info:
        runner.run_experiment("unused.yaml", "test-box")

    errors = [
        str(error) for error in exc_info.value.exceptions
    ]

    assert "simulated experiment failure" in errors
    assert "simulated cleanup failure" in errors

    event_names = [event for event, _ in events]

    assert "experiment_failed" in event_names
    assert "cleanup_failed" in event_names
    assert "experiment_finished" not in event_names

def test_verification_failure_still_triggers_cleanup(
    setup_runner, monkeypatch
):
    events, calls = setup_runner

    def fail_verification(name, latency, loss):
        raise RuntimeError("network verification failed")

    monkeypatch.setattr(
        runner,
        "verify_network_chaos",
        fail_verification,
    )

    with pytest.raises(
        RuntimeError,
        match="network verification failed",
    ):
        runner.run_experiment("unused.yaml", "test-box")

    assert ("remove", "test-box") in calls


def test_event_recording_failure_does_not_skip_cleanup(
    setup_runner, monkeypatch
):
    events, calls = setup_runner

    class BrokenRecorder:
        def __init__(self, environment):
            self.environment = environment

        def record(self, event, details=None):
            if event == "network_chaos_applied":
                raise OSError("simulated disk failure")

            events.append((event, details or {}))

    monkeypatch.setattr(
        runner,
        "EventRecorder",
        BrokenRecorder,
    )

    with pytest.raises(
        RuntimeError,
        match="could not be recorded",
    ):
        runner.run_experiment("unused.yaml", "test-box")

    assert ("remove", "test-box") in calls

def test_keyboard_interrupt_still_triggers_cleanup(
    setup_runner, monkeypatch
):
    events, calls = setup_runner

    def interrupt_experiment(seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(
        runner.time,
        "sleep",
        interrupt_experiment,
    )

    with pytest.raises(KeyboardInterrupt):
        runner.run_experiment("unused.yaml", "test-box")

    assert ("remove", "test-box") in calls

    event_names = [event for event, _ in events]

    assert "experiment_interrupted" in event_names
    assert "cleanup_failed" not in event_names

def test_unsupported_baseline_prevents_network_changes(
    setup_runner, monkeypatch
):
    events, calls = setup_runner

    def reject_baseline(name):
        raise RuntimeError("unsupported network baseline")

    monkeypatch.setattr(
        runner,
        "verify_network_baseline",
        reject_baseline,
    )

    with pytest.raises(
        RuntimeError,
        match="unsupported network baseline",
    ):
        runner.run_experiment("unused.yaml", "test-box")

    assert not any(call[0] == "apply" for call in calls)
    assert not any(call[0] == "remove" for call in calls)


def test_cleanup_receives_original_baseline(
    setup_runner, monkeypatch
):
    events, calls = setup_runner

    baseline = "qdisc noqueue 0: root refcnt 2"
    received = []

    monkeypatch.setattr(
        runner,
        "verify_network_baseline",
        lambda name: baseline,
    )

    monkeypatch.setattr(
        runner,
        "verify_network_cleanup",
        lambda name, expected_baseline: (
            received.append(expected_baseline)
            or "qdisc noqueue 0: root refcnt 2"
        ),
    )

    runner.run_experiment("unused.yaml", "test-box")

    assert received == [baseline]

@pytest.fixture
def setup_resource_runner(setup_runner, monkeypatch):
    """Prepare an experiment with CPU and memory restrictions."""

    events, calls = setup_runner
    lifecycle = []

    scenario = {
        "name": "resource-resilience",
        "duration_seconds": 5,
        "network": {
            "latency_ms": 100,
            "packet_loss_percent": 2,
        },
        "resources": {
            "cpu_percent": 25,
            "memory_limit": "768MiB",
        },
        "checks": [
            {
                "name": "health-check",
                "command": ["true"],
                "timeout_seconds": 2,
                "expected_exit_code": 0,
            }
        ],
    }

    baseline = {
        "keys": [
            "limits.cpu.allowance",
            "limits.memory",
            "limits.memory.enforce",
        ],
        "local": {},
        "effective": {
            "limits.cpu.allowance": "100ms/100ms",
            "limits.memory": "4GiB",
            "limits.memory.enforce": "hard",
        },
    }

    applied = {
        "limits.cpu.allowance": "25ms/100ms",
        "limits.memory": "768MiB",
        "limits.memory.enforce": "hard",
    }

    monkeypatch.setattr(
        runner,
        "load_scenario",
        lambda path: scenario,
    )

    def capture(name, config):
        lifecycle.append("capture")
        return baseline

    def apply(name, config):
        lifecycle.append("apply")
        return applied

    def restore(name, original):
        lifecycle.append("restore")

    def verify(name, original):
        lifecycle.append("verify_restoration")
        return original["effective"]

    def execute_checks(environment, checks, deadline):
        lifecycle.append("application_checks")
        return []

    monkeypatch.setattr(
        runner.resource_chaos,
        "capture_resource_baseline",
        capture,
    )

    monkeypatch.setattr(
        runner.resource_chaos,
        "apply_resource_chaos",
        apply,
    )

    monkeypatch.setattr(
        runner.resource_chaos,
        "restore_resource_baseline",
        restore,
    )

    monkeypatch.setattr(
        runner.resource_chaos,
        "verify_resource_restoration",
        verify,
    )

    monkeypatch.setattr(
        runner,
        "execute_workload_checks",
        execute_checks,
    )

    return events, calls, lifecycle

def test_resource_limits_apply_and_restore_on_success(
    setup_resource_runner,
):
    events, calls, lifecycle = setup_resource_runner

    runner.run_experiment("unused.yaml", "test-box")

    assert lifecycle == [
        "capture",
        "apply",
        "application_checks",
        "restore",
        "verify_restoration",
    ]

    event_names = [event for event, _ in events]

    assert "resource_chaos_verified" in event_names
    assert "resource_cleanup_verified" in event_names
    assert "experiment_finished" in event_names

def test_resources_restore_after_experiment_failure(
    setup_resource_runner,
    monkeypatch,
):
    events, calls, lifecycle = setup_resource_runner

    def fail_checks(environment, checks, deadline):
        lifecycle.append("application_checks")
        raise RuntimeError("simulated application failure")

    monkeypatch.setattr(
        runner,
        "execute_workload_checks",
        fail_checks,
    )

    with pytest.raises(
        RuntimeError,
        match="simulated application failure",
    ):
        runner.run_experiment("unused.yaml", "test-box")

    assert lifecycle == [
        "capture",
        "apply",
        "application_checks",
        "restore",
        "verify_restoration",
    ]

    event_names = [event for event, _ in events]

    assert "experiment_failed" in event_names
    assert "resource_cleanup_verified" in event_names
    assert "experiment_finished" in event_names

    assert ("remove", "test-box") in calls

def test_resources_restore_when_network_cleanup_fails(
    setup_resource_runner,
    monkeypatch,
):
    events, calls, lifecycle = setup_resource_runner

    def fail_network_cleanup(name):
        raise RuntimeError("simulated network cleanup failure")

    monkeypatch.setattr(
        runner,
        "remove_network_chaos",
        fail_network_cleanup,
    )

    with pytest.raises(
        RuntimeError,
        match="network cleanup could not be confirmed",
    ):
        runner.run_experiment("unused.yaml", "test-box")

    assert lifecycle == [
        "capture",
        "apply",
        "application_checks",
        "restore",
        "verify_restoration",
    ]

    event_names = [event for event, _ in events]

    assert "cleanup_failed" in event_names
    assert "resource_cleanup_verified" in event_names
    assert "experiment_finished" not in event_names

def test_resource_restoration_failure_is_reported(
    setup_resource_runner,
    monkeypatch,
):
    events, calls, lifecycle = setup_resource_runner

    def fail_restore(name, baseline):
        lifecycle.append("restore")
        raise RuntimeError("simulated resource restoration failure")

    monkeypatch.setattr(
        runner.resource_chaos,
        "restore_resource_baseline",
        fail_restore,
    )

    with pytest.raises(
        RuntimeError,
        match="resource cleanup could not be confirmed",
    ):
        runner.run_experiment("unused.yaml", "test-box")

    event_names = [event for event, _ in events]

    assert "resource_cleanup_failed" in event_names
    assert "resource_cleanup_verified" not in event_names
    assert "experiment_finished" not in event_names

def test_application_runs_before_and_during_chaos(
    setup_runner,
    monkeypatch,
):

    events, calls = setup_runner

    from contextlib import nullcontext

    scenario = {
        "name": "application-resilience",
        "duration_seconds": 5,
        "network": {
            "latency_ms": 100,
            "packet_loss_percent": 2,
        },
        "application": {
            "specification": "/tmp/application.yaml",
        },
    }

    application_spec = {
        "name": "sample-app",
        "command": ["python3", "app.py"],
        "working_directory": ".",
        "timeout_seconds": 30,
        "expected_exit_code": 0,
        "repetitions": 2,
    }

    monkeypatch.setattr(
        runner,
        "load_scenario",
        lambda path: scenario,
    )

    monkeypatch.setattr(
        runner,
        "load_application_spec",
        lambda path: application_spec,
    )

    monkeypatch.setattr(
        runner,
        "environment_lock",
        lambda environment: nullcontext(),
    )

    monkeypatch.setattr(
        runner,
        "_prepare_application_locked",
        lambda *args, **kwargs: {
            "working_directory": "/opt/vortex/apps/sample-app",
            "runtime_info": {
                "runtime": "Python 3",
                "executable": "python3",
                "available": True,
            },
            "provisioning_info": None,
        },
    )

    def execute_application(
        environment,
        spec,
        working_directory,
        recorder,
        *,
        phase=None,
        results=None,
    ):

        calls.append(("application", phase))

        status = (
            "PASSED" if phase == "baseline"
            else "FAILED"
        )

        return [
            {
                "repetition": 1,
                "status": status,
                "duration_seconds": 1.0,
                "phase": phase,
            },
            {
                "repetition": 2,
                "status": status,
                "duration_seconds": 1.2,
                "phase": phase,
            },
        ]

    monkeypatch.setattr(
        runner,
        "_execute_application_locked",
        execute_application,
    )

    runner.run_experiment(
        "unused.yaml",
        "test-box",
    )

    baseline_position = calls.index(
        ("application", "baseline")
    )

    chaos_position = calls.index(
        ("application", "chaos")
    )

    network_position = calls.index(
        ("apply", "test-box", 100, 2)
    )

    assert baseline_position < network_position
    assert network_position < chaos_position

    comparison_events = [
        details
        for event, details in events
        if event == "application_resilience_compared"
    ]

    assert len(comparison_events) == 1

    assert (
        comparison_events[0]["failure_outcome"]
        == "REGRESSION"
    )

def test_experiment_passes_explicit_provisioning_permission(
    setup_runner,
    monkeypatch,
):

    events, calls = setup_runner

    from contextlib import nullcontext

    scenario = {
        "name": "application-resilience",
        "duration_seconds": 5,
        "network": {
            "latency_ms": 0,
            "packet_loss_percent": 0,
        },
        "application": {
            "specification": "/tmp/application.yaml",
        },
    }

    application_spec = {
        "name": "sample-app",
        "command": ["python3", "app.py"],
        "working_directory": ".",
        "timeout_seconds": 30,
        "expected_exit_code": 0,
        "repetitions": 1,
    }

    provisioning_permissions = []

    monkeypatch.setattr(
        runner,
        "load_scenario",
        lambda path: scenario,
    )

    monkeypatch.setattr(
        runner,
        "load_application_spec",
        lambda path: application_spec,
    )

    monkeypatch.setattr(
        runner,
        "environment_lock",
        lambda environment: nullcontext(),
    )

    def prepare(environment, spec, recorder, **kwargs):

        provisioning_permissions.append(
            kwargs["provision_missing_runtime"]
        )

        return {
            "working_directory": "/opt/vortex/apps/sample-app",
        }

    monkeypatch.setattr(
        runner,
        "_prepare_application_locked",
        prepare,
    )

    monkeypatch.setattr(
        runner,
        "_execute_application_locked",
        lambda *args, **kwargs: [
            {
                "status": "PASSED",
                "duration_seconds": 1.0,
            }
        ],
    )

    runner.run_experiment(
        "unused.yaml",
        "test-box",
        provision_missing_runtime=True,
    )

    assert provisioning_permissions == [True]