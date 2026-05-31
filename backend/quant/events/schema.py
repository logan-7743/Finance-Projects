"""Event record schema for the Trump event corpus."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class EventRecord:
    """A single timestamped text event (social post or speech transcript)."""

    event_id: str
    utc_timestamp: datetime
    source: str
    event_type: str
    text: str
    url: str | None
    native_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["utc_timestamp"] = self.utc_timestamp.astimezone(UTC).isoformat()
        return payload

    @classmethod
    def from_json_dict(cls, payload: dict[str, Any]) -> EventRecord:
        ts = payload["utc_timestamp"]
        if isinstance(ts, str):
            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            raise TypeError("utc_timestamp must be an ISO string.")
        return cls(
            event_id=payload["event_id"],
            utc_timestamp=parsed.astimezone(UTC),
            source=payload["source"],
            event_type=payload["event_type"],
            text=payload["text"],
            url=payload.get("url"),
            native_id=payload["native_id"],
            metadata=dict(payload.get("metadata") or {}),
        )
