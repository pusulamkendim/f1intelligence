from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

TYRE_TOKENS = {
    "SOFT": "tyre-soft",
    "MEDIUM": "tyre-medium",
    "HARD": "tyre-hard",
    "INTERMEDIATE": "tyre-intermediate",
    "WET": "tyre-wet",
}


def normalize_team_color(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip().lstrip("#")
    if len(raw) != 6 or any(c not in "0123456789abcdefABCDEF" for c in raw):
        return None
    return f"#{raw.upper()}"


def tyre_semantic_token(compound: str | None) -> str | None:
    if not compound:
        return None
    return TYRE_TOKENS.get(compound.strip().upper())


def _series(rows: Iterable[dict[str, Any]], point_builder: Any, unit: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    meta: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row["driver_key"])
        meta[key] = {
            "label": str(row["driver_label"]),
            "driver_number": row.get("driver_number"),
            "driver_acronym": row.get("driver_acronym"),
            "classification_position": row.get("classification_position"),
            "team_key": row.get("team_key"),
            "team_label": row.get("team_label"),
            "color": normalize_team_color(row.get("team_color")),
        }
        point = point_builder(row)
        if point is not None:
            grouped[key].append(point)
    series = [
        {
            "key": key,
            **meta[key],
            "unit": unit,
            "points": sorted(points, key=_point_sort_key),
        }
        for key, points in grouped.items()
        if points
    ]
    return sorted(
        series,
        key=lambda item: (
            item.get("classification_position")
            if item.get("classification_position") is not None
            else 999,
            item.get("driver_acronym") or item["key"],
        ),
    )


def _point_sort_key(point: dict[str, Any]) -> tuple[Any, ...]:
    for key in ("lap", "stint", "timestamp", "x", "position"):
        if key in point:
            return (point[key],)
    return (0,)


def position_series(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return _series(
        rows,
        lambda r: {"lap": int(r["lap_number"]), "position": int(r["position"])},
        "position",
    )


def lap_time_series(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    materialized = list(rows)
    valid = [r for r in materialized if r.get("lap_duration_seconds") is not None and not r.get("is_pit_out_lap", False)]
    session_best = min((float(r["lap_duration_seconds"]) for r in valid), default=None)
    personal_best: dict[str, float] = {}
    for row in valid:
        key = str(row["driver_key"])
        value = float(row["lap_duration_seconds"])
        personal_best[key] = min(personal_best.get(key, value), value)

    def point(row: dict[str, Any]) -> dict[str, Any] | None:
        value = row.get("lap_duration_seconds")
        if value is None:
            return None
        seconds = float(value)
        status = None
        if not row.get("is_pit_out_lap", False):
            if session_best is not None and seconds == session_best:
                status = "purple"
            elif seconds == personal_best.get(str(row["driver_key"])):
                status = "green"
            else:
                status = "yellow"
        return {
            "lap": int(row["lap_number"]),
            "seconds": seconds,
            "timing_status": status,
            "is_pit_out_lap": bool(row.get("is_pit_out_lap", False)),
        }

    return _series(materialized, point, "seconds")


def sector_series(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    materialized = list(rows)
    fields = ("sector_1_duration_seconds", "sector_2_duration_seconds", "sector_3_duration_seconds")
    session_best = {
        field: min((float(r[field]) for r in materialized if r.get(field) is not None), default=None)
        for field in fields
    }
    personal_best: dict[tuple[str, str], float] = {}
    for row in materialized:
        driver_key = str(row["driver_key"])
        for field in fields:
            if row.get(field) is None:
                continue
            value = float(row[field])
            key = (driver_key, field)
            personal_best[key] = min(personal_best.get(key, value), value)

    def point(row: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {"lap": int(row["lap_number"])}
        driver_key = str(row["driver_key"])
        for index, field in enumerate(fields, start=1):
            value = row.get(field)
            if value is None:
                continue
            seconds = float(value)
            if session_best[field] is not None and seconds == session_best[field]:
                status = "purple"
            elif seconds == personal_best[(driver_key, field)]:
                status = "green"
            else:
                status = "yellow"
            payload[f"s{index}_seconds"] = seconds
            payload[f"s{index}_status"] = status
        return payload

    return _series(materialized, point, "seconds")


def speed_series(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return _series(
        rows,
        lambda r: {
            "lap": int(r["lap_number"]),
            "i1_kph": r.get("i1_speed_kph"),
            "i2_kph": r.get("i2_speed_kph"),
            "speed_trap_kph": r.get("st_speed_kph"),
        },
        "kph",
    )


def stint_series(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return _series(
        rows,
        lambda r: {
            "stint": int(r["stint_number"]),
            "lap_start": r.get("lap_start"),
            "lap_end": r.get("lap_end"),
            "compound": r.get("compound"),
            "compound_token": tyre_semantic_token(r.get("compound")),
            "tyre_age_at_start": r.get("tyre_age_at_start"),
        },
        "stint",
    )


def interval_series(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return _series(
        rows,
        lambda r: {
            "timestamp": r["observed_at"].isoformat(),
            "gap_to_leader_seconds": r.get("gap_to_leader_seconds"),
            "interval_seconds": r.get("interval_seconds"),
            "gap_text": r.get("gap_to_leader_text"),
            "interval_text": r.get("interval_text"),
        },
        "seconds",
    )


def pit_stop_series(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return _series(
        rows,
        lambda r: {
            "lap": int(r["lap_number"]),
            "timestamp": r["observed_at"].isoformat(),
            "stop_seconds": r.get("stop_duration_seconds"),
            "pit_lane_seconds": r.get("lane_duration_seconds"),
        },
        "seconds",
    )


SEGMENT_TOKENS = {
    0: "segment-unavailable",
    2048: "timing-yellow",
    2049: "timing-green",
    2051: "timing-purple",
    2064: "pit-lane",
}


def segment_semantic_token(value: int | None) -> str:
    if value is None:
        return "segment-unavailable"
    return SEGMENT_TOKENS.get(int(value), "segment-unknown")


def _segment_payload(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    return [
        {
            "index": index + 1,
            "code": int(value) if value is not None else None,
            "token": segment_semantic_token(value),
        }
        for index, value in enumerate(values)
    ]


def segment_series(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return _series(
        rows,
        lambda r: {
            "lap": int(r["lap_number"]),
            "sector_1": _segment_payload(r.get("segments_sector_1")),
            "sector_2": _segment_payload(r.get("segments_sector_2")),
            "sector_3": _segment_payload(r.get("segments_sector_3")),
        },
        "segment",
    )
