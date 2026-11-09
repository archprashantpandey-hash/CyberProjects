import pytest

from datetime import datetime, timedelta, timezone

from vortex.lifecycle.ttl import (
    parse_ttl,
    expiration_from_ttl,
    is_expired,
    format_remaining,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("30s", 30),
        ("30m", 1800),
        ("2h", 7200),
        ("1d", 86400),
    ],
)
def test_parse_ttl(value, expected):
    assert parse_ttl(value) == expected


def test_no_ttl_returns_none():
    assert parse_ttl(None) is None


@pytest.mark.parametrize(
    "value",
    [
        "0m",
        "-5m",
        "30",
        "5x",
        "abc",
        "400d",
    ],
)
def test_invalid_ttl_is_rejected(value):
    with pytest.raises(ValueError):
        parse_ttl(value)


def test_expiration_is_calculated_correctly():

    now = datetime(
        2026, 11, 9, 12, 0, 0,
        tzinfo=timezone.utc,
    )

    expiration = expiration_from_ttl(
        1800,
        now,
    )

    assert expiration == "2026-11-09T12:30:00+00:00"


def test_expired_environment_is_detected():

    now = datetime(
        2026, 11, 9, 12, 0, 0,
        tzinfo=timezone.utc,
    )

    expiration = (
        now - timedelta(minutes=5)
    ).isoformat()

    assert is_expired(expiration, now)


def test_active_environment_is_not_expired():

    now = datetime(
        2026, 11, 9, 12, 0, 0,
        tzinfo=timezone.utc,
    )

    expiration = (
        now + timedelta(minutes=30)
    ).isoformat()

    assert not is_expired(expiration, now)


def test_remaining_time_format():

    now = datetime(
        2026, 11, 9, 12, 0, 0,
        tzinfo=timezone.utc,
    )

    expiration = (
        now + timedelta(minutes=30)
    ).isoformat()

    assert format_remaining(
        expiration,
        now,
    ) == "30m"