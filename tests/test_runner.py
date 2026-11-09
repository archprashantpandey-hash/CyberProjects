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

    assert durations == [5]


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