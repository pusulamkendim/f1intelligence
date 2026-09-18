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
    starts: int
    wins: int
    podiums: int
    poles: int
    fastest_laps: int
    points: Decimal
    dnfs: int
    average_grid: float | None
    average_finish: float | None
    win_rate: float | None
    podium_rate: float | None
    positions_gained: int
    championships: int
    provenance: list[StatisticsProvenance]


class DriverSeasonStatisticsResponse(DriverCareerStatisticsResponse):
    season: int


class DriverModernRaceMetricsResponse(BaseModel):
    driver_key: str
    race_key: str
    session_code: str
    timed_laps: int
    best_lap_seconds: float | None
    median_lap_seconds: float | None
    average_lap_seconds: float | None
    stints: int
    longest_stint_laps: int | None
    compounds_used: list[str]
    provenance: list[StatisticsProvenance]
