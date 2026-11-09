"""Scenario configuration loading and validation."""

import re
from pathlib import Path

import yaml


class ScenarioError(ValueError):
    """Raised when a scenario is invalid."""


CHECK_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")


def load_scenario(path: str) -> dict:
    """Load and validate a YAML scenario."""

    file_path = Path(path)

    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

    except FileNotFoundError as exc:
        raise ScenarioError(
            f"Scenario file not found: {path}"
        ) from exc

    except PermissionError as exc:
        raise ScenarioError(
            f"Permission denied reading scenario: {path}"
        ) from exc

    except UnicodeDecodeError as exc:
        raise ScenarioError(
            "Scenario file must use UTF-8 encoding."
        ) from exc

    except yaml.YAMLError as exc:
        raise ScenarioError(
            f"Invalid YAML: {exc}"
        ) from exc

    except OSError as exc:
        raise ScenarioError(
            f"Could not read scenario file: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ScenarioError("Scenario must be a YAML mapping.")

    name = data.get("name")

    if not isinstance(name, str) or not name.strip():
        raise ScenarioError("Scenario needs a non-empty name.")

    duration = data.get("duration_seconds")

    if type(duration) is not int or not 1 <= duration <= 3600:
        raise ScenarioError(
            "duration_seconds must be an integer from 1 to 3600."
        )

    network = data.get("network", {})

    if not isinstance(network, dict):
        raise ScenarioError("network must be a mapping.")

    allowed_network_keys = {
        "latency_ms",
        "packet_loss_percent",
    }

    unknown_keys = set(network) - allowed_network_keys

    if unknown_keys:
        raise ScenarioError(
            "Unsupported network option(s): "
            + ", ".join(sorted(map(str, unknown_keys)))
        )

    latency = network.get("latency_ms", 0)

    if type(latency) is not int or not 0 <= latency <= 5000:
        raise ScenarioError(
            "latency_ms must be an integer from 0 to 5000."
        )

    loss = network.get("packet_loss_percent", 0)

    if type(loss) not in (int, float) or not 0 <= loss <= 100:
        raise ScenarioError(
            "packet_loss_percent must be a number from 0 to 100."
        )

    # Validate CPU and memory resource restrictions.
    resources = data.get("resources", {})

    if not isinstance(resources, dict):
        raise ScenarioError("resources must be a YAML mapping.")

    allowed_resource_keys = {
        "cpu_percent",
        "memory_limit",
    }

    unknown_resources = set(resources) - allowed_resource_keys

    if unknown_resources:
        raise ScenarioError(
            "Unsupported resource option(s): "
            + ", ".join(sorted(map(str, unknown_resources)))
        )

    normalized_resources = {}

    cpu_percent = resources.get("cpu_percent")

    if cpu_percent is not None:
        if type(cpu_percent) is not int or not 1 <= cpu_percent <= 100:
            raise ScenarioError(
                "cpu_percent must be an integer from 1 to 100."
            )

        normalized_resources["cpu_percent"] = cpu_percent

    memory_limit = resources.get("memory_limit")

    if memory_limit is not None:
        if not isinstance(memory_limit, str):
            raise ScenarioError(
                "memory_limit must use MiB or GiB units."
            )

        match = re.fullmatch(
            r"([1-9][0-9]*)(MiB|GiB)",
            memory_limit,
        )

        if not match:
            raise ScenarioError(
                "memory_limit must use MiB or GiB units."
            )

        amount = int(match.group(1))

        multiplier = (
            1024 ** 2 if match.group(2) == "MiB"
            else 1024 ** 3
        )

        memory_bytes = amount * multiplier

        if not 64 * 1024**2 <= memory_bytes <= 4 * 1024**3:
            raise ScenarioError(
                "memory_limit must be between 64MiB and 4GiB."
            )

        normalized_resources["memory_limit"] = memory_limit

    # Validate application checks.
    checks = data.get("checks", [])

    if not isinstance(checks, list) or len(checks) > 20:
        raise ScenarioError(
            "checks must be a list containing at most 20 checks."
        )

    normalized_checks = []
    check_names = set()

    allowed_check_keys = {
        "name",
        "command",
        "timeout_seconds",
        "expected_exit_code",
    }

    for index, check in enumerate(checks, start=1):

        if not isinstance(check, dict):
            raise ScenarioError(
                f"Check {index} must be a YAML mapping."
            )

        unknown = set(check) - allowed_check_keys

        if unknown:
            raise ScenarioError(
                f"Check {index} has unsupported option(s): "
                + ", ".join(sorted(map(str, unknown)))
            )

        check_name = check.get("name")

        if (
            not isinstance(check_name, str)
            or not CHECK_NAME_PATTERN.fullmatch(check_name)
        ):
            raise ScenarioError(
                f"Check {index} needs a valid name."
            )

        if check_name in check_names:
            raise ScenarioError(
                f"Duplicate application check name: {check_name}"
            )

        check_names.add(check_name)

        command = check.get("command")

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
            raise ScenarioError(
                f"Check '{check_name}' command must be a "
                "non-empty argument list of strings."
            )

        timeout = check.get("timeout_seconds", 10)

        if type(timeout) is not int or not 1 <= timeout <= 120:
            raise ScenarioError(
                f"Check '{check_name}' timeout_seconds "
                "must be an integer from 1 to 120."
            )

        expected = check.get("expected_exit_code", 0)

        if type(expected) is not int or not 0 <= expected <= 255:
            raise ScenarioError(
                f"Check '{check_name}' expected_exit_code "
                "must be an integer from 0 to 255."
            )

        normalized_checks.append({
            "name": check_name,
            "command": command,
            "timeout_seconds": timeout,
            "expected_exit_code": expected,
        })

    data["name"] = name.strip()

    data["network"] = {
        "latency_ms": latency,
        "packet_loss_percent": loss,
    }

    data["resources"] = normalized_resources
    data["checks"] = normalized_checks

    return data