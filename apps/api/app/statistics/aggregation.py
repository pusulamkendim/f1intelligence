from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


@dataclass(frozen=True)
class DriverResult:
    season: int
    round: int
    finish_position: int | None
    grid_position: int | None
    points: Decimal
    status: str | None
    fastest_lap_rank: int | None


@dataclass(frozen=True)
class DriverQualifying:
    season: int
    round: int
    position: int


@dataclass(frozen=True)
class DriverSeasonStanding:
    season: int
    position: int


@dataclass(frozen=True)
class DriverStatistics:
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


def _is_classified_finish(status: str | None) -> bool:
    if status is None:
        return False
    normalized = status.casefold()
    return normalized == "finished" or normalized.startswith("+")


def aggregate_driver_statistics(
    results: Iterable[DriverResult],
    qualifying: Iterable[DriverQualifying] = (),
    standings: Iterable[DriverSeasonStanding] = (),
) -> DriverStatistics:
    result_rows = list(results)
    qualifying_rows = list(qualifying)
    standing_rows = list(standings)

    starts = len(result_rows)
    wins = sum(row.finish_position == 1 for row in result_rows)
    podiums = sum(row.finish_position is not None and row.finish_position <= 3 for row in result_rows)
    fastest_laps = sum(row.fastest_lap_rank == 1 for row in result_rows)
    points = sum((row.points for row in result_rows), Decimal("0"))
    dnfs = sum(not _is_classified_finish(row.status) for row in result_rows)

    grids = [row.grid_position for row in result_rows if row.grid_position is not None]
    finishes = [row.finish_position for row in result_rows if row.finish_position is not None]
    positions_gained = sum(
        row.grid_position - row.finish_position
        for row in result_rows
        if row.grid_position is not None
        and row.grid_position > 0
        and row.finish_position is not None
    )

    pole_rounds = {(row.season, row.round) for row in qualifying_rows if row.position == 1}
    championships = len({row.season for row in standing_rows if row.position == 1})

    return DriverStatistics(
        starts=starts,
        wins=wins,
        podiums=podiums,
        poles=len(pole_rounds),
        fastest_laps=fastest_laps,
        points=points,
        dnfs=dnfs,
        average_grid=(sum(grids) / len(grids)) if grids else None,
        average_finish=(sum(finishes) / len(finishes)) if finishes else None,
        win_rate=(wins / starts) if starts else None,
        podium_rate=(podiums / starts) if starts else None,
        positions_gained=positions_gained,
        championships=championships,
    )
