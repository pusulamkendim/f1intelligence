from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


@dataclass(frozen=True)
class OpenF1Lap:
    session_key: int
    driver_number: int
    lap_number: int
    lap_duration_seconds: float | None
    is_pit_out_lap: bool
    started_at: datetime | None
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class OpenF1Stint:
    session_key: int
    driver_number: int
    stint_number: int
    lap_start: int | None
    lap_end: int | None
    compound: str | None
    tyre_age_at_start: int | None
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class OpenF1Position:
    session_key: int
    driver_number: int
    observed_at: datetime
    position: int
    raw_payload: dict[str, Any]


def parse_laps(payload: list[dict[str, Any]]) -> list[OpenF1Lap]:
    return [OpenF1Lap(int(r["session_key"]), int(r["driver_number"]), int(r["lap_number"]), float(r["lap_duration"]) if r.get("lap_duration") is not None else None, bool(r.get("is_pit_out_lap", False)), _dt(r.get("date_start")), r) for r in payload if r.get("driver_number") is not None and r.get("lap_number") is not None]


def parse_stints(payload: list[dict[str, Any]]) -> list[OpenF1Stint]:
    return [OpenF1Stint(int(r["session_key"]), int(r["driver_number"]), int(r["stint_number"]), int(r["lap_start"]) if r.get("lap_start") is not None else None, int(r["lap_end"]) if r.get("lap_end") is not None else None, r.get("compound"), int(r["tyre_age_at_start"]) if r.get("tyre_age_at_start") is not None else None, r) for r in payload if r.get("driver_number") is not None and r.get("stint_number") is not None]


def parse_positions(payload: list[dict[str, Any]]) -> list[OpenF1Position]:
    parsed: list[OpenF1Position] = []
    for r in payload:
        observed_at = _dt(r.get("date"))
        if r.get("driver_number") is None or r.get("position") is None or observed_at is None:
            continue
        parsed.append(OpenF1Position(int(r["session_key"]), int(r["driver_number"]), observed_at, int(r["position"]), r))
    return parsed
