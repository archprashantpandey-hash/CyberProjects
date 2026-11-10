"""Application specification loading and validation."""

import re
from pathlib import Path

import yaml


class ApplicationSpecError(ValueError):
    """Raised when an application specification is invalid."""


NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,39}$")

ALLOWED_KEYS = {
    "name",
    "source",
    "command",
    "working_directory",
    "timeout_seconds",
    "expected_exit_code",
    "repetitions",
    "discovery",
}


def load_application_spec(path: str) -> dict:
    """Load and validate an application specification."""

    spec_file = Path(path).expanduser()

    try:
        with spec_file.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

    except FileNotFoundError as exc:
        raise ApplicationSpecError(
            f"Application specification not found: {path}"
        ) from exc

    except PermissionError as exc:
        raise ApplicationSpecError(
            f"Permission denied reading specification: {path}"
        ) from exc

    except UnicodeDecodeError as exc:
        raise ApplicationSpecError(
            "Specification must use UTF-8 encoding."
        ) from exc

    except yaml.YAMLError as exc:
        raise ApplicationSpecError(
            f"Invalid YAML: {exc}"
        ) from exc

    except OSError as exc:
        raise ApplicationSpecError(
            f"Could not read specification: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ApplicationSpecError(
            "Specification must be a YAML mapping."
        )

    unknown = set(data) - ALLOWED_KEYS

    if unknown:
        raise ApplicationSpecError(
            "Unsupported specification option(s): "
            + ", ".join(sorted(map(str, unknown)))
        )

    # Application name

    name = data.get("name")

    if (
        not isinstance(name, str)
        or not NAME_PATTERN.fullmatch(name)
    ):
        raise ApplicationSpecError(
            "name must contain lowercase letters, numbers "
            "and hyphens, and start with a letter."
        )

    # Application source

    source = data.get("source")

    if (
        not isinstance(source, str)
        or not source.strip()
        or "\x00" in source
    ):
        raise ApplicationSpecError(
            "source must be a valid file or directory path."
        )

    spec_directory = spec_file.resolve().parent
    source_candidate = Path(source).expanduser()

    if not source_candidate.is_absolute():
        source_candidate = spec_directory / source_candidate

    try:
        source_path = source_candidate.resolve(strict=True)

    except (FileNotFoundError, OSError) as exc:
        raise ApplicationSpecError(
            f"Application source does not exist: {source}"
        ) from exc

    if not source_path.is_file() and not source_path.is_dir():
        raise ApplicationSpecError(
            "Application source must be a file or directory."
        )

    # Working directory

    working_directory = data.get(
        "working_directory",
        ".",
    )

    if (
        not isinstance(working_directory, str)
        or not working_directory.strip()
    ):
        raise ApplicationSpecError(
            "working_directory must be a non-empty relative path."
        )

    relative_directory = Path(working_directory)

    if relative_directory.is_absolute():
        raise ApplicationSpecError(
            "working_directory must be relative to the application source."
        )

    source_root = (
        source_path if source_path.is_dir()
        else source_path.parent
    )

    try:
        resolved_working_directory = (
            source_root / relative_directory
        ).resolve(strict=True)

    except (FileNotFoundError, OSError) as exc:
        raise ApplicationSpecError(
            "Application working directory does not exist."
        ) from exc

    if (
        not resolved_working_directory.is_dir()
        or not resolved_working_directory.is_relative_to(source_root)
    ):
        raise ApplicationSpecError(
            "working_directory must remain inside the application source."
        )

    # Execution command

    command = data.get("command")

    if (
        not isinstance(command, list)
        or not 1 <= len(command) <= 32
        or any(
            not isinstance(part, str)
            or not part
            or "\x00" in part
            or len(part) > 4096
            for part in command
        )
    ):
        raise ApplicationSpecError(
            "command must be a non-empty list of argument strings. "
            "Do not provide a single shell command string."
        )

    # Execution timeout

    timeout = data.get("timeout_seconds", 30)

    if type(timeout) is not int or not 1 <= timeout <= 300:
        raise ApplicationSpecError(
            "timeout_seconds must be an integer from 1 to 300."
        )

    # Expected exit code

    expected_exit_code = data.get(
        "expected_exit_code",
        0,
    )

    if (
        type(expected_exit_code) is not int
        or not 0 <= expected_exit_code <= 255
    ):
        raise ApplicationSpecError(
            "expected_exit_code must be an integer from 0 to 255."
        )

    # Workload repetitions

    repetitions = data.get("repetitions", 3)

    if type(repetitions) is not int or not 1 <= repetitions <= 10:
        raise ApplicationSpecError(
            "repetitions must be an integer from 1 to 10."
        )

    # Resource discovery configuration

    discovery = data.get("discovery", {})

    if not isinstance(discovery, dict):
        raise ApplicationSpecError(
            "discovery must be a YAML mapping."
        )

    allowed_discovery_keys = {"cpu", "memory"}

    unknown_discovery = set(discovery) - allowed_discovery_keys

    if unknown_discovery:
        raise ApplicationSpecError(
            "Unsupported discovery option(s): "
            + ", ".join(sorted(map(str, unknown_discovery)))
        )

    cpu_enabled = discovery.get("cpu", True)
    memory_enabled = discovery.get("memory", True)

    if type(cpu_enabled) is not bool or type(memory_enabled) is not bool:
        raise ApplicationSpecError(
            "Discovery options cpu and memory must be true or false."
        )

    if not cpu_enabled and not memory_enabled:
        raise ApplicationSpecError(
            "At least one resource discovery option must be enabled."
        )

    return {
        "name": name,
        "source": str(source_path),
        "command": command,
        "working_directory": working_directory,
        "timeout_seconds": timeout,
        "expected_exit_code": expected_exit_code,
        "repetitions": repetitions,
        "discovery": {
            "cpu": cpu_enabled,
            "memory": memory_enabled,
        },
        "spec_path": str(spec_file.resolve()),
    }