"""TTL-based cleanup for expired Vortex environments."""

from vortex.core.incus import (
    destroy_instance,
    get_instance_expiration,
    list_instances,
)

from vortex.lifecycle.locks import (
    EnvironmentBusyError,
    environment_lock,
)

from vortex.lifecycle.ttl import is_expired


def cleanup_expired_environments(
    dry_run: bool = False,
    now=None,
) -> list[dict]:
    """Find and safely remove expired environments."""

    results = []

    environments = list_instances()

    for environment in environments:

        name = environment["name"]
        expiration = environment.get("expires_at")

        # Environments without TTL are not automatically deleted.
        if not expiration:
            continue

        try:

            if not is_expired(expiration, now):
                continue

            # Ensure no experiment or other Vortex operation
            # is currently using this environment.
            with environment_lock(name):

                # Recheck metadata while holding the lock.
                current_expiration = get_instance_expiration(name)

                if not current_expiration:

                    results.append({
                        "name": name,
                        "status": "SKIPPED",
                        "detail": "Expiration was removed.",
                    })

                    continue

                if not is_expired(current_expiration, now):

                    results.append({
                        "name": name,
                        "status": "SKIPPED",
                        "detail": "Expiration was extended.",
                    })

                    continue

                if dry_run:

                    results.append({
                        "name": name,
                        "status": "WOULD DELETE",
                        "detail": "Environment has expired.",
                    })

                else:

                    destroy_instance(
                        name,
                        lock_held=True,
                    )

                    results.append({
                        "name": name,
                        "status": "DELETED",
                        "detail": "Expired environment removed.",
                    })

        except EnvironmentBusyError:

            results.append({
                "name": name,
                "status": "BUSY",
                "detail": "Another Vortex operation is using it.",
            })

        except Exception as exc:

            results.append({
                "name": name,
                "status": "ERROR",
                "detail": str(exc),
            })

    return results