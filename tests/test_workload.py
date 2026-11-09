import vortex.scenarios.workload as workload


def test_successful_workload_check(monkeypatch):

    monkeypatch.setattr(
        workload,
        "exec_instance",
        lambda *args, **kwargs: {
            "exit_code": 0,
            "stdout": "healthy",
            "stderr": "",
            "timed_out": False,
            "duration_seconds": 0.1,
        },
    )

    results = workload.execute_workload_checks(
        "test-box",
        [{
            "name": "health",
            "command": ["/bin/true"],
            "timeout_seconds": 5,
            "expected_exit_code": 0,
        }],
        deadline=workload.time.monotonic() + 10,
    )

    assert results[0]["status"] == "PASSED"
    assert results[0]["exit_code"] == 0


def test_failed_workload_check(monkeypatch):

    monkeypatch.setattr(
        workload,
        "exec_instance",
        lambda *args, **kwargs: {
            "exit_code": 1,
            "stdout": "",
            "stderr": "failure",
            "timed_out": False,
            "duration_seconds": 0.1,
        },
    )

    results = workload.execute_workload_checks(
        "test-box",
        [{
            "name": "health",
            "command": ["/bin/false"],
            "timeout_seconds": 5,
            "expected_exit_code": 0,
        }],
        deadline=workload.time.monotonic() + 10,
    )

    assert results[0]["status"] == "FAILED"


def test_timed_out_command(monkeypatch):

    monkeypatch.setattr(
        workload,
        "exec_instance",
        lambda *args, **kwargs: {
            "exit_code": None,
            "stdout": "",
            "stderr": "timeout",
            "timed_out": True,
            "duration_seconds": 5,
        },
    )

    results = workload.execute_workload_checks(
        "test-box",
        [{
            "name": "slow-check",
            "command": ["/bin/sleep", "10"],
            "timeout_seconds": 5,
            "expected_exit_code": 0,
        }],
        deadline=workload.time.monotonic() + 10,
    )

    assert results[0]["status"] == "TIMEOUT"


def test_check_is_not_started_after_deadline(monkeypatch):

    calls = []

    monkeypatch.setattr(
        workload,
        "exec_instance",
        lambda *args, **kwargs: calls.append(args),
    )

    results = workload.execute_workload_checks(
        "test-box",
        [{
            "name": "late-check",
            "command": ["/bin/true"],
            "timeout_seconds": 5,
            "expected_exit_code": 0,
        }],
        deadline=workload.time.monotonic() - 1,
    )

    assert calls == []
    assert results[0]["status"] == "TIMEOUT"