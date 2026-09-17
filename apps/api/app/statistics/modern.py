from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable


@dataclass(frozen=True)
class LapMetricInput:
    lap_number: int
    lap_duration_seconds: float | None
    is_pit_out_lap: bool = False


@dataclass(frozen=True)
class StintMetricInput:
    stint_number: int
    lap_start: int | None
    lap_end: int | None
    compound: str | None
    tyre_age_at_start: int | None


@dataclass(frozen=True)
class ModernRaceMetrics:
    timed_laps: int
    best_lap_seconds: float | None
    median_lap_seconds: float | None
    average_lap_seconds: float | None
    stints: int
    longest_stint_laps: int | None
    compounds_used: tuple[str, ...]


def aggregate_modern_race_metrics(
    laps: Iterable[LapMetricInput],
    stints: Iterable[StintMetricInput],
) -> ModernRaceMetrics:
    lap_rows = list(laps)
    stint_rows = list(stints)
    clean_laps = [
        row.lap_duration_seconds
        for row in lap_rows
        if row.lap_duration_seconds is not None
        and row.lap_duration_seconds > 0
        and not row.is_pit_out_lap
    ]
    stint_lengths = [
        row.lap_end - row.lap_start + 1
        for row in stint_rows
        if row.lap_start is not None and row.lap_end is not None and row.lap_end >= row.lap_start
    ]
    compounds = tuple(sorted({row.compound for row in stint_rows if row.compound}))
    return ModernRaceMetrics(
        timed_laps=len(clean_laps),
        best_lap_seconds=min(clean_laps) if clean_laps else None,
        median_lap_seconds=median(clean_laps) if clean_laps else None,
        average_lap_seconds=(sum(clean_laps) / len(clean_laps)) if clean_laps else None,
        stints=len(stint_rows),
        longest_stint_laps=max(stint_lengths) if stint_lengths else None,
        compounds_used=compounds,
    )
