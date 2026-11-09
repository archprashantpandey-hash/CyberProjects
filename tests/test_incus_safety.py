"""Security tests for Vortex environment management."""

from unittest.mock import patch

import pytest

from vortex.core.incus import (
    IncusError,
    require_managed,
    validate_name,
)


def test_invalid_name_is_rejected():
    with pytest.raises(IncusError):
        validate_name("../outside")


def test_uppercase_name_is_rejected():
    with pytest.raises(IncusError):
        validate_name("MyContainer")


def test_missing_environment_is_rejected():
    with patch(
        "vortex.core.incus.instance_exists",
        return_value=False,
    ):
        with pytest.raises(IncusError, match="does not exist"):
            require_managed("missing-test")


def test_unmanaged_environment_is_rejected():
    with (
        patch(
            "vortex.core.incus.instance_exists",
            return_value=True,
        ),
        patch(
            "vortex.core.incus.is_managed",
            return_value=False,
        ),
    ):
        with pytest.raises(IncusError, match="not Vortex-managed"):
            require_managed("external-test")


def test_managed_environment_passes_check():
    with (
        patch(
            "vortex.core.incus.instance_exists",
            return_value=True,
        ),
        patch(
            "vortex.core.incus.is_managed",
            return_value=True,
        ),
    ):
        require_managed("safe-test")