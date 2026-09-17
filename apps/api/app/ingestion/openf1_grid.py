from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OpenF1StartingGridRow:
    session_key: int
    meeting_key: int
    driver_number: int
    position: int
    lap_duration_seconds: float | None
    raw_payload: dict[str, Any]


def parse_starting_grid(payload: list[dict[str, Any]]) -> list[OpenF1StartingGridRow]:
    rows: list[OpenF1StartingGridRow] = []
    for item in payload:
        if item.get("driver_number") is None or item.get("position") is None:
            continue
        rows.append(
            OpenF1StartingGridRow(
                session_key=int(item["session_key"]),
                meeting_key=int(item["meeting_key"]),
                driver_number=int(item["driver_number"]),
                position=int(item["position"]),
                lap_duration_seconds=(
                    float(item["lap_duration"])
                    if isinstance(item.get("lap_duration"), (int, float))
                    else None
                ),
                raw_payload=item,
            )
        )
    return rows
