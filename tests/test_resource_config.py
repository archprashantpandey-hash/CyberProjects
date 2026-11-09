"""Tests for scenario resource configuration."""

import pytest

from vortex.config import ScenarioError, load_scenario


def create_scenario(tmp_path, resources):
    path = tmp_path / "resource-test.yaml"

    path.write_text(
        "name: resource-test\n"
        "duration_seconds: 5\n"
        + resources,
        encoding="utf-8",
    )

    return path


def test_accepts_cpu_and_memory_limits(tmp_path):
    path = create_scenario(
        tmp_path,
        'resources:\n'
        '  cpu_percent: 25\n'
        '  memory_limit: "768MiB"\n',
    )

    scenario = load_scenario(str(path))

    assert scenario["resources"] == {
        "cpu_percent": 25,
        "memory_limit": "768MiB",
    }


def test_missing_resource_section_defaults_to_empty(tmp_path):
    path = create_scenario(tmp_path, "")

    scenario = load_scenario(str(path))

    assert scenario["resources"] == {}


@pytest.mark.parametrize("value", [0, 101, -1, True, 25.5])
def test_rejects_invalid_cpu_percentage(tmp_path, value):
    path = create_scenario(
        tmp_path,
        f"resources:\n  cpu_percent: {value}\n",
    )

    with pytest.raises(ScenarioError):
        load_scenario(str(path))


@pytest.mark.parametrize(
    "value",
    ["32MiB", "8GiB", "768MB", "invalid", "512MiB"],
)
def test_rejects_invalid_memory_limit(tmp_path, value):
    path = create_scenario(
        tmp_path,
        f'resources:\n  memory_limit: "{value}"\n',
    )

    if value == "512MiB":
        assert load_scenario(str(path))["resources"]["memory_limit"] == value
    else:
        with pytest.raises(ScenarioError):
            load_scenario(str(path))


def test_rejects_unknown_resource_option(tmp_path):
    path = create_scenario(
        tmp_path,
        "resources:\n  disk_percent: 50\n",
    )

    with pytest.raises(ScenarioError, match="Unsupported resource"):
        load_scenario(str(path))