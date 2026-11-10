"""Tests for application security setup."""

import pytest

from vortex.apps import security


def test_application_user_setup(monkeypatch):

    calls = []

    def fake_exec(environment, command, **kwargs):

        calls.append((environment, command))

        return {
            "exit_code": 0,
            "stdout": "Application account verified.",
            "stderr": "",
            "timed_out": False,
        }

    monkeypatch.setattr(
        security,
        "exec_instance",
        fake_exec,
    )

    result = security.ensure_application_user("app-lab")

    script = calls[0][1][-1]

    assert result["username"] == "vortex-app"
    assert result["uid"] == 10001
    assert result["gid"] == 10001

    assert "groupadd --gid 10001" in script
    assert "useradd" in script
    assert "/usr/sbin/nologin" in script


def test_rejects_failed_account_setup(monkeypatch):

    monkeypatch.setattr(
        security,
        "exec_instance",
        lambda *args, **kwargs: {
            "exit_code": 1,
            "stdout": "",
            "stderr": "UID conflict",
            "timed_out": False,
        },
    )

    with pytest.raises(
        security.ApplicationSecurityError,
        match="UID conflict",
    ):
        security.ensure_application_user("app-lab")


def test_application_directory_permissions(monkeypatch):

    calls = []

    def fake_exec(environment, command, **kwargs):

        calls.append(command)

        return {
            "exit_code": 0,
            "stdout": (
                "10001:10001:750"
                if command[0] == "stat"
                else ""
            ),
            "stderr": "",
            "timed_out": False,
        }

    monkeypatch.setattr(
        security,
        "exec_instance",
        fake_exec,
    )

    result = security.secure_application_tree(
        "app-lab",
        "sample-app",
    )

    assert result["owner"] == "vortex-app"

    assert calls[0] == [
        "test",
        "-d",
        "/opt/vortex/apps/sample-app",
    ]

    assert calls[1][0] == "chown"
    assert calls[2][0] == "chmod"
    assert calls[3][0] == "stat"


def test_rejects_invalid_application_name(monkeypatch):

    monkeypatch.setattr(
        security,
        "exec_instance",
        lambda *args, **kwargs: pytest.fail(
            "Unexpected Incus operation"
        ),
    )

    with pytest.raises(
        security.ApplicationSecurityError,
        match="Invalid application name",
    ):
        security.secure_application_tree(
            "app-lab",
            "../unsafe",
        )