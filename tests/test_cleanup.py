from datetime import datetime, timedelta, timezone

import vortex.lifecycle.cleanup as cleanup


NOW = datetime(
    2026, 11, 9, 12, 0, 0,
    tzinfo=timezone.utc,
)


def setup_cleanup(monkeypatch):

    expired = (
        NOW - timedelta(minutes=5)
    ).isoformat()

    active = (
        NOW + timedelta(minutes=30)
    ).isoformat()

    metadata = {
        "expired-box": expired,
        "active-box": active,
    }

    environments = [
        {
            "name": "expired-box",
            "expires_at": expired,
        },
        {
            "name": "active-box",
            "expires_at": active,
        },
    ]

    calls = []

    monkeypatch.setattr(
        cleanup,
        "list_instances",
        lambda: environments,
    )

    monkeypatch.setattr(
        cleanup,
        "get_instance_expiration",
        lambda name: metadata[name],
    )

    monkeypatch.setattr(
        cleanup,
        "destroy_instance",
        lambda name, lock_held=False: calls.append(
            (name, lock_held)
        ),
    )

    return calls


def test_cleanup_dry_run_does_not_delete(monkeypatch):

    calls = setup_cleanup(monkeypatch)

    results = cleanup.cleanup_expired_environments(
        dry_run=True,
        now=NOW,
    )

    assert calls == []

    assert len(results) == 1
    assert results[0]["name"] == "expired-box"
    assert results[0]["status"] == "WOULD DELETE"


def test_cleanup_deletes_expired_environment(monkeypatch):

    calls = setup_cleanup(monkeypatch)

    results = cleanup.cleanup_expired_environments(
        dry_run=False,
        now=NOW,
    )

    assert calls == [
        ("expired-box", True)
    ]

    assert results[0]["status"] == "DELETED"


def test_active_environment_is_not_deleted(monkeypatch):

    calls = setup_cleanup(monkeypatch)

    cleanup.cleanup_expired_environments(
        now=NOW,
    )

    assert all(
        name != "active-box"
        for name, locked in calls
    )


def test_environment_without_expiration_is_ignored(monkeypatch):

    calls = setup_cleanup(monkeypatch)

    monkeypatch.setattr(
        cleanup,
        "list_instances",
        lambda: [
            {"name": "permanent-box", "expires_at": None}
        ],
    )

    results = cleanup.cleanup_expired_environments(
        now=NOW,
    )

    assert results == []
    assert calls == []