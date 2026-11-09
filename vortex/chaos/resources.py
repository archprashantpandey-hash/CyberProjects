"""Controlled CPU and memory resource restrictions for Vortex."""

import re

import yaml

from vortex.core.incus import (
    IncusError,
    require_managed,
    run_incus,
)


CPU_KEY = "limits.cpu.allowance"
MEMORY_KEY = "limits.memory"
MEMORY_ENFORCE_KEY = "limits.memory.enforce"

MEMORY_PATTERN = re.compile(r"^([1-9][0-9]*)(MiB|GiB)$")

MIN_MEMORY = 64 * 1024**2
MAX_MEMORY = 4 * 1024**3


def _read_config(name: str, expanded: bool = False) -> dict:
    """Read local or expanded Incus configuration."""

    args = ["config", "show", name]

    if expanded:
        args.append("--expanded")

    try:
        document = yaml.safe_load(run_incus(*args)) or {}
    except yaml.YAMLError as exc:
        raise IncusError(
            "Could not parse Incus configuration."
        ) from exc

    config = document.get("config", {})

    if not isinstance(config, dict):
        raise IncusError(
            "Invalid Incus configuration structure."
        )

    return config


def _memory_bytes(value: str) -> int:
    """Convert an accepted memory quantity into bytes."""

    match = MEMORY_PATTERN.fullmatch(value)

    if not match:
        raise IncusError(
            "Memory limit must use MiB or GiB units."
        )

    amount = int(match.group(1))
    unit = match.group(2)

    multiplier = (
        1024**2 if unit == "MiB" else 1024**3
    )

    result = amount * multiplier

    if not MIN_MEMORY <= result <= MAX_MEMORY:
        raise IncusError(
            "Memory limit must be between 64MiB and 4GiB."
        )

    return result


def _expected_settings(resources: dict) -> dict:
    """Translate scenario resource settings into Incus options."""

    settings = {}

    cpu = resources.get("cpu_percent")

    if cpu is not None:
        if type(cpu) is not int or not 1 <= cpu <= 100:
            raise IncusError(
                "CPU percentage must be between 1 and 100."
            )

        settings[CPU_KEY] = f"{cpu}ms/100ms"

    memory = resources.get("memory_limit")

    if memory is not None:
        if not isinstance(memory, str):
            raise IncusError("Invalid memory limit.")

        _memory_bytes(memory)

        settings[MEMORY_KEY] = memory
        settings[MEMORY_ENFORCE_KEY] = "hard"

    if not settings:
        raise IncusError(
            "No CPU or memory restrictions were requested."
        )

    return settings


def capture_resource_baseline(
    name: str,
    resources: dict,
) -> dict:
    """Capture original resource settings before experimentation."""

    require_managed(name)

    expected = _expected_settings(resources)
    keys = list(expected)

    local = _read_config(name)
    expanded = _read_config(name, expanded=True)

    return {
        "keys": keys,
        "local": {
            key: local[key]
            for key in keys
            if key in local
        },
        "effective": {
            key: expanded.get(key)
            for key in keys
        },
    }


def apply_resource_chaos(
    name: str,
    resources: dict,
) -> dict:
    """Apply CPU and memory restrictions to a managed container."""

    require_managed(name)

    settings = _expected_settings(resources)

    arguments = [
        f"{key}={value}"
        for key, value in settings.items()
    ]

    run_incus(
        "config",
        "set",
        name,
        *arguments,
    )

    return verify_resource_chaos(name, resources)


def verify_resource_chaos(
    name: str,
    resources: dict,
) -> dict:
    """Verify the effective resource configuration."""

    require_managed(name)

    expected = _expected_settings(resources)
    actual = _read_config(name, expanded=True)

    for key, value in expected.items():
        if str(actual.get(key, "")) != str(value):
            raise IncusError(
                f"Resource verification failed for {key}: "
                f"expected {value}, got {actual.get(key)}."
            )

    return {
        key: actual[key]
        for key in expected
    }


def restore_resource_baseline(
    name: str,
    baseline: dict,
) -> None:
    """Restore original local settings and profile inheritance."""

    require_managed(name)

    original_local = baseline["local"]
    current_local = _read_config(name)

    errors = []

    for key in baseline["keys"]:

        try:
            if key in original_local:

                original_value = original_local[key]

                if current_local.get(key) != original_value:
                    run_incus(
                        "config",
                        "set",
                        name,
                        f"{key}={original_value}",
                    )

            elif key in current_local:

                run_incus(
                    "config",
                    "unset",
                    name,
                    key,
                )

        except Exception as exc:
            errors.append(f"{key}: {exc}")

    if errors:
        raise IncusError(
            "Some resource settings could not be restored: "
            + "; ".join(errors)
        )


def verify_resource_restoration(
    name: str,
    baseline: dict,
) -> dict:
    """Verify that effective resource settings match the baseline."""

    require_managed(name)

    actual = _read_config(name, expanded=True)
    expected = baseline["effective"]

    differences = []

    for key in baseline["keys"]:

        if actual.get(key) != expected.get(key):
            differences.append(
                f"{key}: expected {expected.get(key)}, "
                f"got {actual.get(key)}"
            )

    if differences:
        raise IncusError(
            "Resource restoration verification failed: "
            + "; ".join(differences)
        )

    return {
        key: actual.get(key)
        for key in baseline["keys"]
    }