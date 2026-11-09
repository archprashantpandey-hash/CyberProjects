"""Tests for Vortex scenario configuration."""

import pytest

from vortex.config import ScenarioError, load_scenario


def test_load_valid_scenario(tmp_path):
    scenario_file = tmp_path / "valid.yaml"

    scenario_file.write_text(
        """
name: test-network
description: Test scenario
network:
  latency_ms: 100
  packet_loss_percent: 2
duration_seconds: 5
""",
        encoding="utf-8",
    )

    scenario = load_scenario(str(scenario_file))

    assert scenario["name"] == "test-network"
    assert scenario["duration_seconds"] == 5
    assert scenario["network"]["latency_ms"] == 100
    assert scenario["network"]["packet_loss_percent"] == 2


def test_missing_scenario_file():
    with pytest.raises(ScenarioError, match="Scenario file not found"):
        load_scenario("this-file-does-not-exist.yaml")


def test_rejects_invalid_duration(tmp_path):
    scenario_file = tmp_path / "invalid-duration.yaml"

    scenario_file.write_text(
        """
name: invalid-duration
duration_seconds: 5000
network:
  latency_ms: 100
  packet_loss_percent: 2
""",
        encoding="utf-8",
    )

    with pytest.raises(ScenarioError, match="duration_seconds"):
        load_scenario(str(scenario_file))


def test_rejects_negative_latency(tmp_path):
    scenario_file = tmp_path / "negative-latency.yaml"

    scenario_file.write_text(
        """
name: negative-latency
duration_seconds: 5
network:
  latency_ms: -10
  packet_loss_percent: 0
""",
        encoding="utf-8",
    )

    with pytest.raises(ScenarioError, match="latency_ms"):
        load_scenario(str(scenario_file))


def test_rejects_packet_loss_above_100_percent(tmp_path):
    scenario_file = tmp_path / "invalid-loss.yaml"

    scenario_file.write_text(
        """
name: invalid-loss
duration_seconds: 5
network:
  latency_ms: 0
  packet_loss_percent: 101
""",
        encoding="utf-8",
    )

    with pytest.raises(ScenarioError, match="packet_loss_percent"):
        load_scenario(str(scenario_file))

def test_load_scenario_with_application_checks(tmp_path):

    scenario_file = tmp_path / "application.yaml"

    scenario_file.write_text(
        """
name: application-test
duration_seconds: 15

checks:
  - name: health
    command:
      - /bin/true
    timeout_seconds: 5
    expected_exit_code: 0
""",
        encoding="utf-8",
    )

    scenario = load_scenario(str(scenario_file))

    assert len(scenario["checks"]) == 1
    assert scenario["checks"][0]["name"] == "health"
    assert scenario["checks"][0]["expected_exit_code"] == 0


def test_scenario_without_checks_gets_empty_list(tmp_path):

    scenario_file = tmp_path / "basic.yaml"

    scenario_file.write_text(
        """
name: basic-test
duration_seconds: 5
""",
        encoding="utf-8",
    )

    scenario = load_scenario(str(scenario_file))

    assert scenario["checks"] == []


def test_rejects_invalid_check_command(tmp_path):

    scenario_file = tmp_path / "invalid-check.yaml"

    scenario_file.write_text(
        """
name: invalid-check
duration_seconds: 5

checks:
  - name: health
    command: "echo healthy"
""",
        encoding="utf-8",
    )

    with pytest.raises(ScenarioError, match="argument list"):
        load_scenario(str(scenario_file))


def test_rejects_invalid_check_timeout(tmp_path):

    scenario_file = tmp_path / "invalid-timeout.yaml"

    scenario_file.write_text(
        """
name: invalid-timeout
duration_seconds: 5

checks:
  - name: health
    command:
      - /bin/true
    timeout_seconds: 500
""",
        encoding="utf-8",
    )

    with pytest.raises(ScenarioError, match="timeout_seconds"):
        load_scenario(str(scenario_file))