"""Tests for non-root Incus command execution."""

from types import SimpleNamespace

import pytest

from vortex.core import incus


def test_exec_instance_supports_non_root_identity(monkeypatch):

    monkeypatch.setattr(
        incus,
        "require_active_environment",
        lambda name: None,
    )

    calls = []

    def fake_run(arguments, **kwargs):
        calls.append(arguments)

        return SimpleNamespace(
            returncode=0,
            stdout="uid=10001",
            stderr="",
        )

    monkeypatch.setattr(
        incus.subprocess,
        "run",
        fake_run,
    )

    incus.exec_instance(
        "app-lab",
        ["id"],
        user=10001,
        group=10001,
        cwd="/opt/vortex/apps/sample-app",
    )

    assert calls[0] == [
        incus.INCUS,
        "exec",
        "app-lab",
        "--user",
        "10001",
        "--group",
        "10001",
        "--cwd",
        "/opt/vortex/apps/sample-app",
        "--",
        "id",
    ]


def test_identity_requires_user_and_group_together(monkeypatch):

    monkeypatch.setattr(
        incus,
        "require_active_environment",
        lambda name: None,
    )

    with pytest.raises(incus.IncusError, match="together"):

        incus.exec_instance(
            "app-lab",
            ["id"],
            user=10001,
        )


def test_rejects_unsafe_working_directory(monkeypatch):

    monkeypatch.setattr(
        incus,
        "require_active_environment",
        lambda name: None,
    )

    with pytest.raises(incus.IncusError, match="Working directory"):

        incus.exec_instance(
            "app-lab",
            ["id"],
            user=10001,
            group=10001,
            cwd="/opt/vortex/../etc",
        )