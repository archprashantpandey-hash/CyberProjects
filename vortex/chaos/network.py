"""Network chaos controls confined to Incus containers."""

import re

from vortex.core.incus import (
    IncusError,
    require_managed,
    run_incus,
)


def check_network_tools(name: str) -> None:
    """Verify that the container has the tc utility."""
    require_managed(name)
    run_incus("exec", name, "--", "tc", "-V")


def inspect_network_qdisc(name: str) -> str:
    """Retrieve the actual network queuing configuration."""
    require_managed(name)

    return run_incus(
        "exec", name, "--",
        "tc", "qdisc", "show", "dev", "eth0",
    )


def _root_qdisc_line(output: str) -> str:
    """Find exactly one root qdisc in tc output."""

    root_lines = [
        line.strip()
        for line in output.splitlines()
        if re.match(r"^\s*qdisc\s+", line)
        and re.search(r"\broot(?:\s|$)", line)
    ]

    if len(root_lines) != 1:
        raise IncusError(
            "Could not safely identify exactly one root qdisc. "
            f"Actual configuration: {output}"
        )

    return root_lines[0]


def _qdisc_identity(line: str) -> tuple[str, str]:
    """Extract the qdisc type and handle from a root qdisc line."""

    match = re.match(
        r"^qdisc\s+(\S+)\s+(\S+):\s+root(?:\s|$)",
        line,
    )

    if not match:
        raise IncusError(
            f"Could not understand root qdisc configuration: {line}"
        )

    return match.group(1), match.group(2)


def verify_network_baseline(name: str) -> str:
    """Allow experiments only with the supported original baseline."""

    output = inspect_network_qdisc(name)
    root_line = _root_qdisc_line(output)

    qdisc_type, _ = _qdisc_identity(root_line)

    if qdisc_type != "noqueue":
        raise IncusError(
            "Unsafe network baseline: expected root qdisc "
            f"'noqueue', found '{root_line}'. "
            "Refusing to overwrite existing network configuration."
        )

    return root_line


def apply_network_chaos(
    name: str,
    latency_ms: int,
    packet_loss_percent: float,
) -> None:
    """Apply network degradation inside a managed container."""

    require_managed(name)

    if latency_ms == 0 and packet_loss_percent == 0:
        return

    # Never replace an unfamiliar existing root qdisc.
    verify_network_baseline(name)

    args = [
        "exec", name, "--",
        "tc", "qdisc", "replace",
        "dev", "eth0", "root", "netem",
    ]

    if latency_ms > 0:
        args.extend(["delay", f"{latency_ms}ms"])

    if packet_loss_percent > 0:
        args.extend(["loss", f"{packet_loss_percent}%"])

    run_incus(*args)


def verify_network_chaos(
    name: str,
    latency_ms: int,
    packet_loss_percent: float,
) -> str:
    """Verify that requested network degradation is present."""

    output = inspect_network_qdisc(name)
    root_line = _root_qdisc_line(output)

    qdisc_type, _ = _qdisc_identity(root_line)

    if qdisc_type != "netem":
        raise IncusError(
            "Network verification failed: netem is not active "
            f"on the root qdisc. Actual: {output}"
        )

    if latency_ms > 0:
        delay_pattern = (
            rf"\bdelay\s+{latency_ms}(?:\.0+)?ms(?:\s|$)"
        )

        if not re.search(delay_pattern, root_line):
            raise IncusError(
                f"Network verification failed: expected "
                f"{latency_ms}ms latency. Actual: {output}"
            )

    if packet_loss_percent > 0:
        loss_value = format(packet_loss_percent, "g")

        loss_pattern = (
            rf"\bloss\s+{re.escape(loss_value)}"
            rf"(?:\.0+)?%(?:\s|$)"
        )

        if not re.search(loss_pattern, root_line):
            raise IncusError(
                f"Network verification failed: expected "
                f"{loss_value}% packet loss. Actual: {output}"
            )

    return output


def remove_network_chaos(name: str) -> None:
    """Remove Vortex netem without deleting unrelated qdiscs."""

    require_managed(name)

    output = inspect_network_qdisc(name)
    root_line = _root_qdisc_line(output)

    qdisc_type, _ = _qdisc_identity(root_line)

    # Never delete a qdisc that Vortex did not install.
    if qdisc_type != "netem":
        return

    run_incus(
        "exec", name, "--",
        "tc", "qdisc", "del", "dev", "eth0", "root",
    )


def verify_network_cleanup(
    name: str,
    expected_baseline: str,
) -> str:
    """Confirm that the original root qdisc has been restored."""

    output = inspect_network_qdisc(name)
    actual_root = _root_qdisc_line(output)

    expected_identity = _qdisc_identity(expected_baseline)
    actual_identity = _qdisc_identity(actual_root)

    if actual_identity[0] == "netem":
        raise IncusError(
            "Network cleanup verification failed: "
            f"netem is still active. Actual: {output}"
        )

    if actual_identity != expected_identity:
        raise IncusError(
            "Network cleanup verification failed: "
            "original root qdisc was not restored. "
            f"Expected: {expected_baseline}. "
            f"Actual: {actual_root}"
        )

    return output