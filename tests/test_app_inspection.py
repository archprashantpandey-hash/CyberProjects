"""Tests for application inspection."""

from vortex.apps.inspection import inspect_application_spec


def create_application(tmp_path, source_type="directory"):

    source = tmp_path / "sample-app"

    if source_type == "directory":
        source.mkdir()

        (source / "app.py").write_text(
            "print('Hello Vortex')",
            encoding="utf-8",
        )

    else:
        source.write_text(
            "print('Hello Vortex')",
            encoding="utf-8",
        )

    source_value = "./sample-app"

    spec_file = tmp_path / "application.yaml"

    spec_file.write_text(
        f"""
name: sample-app
source: {source_value}

command:
  - python3
  - app.py

working_directory: .
timeout_seconds: 30
expected_exit_code: 0
repetitions: 3

discovery:
  cpu: true
  memory: true
""",
        encoding="utf-8",
    )

    return spec_file, source


def test_inspect_directory_application(tmp_path):

    spec_file, source = create_application(tmp_path)

    result = inspect_application_spec(str(spec_file))

    assert result["Application"] == "sample-app"
    assert result["Source type"] == "Directory"
    assert result["Source path"] == str(source.resolve())
    assert result["Discovery targets"] == "CPU, MEMORY"


def test_inspect_single_file_application(tmp_path):

    spec_file, source = create_application(
        tmp_path,
        source_type="file",
    )

    result = inspect_application_spec(str(spec_file))

    assert result["Source type"] == "Single file"
    assert result["Source path"] == str(source.resolve())


def test_inspection_does_not_execute_application(tmp_path):

    spec_file, source = create_application(tmp_path)

    inspect_application_spec(str(spec_file))

    # Inspection must not modify the application.
    assert source.joinpath("app.py").read_text(
        encoding="utf-8"
    ) == "print('Hello Vortex')"
    