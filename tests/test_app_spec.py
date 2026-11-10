"""Tests for application specification loading."""

import pytest

from vortex.apps.spec import (
    ApplicationSpecError,
    load_application_spec,
)


def create_spec(tmp_path, content):
    app_directory = tmp_path / "sample-app"
    app_directory.mkdir(exist_ok=True)

    (app_directory / "app.py").write_text(
        "print('Vortex test application')\n",
        encoding="utf-8",
    )

    spec_file = tmp_path / "application.yaml"
    spec_file.write_text(content, encoding="utf-8")

    return spec_file


def test_load_valid_application_spec(tmp_path):

    spec_file = create_spec(
        tmp_path,
        """
name: sample-app

source: ./sample-app

command:
  - python3
  - app.py

timeout_seconds: 30
expected_exit_code: 0
repetitions: 3

discovery:
  cpu: true
  memory: true
""",
    )

    spec = load_application_spec(str(spec_file))

    assert spec["name"] == "sample-app"
    assert spec["command"] == ["python3", "app.py"]
    assert spec["timeout_seconds"] == 30
    assert spec["repetitions"] == 3
    assert spec["discovery"]["cpu"] is True
    assert spec["discovery"]["memory"] is True


def test_source_path_is_resolved(tmp_path):

    spec_file = create_spec(
        tmp_path,
        """
name: sample-app
source: ./sample-app
command:
  - python3
  - app.py
""",
    )

    spec = load_application_spec(str(spec_file))

    assert spec["source"] == str(
        (tmp_path / "sample-app").resolve()
    )


def test_rejects_missing_source(tmp_path):

    spec_file = tmp_path / "invalid.yaml"

    spec_file.write_text(
        """
name: missing-app
source: ./does-not-exist
command:
  - python3
  - app.py
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ApplicationSpecError,
        match="source does not exist",
    ):
        load_application_spec(str(spec_file))


def test_rejects_shell_command_string(tmp_path):

    spec_file = create_spec(
        tmp_path,
        """
name: sample-app
source: ./sample-app
command: python3 app.py
""",
    )

    with pytest.raises(
        ApplicationSpecError,
        match="list of argument strings",
    ):
        load_application_spec(str(spec_file))


def test_rejects_invalid_repetitions(tmp_path):

    spec_file = create_spec(
        tmp_path,
        """
name: sample-app
source: ./sample-app
command:
  - python3
  - app.py
repetitions: 50
""",
    )

    with pytest.raises(
        ApplicationSpecError,
        match="repetitions",
    ):
        load_application_spec(str(spec_file))


def test_rejects_disabled_discovery(tmp_path):

    spec_file = create_spec(
        tmp_path,
        """
name: sample-app
source: ./sample-app
command:
  - python3
  - app.py
discovery:
  cpu: false
  memory: false
""",
    )

    with pytest.raises(
        ApplicationSpecError,
        match="At least one resource",
    ):
        load_application_spec(str(spec_file))


def test_rejects_working_directory_escape(tmp_path):

    spec_file = create_spec(
        tmp_path,
        """
name: sample-app
source: ./sample-app
command:
  - python3
  - app.py
working_directory: ../
""",
    )

    with pytest.raises(
        ApplicationSpecError,
        match="inside the application source",
    ):
        load_application_spec(str(spec_file))