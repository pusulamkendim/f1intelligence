from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class OpenF1Overtake:
    session_key: int
    meeting_key: int
    overtaking_driver_number: int
    overtaken_driver_number: int
    position: int
    observed_at: datetime
    raw_payload: dict[str, Any]


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_overtakes(payload: list[dict[str, Any]]) -> list[OpenF1Overtake]:
    rows: list[OpenF1Overtake] = []
    for item in payload:
        observed_at = _timestamp(item.get("date"))
        required = (
            item.get("session_key"),
            item.get("meeting_key"),
            item.get("overtaking_driver_number"),
            item.get("overtaken_driver_number"),
            item.get("position"),
        )
        if observed_at is None or any(value is None for value in required):
            continue
        rows.append(
            OpenF1Overtake(
                session_key=int(item["session_key"]),
                meeting_key=int(item["meeting_key"]),
                overtaking_driver_number=int(item["overtaking_driver_number"]),
                overtaken_driver_number=int(item["overtaken_driver_number"]),
                position=int(item["position"]),
                observed_at=observed_at,
                raw_payload=item,
            )
        )
    return rows
