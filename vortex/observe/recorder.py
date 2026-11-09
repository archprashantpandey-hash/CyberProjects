"""JSON Lines event recorder for Vortex experiments."""

import json
from datetime import datetime, timezone
from pathlib import Path


class EventRecorder:
    """Append timestamped events to a report file."""

    def __init__(self, environment: str) -> None:
        self.environment = environment
        self.path = Path("reports") / f"{environment}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, details: dict | None = None) -> None:
        """Append one event as a JSON object."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": self.environment,
            "event": event,
            "details": details or {},
        }

        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry) + "\n")