"""Scenario configuration loading and validation."""

from pathlib import Path

import yaml


class ScenarioError(ValueError):
    """Raised when a scenario is invalid."""


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
        raise ScenarioError(
            "Scenario must be a YAML mapping."
        )

    name = data.get("name")

    if not isinstance(name, str) or not name.strip():
        raise ScenarioError(
            "Scenario needs a non-empty name."
        )

    duration = data.get("duration_seconds")

    if type(duration) is not int or not 1 <= duration <= 3600:
        raise ScenarioError(
            "duration_seconds must be an integer from 1 to 3600."
        )

    network = data.get("network", {})

    if not isinstance(network, dict):
        raise ScenarioError(
            "network must be a mapping."
        )

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

    if (
        type(loss) not in (int, float)
        or not 0 <= loss <= 100
    ):
        raise ScenarioError(
            "packet_loss_percent must be a number from 0 to 100."
        )

    data["name"] = name.strip()
    data["network"] = {
        "latency_ms": latency,
        "packet_loss_percent": loss,
    }

    return data