from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class StatisticsProvenance(BaseModel):
    provider: str
    source_url: str | None = None
    fetched_at: str | None = None
    datasets: list[str]


class DriverCareerStatisticsResponse(BaseModel):
    driver_key: str
    race_entries: int
    starts: int
    wins: int
    podiums: int
    poles: int
    qualifying_p1s: int
    fastest_laps: int
    points: Decimal
    race_points: Decimal
    sprint_points: Decimal
    points_adjustment: Decimal
    classified_finishes: int
    dnfs: int
    dns: int
    dsqs: int
    sprint_entries: int
    sprint_starts: int
    sprint_wins: int
    sprint_top3s: int
    average_grid: float | None
    average_finish: float | None
    average_classification_position: float | None
    win_rate: float | None
    podium_rate: float | None
    positions_gained: int
    championships: int
    provenance: list[StatisticsProvenance]


class DriverSeasonStatisticsResponse(DriverCareerStatisticsResponse):
    season: int
    championship_position: int | None = None
    season_complete: bool = False


class DriverModernRaceMetricsResponse(BaseModel):
    driver_key: str
    race_key: str
    session_code: str
    timed_laps: int
    best_lap_seconds: float | None
    median_lap_seconds: float | None
    average_lap_seconds: float | None
    lap_sample_policy: str = "timed_laps_excluding_pit_out_and_null"
    stints: int
    longest_stint_laps: int | None
    compounds_used: list[str]
    provenance: list[StatisticsProvenance]
