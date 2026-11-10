"""Tests for application runtime detection."""

from vortex.apps import runtime


def test_identifies_python_runtime():
    result = runtime.identify_runtime(
        ["python3", "app.py"]
    )

    assert result["name"] == "Python 3"
    assert result["package"] == "python3"


def test_identifies_node_runtime():
    result = runtime.identify_runtime(
        ["node", "app.js"]
    )

    assert result["name"] == "Node.js"
    assert result["package"] == "nodejs"


def test_unknown_runtime_is_not_auto_managed():
    result = runtime.identify_runtime(
        ["custom-program", "app"]
    )

    assert result is None


def test_detects_installed_python(monkeypatch):
    calls = []

    def fake_exec(environment, command, **kwargs):
        calls.append((command, kwargs))

        if command[1] == "-c":
            return {
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "timed_out": False,
            }

        return {
            "exit_code": 0,
            "stdout": "Python 3.11.2",
            "stderr": "",
            "timed_out": False,
        }

    monkeypatch.setattr(
        runtime,
        "exec_instance",
        fake_exec,
    )

    result = runtime.inspect_runtime(
        "app-lab3",
        ["python3", "app.py"],
    )

    assert result["available"] is True
    assert result["supported"] is True
    assert result["version"] == "Python 3.11.2"

    assert calls[0][1]["user"] == 10001
    assert calls[0][1]["group"] == 10001


def test_detects_missing_runtime(monkeypatch):
    def fake_exec(environment, command, **kwargs):
        return {
            "exit_code": 1,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
        }

    monkeypatch.setattr(
        runtime,
        "exec_instance",
        fake_exec,
    )

    result = runtime.inspect_runtime(
        "fresh-environment",
        ["node", "app.js"],
    )

    assert result["available"] is False
    assert result["supported"] is True
    assert result["version"] is None