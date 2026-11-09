"""Tests for CPU and memory resource management."""

import yaml

import vortex.chaos.resources as resources


def setup_resource_backend(monkeypatch):

    local = {
        "user.vortex.managed": "true",
        "limits.cpu.allowance": "100ms/100ms",
    }

    profile = {
        "limits.memory": "4GiB",
        "limits.memory.enforce": "hard",
    }

    def fake_run_incus(*args):

        if args[:2] == ("config", "show"):

            expanded = "--expanded" in args

            config = dict(profile) if expanded else {}

            config.update(local)

            return yaml.safe_dump({"config": config})

        if args[:2] == ("config", "set"):

            for argument in args[3:]:
                key, value = argument.split("=", 1)
                local[key] = value

            return ""

        if args[:2] == ("config", "unset"):

            local.pop(args[3], None)
            return ""

        raise AssertionError(f"Unexpected Incus call: {args}")

    monkeypatch.setattr(
        resources,
        "require_managed",
        lambda name: None,
    )

    monkeypatch.setattr(
        resources,
        "run_incus",
        fake_run_incus,
    )

    return local


def test_resource_limits_apply_and_restore(monkeypatch):

    local = setup_resource_backend(monkeypatch)

    resources_config = {
        "cpu_percent": 25,
        "memory_limit": "768MiB",
    }

    baseline = resources.capture_resource_baseline(
        "chaos-test",
        resources_config,
    )

    actual = resources.apply_resource_chaos(
        "chaos-test",
        resources_config,
    )

    assert actual["limits.cpu.allowance"] == "25ms/100ms"
    assert actual["limits.memory"] == "768MiB"
    assert actual["limits.memory.enforce"] == "hard"

    resources.restore_resource_baseline(
        "chaos-test",
        baseline,
    )

    restored = resources.verify_resource_restoration(
        "chaos-test",
        baseline,
    )

    assert restored["limits.cpu.allowance"] == "100ms/100ms"
    assert restored["limits.memory"] == "4GiB"

    assert local["limits.cpu.allowance"] == "100ms/100ms"
    assert "limits.memory" not in local
    assert "limits.memory.enforce" not in local


def test_invalid_cpu_limit_is_rejected():

    import pytest

    with pytest.raises(resources.IncusError):
        resources._expected_settings({
            "cpu_percent": 150,
        })


def test_invalid_memory_limit_is_rejected():

    import pytest

    with pytest.raises(resources.IncusError):
        resources._expected_settings({
            "memory_limit": "16MiB",
        })