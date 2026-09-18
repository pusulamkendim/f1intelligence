from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal


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
class DriverSprintResult:
    season: int
    round: int
    finish_position: int | None
    grid_position: int | None
    points: Decimal
    status: str | None


@dataclass(frozen=True)
class DriverQualifying:
    season: int
    round: int
    position: int


@dataclass(frozen=True)
class DriverSeasonStanding:
    season: int
    after_round: int
    position: int
    points: Decimal
    season_complete: bool


@dataclass(frozen=True)
class DriverStatistics:
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
    sprint_podiums: int
    average_grid: float | None
    average_finish: float | None
    average_classification_position: float | None
    win_rate: float | None
    podium_rate: float | None
    positions_gained: int
    championships: int


DNS_PREFIXES = (
    "did not start",
    "did not qualify",
    "did not prequalify",
    "withdrawn",
    "withdrew",
)
DSQ_PREFIXES = (
    "disqualified",
    "excluded",
)


def _normalized_status(status: str | None) -> str:
    return " ".join((status or "").casefold().split())


def is_dns(status: str | None) -> bool:
    normalized = _normalized_status(status)
    return any(normalized.startswith(prefix) for prefix in DNS_PREFIXES)


def is_dsq(status: str | None) -> bool:
    normalized = _normalized_status(status)
    return any(normalized.startswith(prefix) for prefix in DSQ_PREFIXES)


def is_classified_finish(status: str | None) -> bool:
    normalized = _normalized_status(status)
    return (
        normalized == "finished"
        or normalized == "classified"
        or normalized == "lapped"
        or normalized.startswith("+")
    )


def did_start(status: str | None) -> bool:
    return not is_dns(status)


def _points_by_season(
    results: list[DriverResult],
    sprints: list[DriverSprintResult],
    standings: list[DriverSeasonStanding],
) -> Decimal:
    race_by_season: dict[int, Decimal] = {}
    sprint_by_season: dict[int, Decimal] = {}
    standings_by_season = {row.season: row for row in standings}

    for row in results:
        race_by_season[row.season] = (
            race_by_season.get(row.season, Decimal("0")) + row.points
        )
    for row in sprints:
        sprint_by_season[row.season] = (
            sprint_by_season.get(row.season, Decimal("0")) + row.points
        )

    seasons = (
        set(race_by_season)
        | set(sprint_by_season)
        | set(standings_by_season)
    )
    total = Decimal("0")
    for season in seasons:
        standing = standings_by_season.get(season)
        if standing is not None:
            total += standing.points
        else:
            total += race_by_season.get(season, Decimal("0"))
            total += sprint_by_season.get(season, Decimal("0"))
    return total


def aggregate_driver_statistics(
    results: Iterable[DriverResult],
    qualifying: Iterable[DriverQualifying] = (),
    standings: Iterable[DriverSeasonStanding] = (),
    sprints: Iterable[DriverSprintResult] = (),
) -> DriverStatistics:
    result_rows = list(results)
    qualifying_rows = list(qualifying)
    standing_rows = list(standings)
    sprint_rows = list(sprints)

    started_rows = [row for row in result_rows if did_start(row.status)]
    classified_rows = [
        row for row in started_rows if is_classified_finish(row.status)
    ]

    race_entries = len(result_rows)
    starts = len(started_rows)
    wins = sum(row.finish_position == 1 for row in result_rows)
    podiums = sum(
        row.finish_position is not None and row.finish_position <= 3
        for row in result_rows
    )
    fastest_laps = sum(
        row.fastest_lap_rank == 1 for row in result_rows
    )
    race_points = sum(
        (row.points for row in result_rows),
        Decimal("0"),
    )
    sprint_points = sum(
        (row.points for row in sprint_rows),
        Decimal("0"),
    )
    points = _points_by_season(
        result_rows,
        sprint_rows,
        standing_rows,
    )

    dns = sum(is_dns(row.status) for row in result_rows)
    dsqs = sum(
        did_start(row.status) and is_dsq(row.status)
        for row in result_rows
    )
    dnfs = sum(
        did_start(row.status)
        and not is_classified_finish(row.status)
        and not is_dsq(row.status)
        for row in result_rows
    )

    grids = [
        row.grid_position
        for row in started_rows
        if row.grid_position is not None and row.grid_position > 0
    ]
    classified_finishes = [
        row.finish_position
        for row in classified_rows
        if row.finish_position is not None
    ]
    classification_positions = [
        row.finish_position
        for row in started_rows
        if row.finish_position is not None
    ]
    positions_gained = sum(
        row.grid_position - row.finish_position
        for row in started_rows
        if row.grid_position is not None
        and row.grid_position > 0
        and row.finish_position is not None
    )

    pole_rounds = {
        (row.season, row.round)
        for row in qualifying_rows
        if row.position == 1
    }
    championships = len(
        {
            row.season
            for row in standing_rows
            if row.position == 1 and row.season_complete
        }
    )

    sprint_started = [
        row for row in sprint_rows if did_start(row.status)
    ]
    sprint_wins = sum(
        row.finish_position == 1 for row in sprint_rows
    )
    sprint_podiums = sum(
        row.finish_position is not None and row.finish_position <= 3
        for row in sprint_rows
    )

    return DriverStatistics(
        race_entries=race_entries,
        starts=starts,
        wins=wins,
        podiums=podiums,
        poles=len(pole_rounds),
        qualifying_p1s=len(pole_rounds),
        fastest_laps=fastest_laps,
        points=points,
        race_points=race_points,
        sprint_points=sprint_points,
        points_adjustment=points - race_points - sprint_points,
        classified_finishes=len(classified_rows),
        dnfs=dnfs,
        dns=dns,
        dsqs=dsqs,
        sprint_entries=len(sprint_rows),
        sprint_starts=len(sprint_started),
        sprint_wins=sprint_wins,
        sprint_podiums=sprint_podiums,
        average_grid=(sum(grids) / len(grids)) if grids else None,
        average_finish=(
            sum(classified_finishes) / len(classified_finishes)
            if classified_finishes
            else None
        ),
        average_classification_position=(
            sum(classification_positions)
            / len(classification_positions)
            if classification_positions
            else None
        ),
        win_rate=(wins / starts) if starts else None,
        podium_rate=(podiums / starts) if starts else None,
        positions_gained=positions_gained,
        championships=championships,
    )
