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
            "team_key": row.get("team_key"),
            "team_label": row.get("team_label"),
            "color": normalize_team_color(row.get("team_color")),
        }
        point = point_builder(row)
        if point is not None:
            grouped[key].append(point)
    return [
        {"key": key, **meta[key], "unit": unit, "points": sorted(points, key=_point_sort_key)}
        for key, points in sorted(grouped.items())
        if points
    ]


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
    def point(row: dict[str, Any]) -> dict[str, Any] | None:
        value = row.get("lap_duration_seconds")
        if value is None:
            return None
        return {
            "lap": int(row["lap_number"]),
            "seconds": float(value),
            "is_pit_out_lap": bool(row.get("is_pit_out_lap", False)),
        }

    return _series(rows, point, "seconds")


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
