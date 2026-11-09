"""TTL parsing and expiration utilities."""

import math
import re

from datetime import datetime, timedelta, timezone


TTL_PATTERN = re.compile(r"^([1-9]\d*)([smhd])$")

UNIT_SECONDS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
}

MAX_TTL_SECONDS = 365 * 86400


def utc_now():
    return datetime.now(timezone.utc)


def parse_ttl(value):
    """Convert values such as 30m, 2h or 1d into seconds."""

    if value is None:
        return None

    match = TTL_PATTERN.fullmatch(value.strip())

    if not match:
        raise ValueError(
            "Invalid TTL. Use formats such as 30s, 30m, 2h or 1d."
        )

    amount = int(match.group(1))
    unit = match.group(2)

    seconds = amount * UNIT_SECONDS[unit]

    if seconds > MAX_TTL_SECONDS:
        raise ValueError("Maximum supported TTL is 365 days.")

    return seconds


def expiration_from_ttl(ttl_seconds, now=None):
    """Calculate a persistent UTC expiration timestamp."""

    if ttl_seconds is None:
        return None

    if (
        not isinstance(ttl_seconds, int)
        or isinstance(ttl_seconds, bool)
        or not 1 <= ttl_seconds <= MAX_TTL_SECONDS
    ):
        raise ValueError("TTL must be between 1 second and 365 days.")

    current = now or utc_now()

    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    expiration = current.astimezone(timezone.utc) + timedelta(
        seconds=ttl_seconds
    )

    return expiration.isoformat(timespec="seconds")


def parse_expiration(value):
    """Parse a stored expiration timestamp."""

    if not value:
        return None

    try:
        expiration = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            f"Invalid expiration timestamp: {value}"
        ) from exc

    if expiration.tzinfo is None:
        expiration = expiration.replace(tzinfo=timezone.utc)

    return expiration.astimezone(timezone.utc)


def is_expired(value, now=None):
    """Check whether an expiration timestamp has passed."""

    expiration = parse_expiration(value)

    if expiration is None:
        return False

    current = now or utc_now()

    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    return expiration <= current.astimezone(timezone.utc)


def format_remaining(value, now=None):
    """Format the remaining lifetime for CLI display."""

    if not value:
        return "No expiry"

    expiration = parse_expiration(value)

    current = now or utc_now()

    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    seconds = math.ceil(
        (expiration - current.astimezone(timezone.utc)).total_seconds()
    )

    if seconds <= 0:
        return "EXPIRED"

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    if seconds and not days:
        parts.append(f"{seconds}s")

    return " ".join(parts)