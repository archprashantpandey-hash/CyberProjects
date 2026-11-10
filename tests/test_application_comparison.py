"""Tests for application resilience comparison."""

import pytest

from vortex.scenarios.application import (
    compare_application_phases,
)


def test_compares_average_execution_time():

    baseline = [
        {"status": "PASSED", "duration_seconds": 1.0},
        {"status": "PASSED", "duration_seconds": 1.5},
    ]

    chaos = [
        {"status": "PASSED", "duration_seconds": 2.0},
        {"status": "PASSED", "duration_seconds": 2.5},
    ]

    result = compare_application_phases(
        baseline,
        chaos,
    )

    assert result["baseline"]["average_duration_seconds"] == 1.25
    assert result["chaos"]["average_duration_seconds"] == 2.25

    assert result["average_duration_change_seconds"] == 1.0
    assert result["average_duration_change_percent"] == 80.0

    assert result["failure_outcome"] == "UNCHANGED"


def test_detects_new_failures_under_chaos():

    baseline = [
        {"status": "PASSED", "duration_seconds": 1.0},
        {"status": "PASSED", "duration_seconds": 1.0},
    ]

    chaos = [
        {"status": "PASSED", "duration_seconds": 1.2},
        {"status": "FAILED", "duration_seconds": 1.5},
    ]

    result = compare_application_phases(
        baseline,
        chaos,
    )

    assert result["baseline"]["failure_rate_percent"] == 0
    assert result["chaos"]["failure_rate_percent"] == 50

    assert result["failure_rate_change_percentage_points"] == 50
    assert result["failure_outcome"] == "REGRESSION"


def test_handles_zero_baseline_execution_time():

    baseline = [
        {"status": "PASSED", "duration_seconds": 0.0},
    ]

    chaos = [
        {"status": "PASSED", "duration_seconds": 0.2},
    ]

    result = compare_application_phases(
        baseline,
        chaos,
    )

    assert result["average_duration_change_seconds"] == 0.2

    # Percentage change is undefined when baseline is zero.
    assert result["average_duration_change_percent"] is None


def test_rejects_empty_phase_results():

    with pytest.raises(
        ValueError,
        match="Baseline execution results cannot be empty",
    ):
        compare_application_phases(
            [],
            [{"status": "PASSED", "duration_seconds": 1.0}],
        )