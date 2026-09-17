from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _number_or_text(value: Any) -> tuple[float | None, str | None]:
    if isinstance(value, (int, float)):
        return float(value), None
    if isinstance(value, str):
        return None, value
    return None, None


@dataclass(frozen=True)
class OpenF1RaceControlEvent:
    session_key: int
    observed_at: datetime
    message: str
    driver_number: int | None
    category: str | None
    flag: str | None
    scope: str | None
    lap_number: int | None
    sector: int | None
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class OpenF1Interval:
    session_key: int
    driver_number: int
    observed_at: datetime
    interval_seconds: float | None
    interval_text: str | None
    gap_to_leader_seconds: float | None
    gap_to_leader_text: str | None
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class OpenF1PitStop:
    session_key: int
    driver_number: int
    lap_number: int
    observed_at: datetime | None
    lane_duration_seconds: float | None
    stop_duration_seconds: float | None
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class OpenF1Weather:
    session_key: int
    observed_at: datetime
    air_temperature_c: float | None
    track_temperature_c: float | None
    humidity_percent: float | None
    pressure_mbar: float | None
    rainfall: bool | None
    wind_direction_degrees: int | None
    wind_speed_mps: float | None
    raw_payload: dict[str, Any]


def parse_race_control(payload: list[dict[str, Any]]) -> list[OpenF1RaceControlEvent]:
    rows = []
    for row in payload:
        observed_at = _dt(row.get("date"))
        if row.get("session_key") is None or observed_at is None or not row.get("message"):
            continue
        rows.append(OpenF1RaceControlEvent(
            session_key=int(row["session_key"]), observed_at=observed_at, message=str(row["message"]),
            driver_number=int(row["driver_number"]) if row.get("driver_number") is not None else None,
            category=row.get("category"), flag=row.get("flag"), scope=row.get("scope"),
            lap_number=int(row["lap_number"]) if row.get("lap_number") is not None else None,
            sector=int(row["sector"]) if row.get("sector") is not None else None, raw_payload=row,
        ))
    return rows


def parse_intervals(payload: list[dict[str, Any]]) -> list[OpenF1Interval]:
    rows = []
    for row in payload:
        observed_at = _dt(row.get("date"))
        if row.get("session_key") is None or row.get("driver_number") is None or observed_at is None:
            continue
        interval_seconds, interval_text = _number_or_text(row.get("interval"))
        gap_seconds, gap_text = _number_or_text(row.get("gap_to_leader"))
        rows.append(OpenF1Interval(int(row["session_key"]), int(row["driver_number"]), observed_at, interval_seconds, interval_text, gap_seconds, gap_text, row))
    return rows


def parse_pit_stops(payload: list[dict[str, Any]]) -> list[OpenF1PitStop]:
    rows = []
    for row in payload:
        if row.get("session_key") is None or row.get("driver_number") is None or row.get("lap_number") is None:
            continue
        rows.append(OpenF1PitStop(
            int(row["session_key"]), int(row["driver_number"]), int(row["lap_number"]), _dt(row.get("date")),
            float(row["lane_duration"]) if row.get("lane_duration") is not None else None,
            float(row["stop_duration"]) if row.get("stop_duration") is not None else None, row,
        ))
    return rows


def parse_weather(payload: list[dict[str, Any]]) -> list[OpenF1Weather]:
    rows = []
    for row in payload:
        observed_at = _dt(row.get("date"))
        if row.get("session_key") is None or observed_at is None:
            continue
        rainfall = row.get("rainfall")
        rows.append(OpenF1Weather(
            int(row["session_key"]), observed_at,
            float(row["air_temperature"]) if row.get("air_temperature") is not None else None,
            float(row["track_temperature"]) if row.get("track_temperature") is not None else None,
            float(row["humidity"]) if row.get("humidity") is not None else None,
            float(row["pressure"]) if row.get("pressure") is not None else None,
            bool(rainfall) if rainfall is not None else None,
            int(row["wind_direction"]) if row.get("wind_direction") is not None else None,
            float(row["wind_speed"]) if row.get("wind_speed") is not None else None, row,
        ))
    return rows
