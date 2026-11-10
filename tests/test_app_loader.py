"""Tests for application loading."""

from uuid import UUID

import pytest

from vortex.apps import loader
from vortex.core import incus

def mock_application_security(monkeypatch):

    calls = []

    monkeypatch.setattr(
        loader,
        "ensure_application_user",
        lambda environment: {
            "username": "vortex-app",
            "uid": 10001,
            "gid": 10001,
        },
    )

    monkeypatch.setattr(
        loader,
        "secure_application_tree",
        lambda environment, name: calls.append(
            (environment, name)
        ),
    )

    return calls

def create_directory_spec(tmp_path):

    application = tmp_path / "sample-app"
    application.mkdir()

    (application / "app.py").write_text(
        "print('Hello Vortex')",
        encoding="utf-8",
    )

    specification = tmp_path / "application.yaml"

    specification.write_text(
        """
name: sample-app
source: ./sample-app

command:
  - python3
  - app.py

working_directory: .
repetitions: 3
""",
        encoding="utf-8",
    )

    return specification, application


def create_file_spec(tmp_path):

    application = tmp_path / "app.py"

    application.write_text(
        "print('Hello Vortex')",
        encoding="utf-8",
    )

    specification = tmp_path / "application.yaml"

    specification.write_text(
        """
name: sample-app
source: ./app.py

command:
  - python3
  - app.py
""",
        encoding="utf-8",
    )

    return specification, application


def mock_remote_success(monkeypatch):

    calls = []

    def fake_exec(environment, command, timeout_seconds=10):

        calls.append((environment, command))

        return {
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
            "duration_seconds": 0.01,
        }

    monkeypatch.setattr(loader, "exec_instance", fake_exec)

    return calls


def test_load_directory_application(tmp_path, monkeypatch):

    security_calls = mock_application_security(monkeypatch)

    specification, application = create_directory_spec(tmp_path)

    push_calls = []

    monkeypatch.setattr(
        loader,
        "push_instance_path",
        lambda *args: push_calls.append(args),
    )

    monkeypatch.setattr(
        loader.uuid,
        "uuid4",
        lambda: UUID(int=1),
    )

    remote_calls = mock_remote_success(monkeypatch)

    result = loader.load_application(
        str(specification),
        "app-lab",
    )

    staging = (
        "/opt/vortex/apps/"
        ".vortex-upload-00000000000000000000000000000001"
    )

    app_root = "/opt/vortex/apps/sample-app"

    assert push_calls == [
        (
            "app-lab",
            str(application.resolve()),
            staging,
        )
    ]

    assert remote_calls[0][1] == [
        "test", "!", "-e", app_root
    ]

    assert remote_calls[1][1] == [
        "mv",
        "--",
        f"{staging}/sample-app",
        app_root,
    ]

    assert result["destination"] == app_root
    assert result["working_directory"] == app_root
    assert security_calls == [("app-lab", "sample-app")]


def test_load_single_file_application(tmp_path, monkeypatch):

    security_calls = mock_application_security(monkeypatch)

    specification, application = create_file_spec(tmp_path)

    push_calls = []

    monkeypatch.setattr(
        loader,
        "push_instance_path",
        lambda *args: push_calls.append(args),
    )

    remote_calls = mock_remote_success(monkeypatch)

    result = loader.load_application(
        str(specification),
        "app-lab",
    )

    assert push_calls == [
        (
            "app-lab",
            str(application.resolve()),
            "/opt/vortex/apps/sample-app/app.py",
        )
    ]

    assert result["destination"].endswith("app.py")
    assert len(remote_calls) == 1
    assert security_calls == [("app-lab", "sample-app")]


def test_push_directory_uses_recursive_transfer(
    tmp_path,
    monkeypatch,
):

    source = tmp_path / "application"
    source.mkdir()

    calls = []

    monkeypatch.setattr(
        incus,
        "require_active_environment",
        lambda name: calls.append(("require", name)),
    )

    monkeypatch.setattr(
        incus,
        "run_incus",
        lambda *args: calls.append(args),
    )

    incus.push_instance_path(
        "app-lab",
        str(source),
        "/opt/vortex/apps/sample-app",
    )

    assert calls[0] == ("require", "app-lab")

    assert calls[1] == (
        "file",
        "push",
        "--create-dirs",
        "--recursive",
        str(source.resolve()),
        "app-lab/opt/vortex/apps/sample-app",
    )


def test_push_file_does_not_use_recursive_flag(
    tmp_path,
    monkeypatch,
):

    source = tmp_path / "app.py"
    source.write_text("print('test')", encoding="utf-8")

    calls = []

    monkeypatch.setattr(
        incus,
        "require_active_environment",
        lambda name: None,
    )

    monkeypatch.setattr(
        incus,
        "run_incus",
        lambda *args: calls.append(args),
    )

    incus.push_instance_path(
        "app-lab",
        str(source),
        "/opt/vortex/apps/sample-app/app.py",
    )

    assert "--recursive" not in calls[0]


def test_rejects_unsafe_destination(tmp_path, monkeypatch):

    source = tmp_path / "app.py"
    source.write_text("print('test')", encoding="utf-8")

    monkeypatch.setattr(
        incus,
        "require_active_environment",
        lambda name: None,
    )

    monkeypatch.setattr(
        incus,
        "run_incus",
        lambda *args: pytest.fail("Unexpected Incus operation"),
    )

    with pytest.raises(incus.IncusError, match="destination"):
        incus.push_instance_path(
            "app-lab",
            str(source),
            "/opt/vortex/../etc/test",
        )


def test_loader_rejects_existing_application(
    tmp_path,
    monkeypatch,
):

    specification, _ = create_file_spec(tmp_path)

    pushed = []

    monkeypatch.setattr(
        loader,
        "push_instance_path",
        lambda *args: pushed.append(args),
    )

    monkeypatch.setattr(
        loader,
        "exec_instance",
        lambda *args, **kwargs: {
            "exit_code": 1,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
        },
    )

    with pytest.raises(incus.IncusError, match="already exists"):

        loader.load_application(
            str(specification),
            "app-lab",
        )

    assert pushed == []