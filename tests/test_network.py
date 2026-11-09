"""Tests for network chaos verification and safety."""

from unittest.mock import patch

import pytest

from vortex.core.incus import IncusError
from vortex.chaos.network import (
    apply_network_chaos,
    remove_network_chaos,
    verify_network_baseline,
    verify_network_chaos,
    verify_network_cleanup,
)


NOQUEUE = "qdisc noqueue 0: root refcnt 2"

NETEM = (
    "qdisc netem 8001: root refcnt 2 "
    "limit 1000 delay 300ms loss 5%"
)

FQ_CODEL = "qdisc fq_codel 0: root refcnt 2"


def test_network_baseline_accepts_noqueue():
    with patch(
        "vortex.chaos.network.inspect_network_qdisc",
        return_value=NOQUEUE,
    ):
        result = verify_network_baseline("chaos-test")

    assert result == NOQUEUE


def test_network_baseline_rejects_unsupported_qdisc():
    with patch(
        "vortex.chaos.network.inspect_network_qdisc",
        return_value=FQ_CODEL,
    ):
        with pytest.raises(
            IncusError,
            match="Refusing to overwrite",
        ):
            verify_network_baseline("chaos-test")


def test_apply_refuses_unsupported_baseline():
    with (
        patch(
            "vortex.chaos.network.require_managed"
        ),
        patch(
            "vortex.chaos.network.inspect_network_qdisc",
            return_value=FQ_CODEL,
        ),
        patch("vortex.chaos.network.run_incus") as run,
    ):
        with pytest.raises(IncusError, match="Unsafe network baseline"):
            apply_network_chaos("chaos-test", 300, 5)

    run.assert_not_called()


def test_network_chaos_verification_passes():
    with patch(
        "vortex.chaos.network.inspect_network_qdisc",
        return_value=NETEM,
    ):
        result = verify_network_chaos(
            "chaos-test",
            300,
            5,
        )

    assert "delay 300ms" in result
    assert "loss 5%" in result


def test_wrong_latency_is_rejected():
    output = "qdisc netem 8001: root delay 100ms loss 5%"

    with patch(
        "vortex.chaos.network.inspect_network_qdisc",
        return_value=output,
    ):
        with pytest.raises(
            IncusError,
            match="expected 300ms latency",
        ):
            verify_network_chaos("chaos-test", 300, 5)


def test_wrong_packet_loss_is_rejected():
    output = "qdisc netem 8001: root delay 300ms loss 2%"

    with patch(
        "vortex.chaos.network.inspect_network_qdisc",
        return_value=output,
    ):
        with pytest.raises(
            IncusError,
            match="expected 5% packet loss",
        ):
            verify_network_chaos("chaos-test", 300, 5)


def test_missing_netem_is_rejected():
    with patch(
        "vortex.chaos.network.inspect_network_qdisc",
        return_value=NOQUEUE,
    ):
        with pytest.raises(
            IncusError,
            match="netem is not active",
        ):
            verify_network_chaos("chaos-test", 300, 5)


def test_cleanup_verification_passes():
    with patch(
        "vortex.chaos.network.inspect_network_qdisc",
        return_value=NOQUEUE,
    ):
        result = verify_network_cleanup(
            "chaos-test",
            NOQUEUE,
        )

    assert "noqueue" in result


def test_cleanup_detects_remaining_netem():
    with patch(
        "vortex.chaos.network.inspect_network_qdisc",
        return_value=NETEM,
    ):
        with pytest.raises(
            IncusError,
            match="netem is still active",
        ):
            verify_network_cleanup("chaos-test", NOQUEUE)


def test_cleanup_detects_wrong_restored_qdisc():
    with patch(
        "vortex.chaos.network.inspect_network_qdisc",
        return_value=FQ_CODEL,
    ):
        with pytest.raises(
            IncusError,
            match="original root qdisc was not restored",
        ):
            verify_network_cleanup("chaos-test", NOQUEUE)


def test_remove_does_not_delete_non_netem_qdisc():
    with (
        patch("vortex.chaos.network.require_managed"),
        patch(
            "vortex.chaos.network.inspect_network_qdisc",
            return_value=FQ_CODEL,
        ),
        patch("vortex.chaos.network.run_incus") as run,
    ):
        remove_network_chaos("chaos-test")

    run.assert_not_called()


def test_remove_deletes_netem_qdisc():
    with (
        patch("vortex.chaos.network.require_managed"),
        patch(
            "vortex.chaos.network.inspect_network_qdisc",
            return_value=NETEM,
        ),
        patch("vortex.chaos.network.run_incus") as run,
    ):
        remove_network_chaos("chaos-test")

    run.assert_called_once_with(
        "exec",
        "chaos-test",
        "--",
        "tc",
        "qdisc",
        "del",
        "dev",
        "eth0",
        "root",
    )