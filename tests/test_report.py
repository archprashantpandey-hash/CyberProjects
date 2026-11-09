"""Tests for Vortex experiment reports."""

import json

import pytest

from vortex.observe.report import generate_report
from vortex.core.incus import IncusError


def write_events(tmp_path, environment, events):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(exist_ok=True)

    log_path = reports_dir / f"{environment}.jsonl"
    log_path.write_text(
        "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )

    return log_path


def make_event(name, details=None, timestamp="2026-10-30T10:00:00+00:00"):
    return {
        "timestamp": timestamp,
        "environment": "test-box",
        "event": name,
        "details": details or {},
    }


def test_completed_experiment_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    write_events(
        tmp_path,
        "test-box",
        [
            make_event(
                "experiment_started",
                {"scenario": "test-network"},
            ),
            make_event(
                "network_chaos_applied",
                {
                    "latency_ms": 100,
                    "packet_loss_percent": 2,
                },
            ),
            make_event("experiment_duration_completed"),
            make_event("experiment_finished"),
        ],
    )

    report = generate_report("test-box")

    assert "Status:      COMPLETED" in report
    assert "Scenario:    test-network" in report
    assert "100 ms" in report
    assert "2%" in report
    assert (tmp_path / "reports" / "test-box-report.txt").is_file()


def test_failed_experiment_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    write_events(
        tmp_path,
        "test-box",
        [
            make_event(
                "experiment_started",
                {"scenario": "failure-test"},
            ),
            make_event(
                "experiment_failed",
                {"error": "simulated failure"},
            ),
        ],
    )

    report = generate_report("test-box")

    assert "Status:      FAILED" in report


def test_incomplete_experiment_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    write_events(
        tmp_path,
        "test-box",
        [
            make_event(
                "experiment_started",
                {"scenario": "interrupted-test"},
            ),
            make_event("network_chaos_applied", {"latency_ms": 50}),
        ],
    )

    report = generate_report("test-box")

    assert "Status:      INCOMPLETE" in report


def test_missing_event_log_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError, match="No event log found"):
        generate_report("missing-box")


def test_malformed_json_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "test-box.jsonl").write_text(
        '{"event": "experiment_started"}\nnot-json\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid JSON on line 2"):
        generate_report("test-box")


def test_report_uses_latest_experiment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    write_events(
        tmp_path,
        "test-box",
        [
            make_event(
                "experiment_started",
                {"scenario": "old-run"},
            ),
            make_event("experiment_duration_completed"),
            make_event(
                "experiment_started",
                {"scenario": "latest-run"},
            ),
        ],
    )

    report = generate_report("test-box")

    assert "Scenario:    latest-run" in report
    assert "old-run" not in report
    assert "Status:      INCOMPLETE" in report

def test_report_rejects_unsafe_environment_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    outside_log = tmp_path / "outside.jsonl"

    outside_log.write_text(
        json.dumps(
            make_event(
                "experiment_started",
                {"scenario": "path-test"},
            )
        ) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(IncusError, match="lowercase letters"):
        generate_report("../outside")

    assert not (tmp_path / "outside-report.txt").exists()