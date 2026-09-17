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
    sector_1_duration_seconds: float | None
    sector_2_duration_seconds: float | None
    sector_3_duration_seconds: float | None
    i1_speed_kph: int | None
    i2_speed_kph: int | None
    st_speed_kph: int | None
    segments_sector_1: list[int] | None
    segments_sector_2: list[int] | None
    segments_sector_3: list[int] | None
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
    parsed: list[OpenF1Lap] = []
    for row in payload:
        if row.get("driver_number") is None or row.get("lap_number") is None:
            continue
        parsed.append(OpenF1Lap(
            session_key=int(row["session_key"]), driver_number=int(row["driver_number"]), lap_number=int(row["lap_number"]),
            lap_duration_seconds=float(row["lap_duration"]) if row.get("lap_duration") is not None else None,
            is_pit_out_lap=bool(row.get("is_pit_out_lap", False)), started_at=_dt(row.get("date_start")),
            sector_1_duration_seconds=float(row["duration_sector_1"]) if row.get("duration_sector_1") is not None else None,
            sector_2_duration_seconds=float(row["duration_sector_2"]) if row.get("duration_sector_2") is not None else None,
            sector_3_duration_seconds=float(row["duration_sector_3"]) if row.get("duration_sector_3") is not None else None,
            i1_speed_kph=int(row["i1_speed"]) if row.get("i1_speed") is not None else None,
            i2_speed_kph=int(row["i2_speed"]) if row.get("i2_speed") is not None else None,
            st_speed_kph=int(row["st_speed"]) if row.get("st_speed") is not None else None,
            segments_sector_1=row.get("segments_sector_1"), segments_sector_2=row.get("segments_sector_2"), segments_sector_3=row.get("segments_sector_3"), raw_payload=row,
        ))
    return parsed


def parse_stints(payload: list[dict[str, Any]]) -> list[OpenF1Stint]:
    parsed: list[OpenF1Stint] = []
    for row in payload:
        if row.get("driver_number") is None or row.get("stint_number") is None:
            continue
        parsed.append(OpenF1Stint(session_key=int(row["session_key"]), driver_number=int(row["driver_number"]), stint_number=int(row["stint_number"]), lap_start=int(row["lap_start"]) if row.get("lap_start") is not None else None, lap_end=int(row["lap_end"]) if row.get("lap_end") is not None else None, compound=row.get("compound"), tyre_age_at_start=int(row["tyre_age_at_start"]) if row.get("tyre_age_at_start") is not None else None, raw_payload=row))
    return parsed


def parse_positions(payload: list[dict[str, Any]]) -> list[OpenF1Position]:
    parsed: list[OpenF1Position] = []
    for row in payload:
        observed_at = _dt(row.get("date"))
        if row.get("driver_number") is None or row.get("position") is None or observed_at is None:
            continue
        parsed.append(OpenF1Position(session_key=int(row["session_key"]), driver_number=int(row["driver_number"]), observed_at=observed_at, position=int(row["position"]), raw_payload=row))
    return parsed
