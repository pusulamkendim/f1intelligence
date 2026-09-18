from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.statistics import (
    DriverCareerStatisticsResponse,
    DriverModernRaceMetricsResponse,
    DriverSeasonStatisticsResponse,
    StatisticsProvenance,
)
from app.statistics.aggregation import (
    DriverQualifying,
    DriverResult,
    DriverSeasonStanding,
    DriverSprintResult,
    aggregate_driver_statistics,
)
from app.statistics.modern import (
    LapMetricInput,
    StintMetricInput,
    aggregate_modern_race_metrics,
)


class StatisticsNotFoundError(LookupError):
    pass


async def _driver_id(
    db: AsyncSession,
    driver_key: str,
) -> Any:
    result = await db.execute(
        text(
            """
            SELECT id
            FROM entities
            WHERE entity_type = 'person'
              AND metadata->>'kind' = 'driver'
              AND (slug = :key OR id::text = :key)
            LIMIT 1
            """
        ),
        {"key": driver_key},
    )
    row = result.mappings().first()
    if row is None:
        raise StatisticsNotFoundError("Driver not found")
    return row["id"]


async def _historical_rows(
    db: AsyncSession,
    entity_id: Any,
    season: int | None,
) -> tuple[list[Any], list[Any], list[Any], list[Any]]:
    season_clause = "AND r.season = :season" if season is not None else ""
    params = {"entity_id": entity_id, "season": season}

    results = (
        await db.execute(
            text(
                f"""
                SELECT
                    r.season,
                    r.round,
                    rr.finish_position,
                    rr.grid_position,
                    rr.points,
                    rr.status,
                    rr.fastest_lap_rank,
                    rr.provider,
                    rr.source_url,
                    rr.fetched_at
                FROM race_results rr
                JOIN races r ON r.id = rr.race_id
                WHERE rr.driver_entity_id = :entity_id
                  {season_clause}
                ORDER BY r.season, r.round
                """
            ),
            params,
        )
    ).mappings().all()

    sprints = (
        await db.execute(
            text(
                f"""
                SELECT
                    r.season,
                    r.round,
                    sr.finish_position,
                    sr.grid_position,
                    sr.points,
                    sr.status,
                    sr.provider,
                    sr.source_url,
                    sr.fetched_at
                FROM sprint_results sr
                JOIN races r ON r.id = sr.race_id
                WHERE sr.driver_entity_id = :entity_id
                  {season_clause}
                ORDER BY r.season, r.round
                """
            ),
            params,
        )
    ).mappings().all()

    qualifying = (
        await db.execute(
            text(
                f"""
                SELECT
                    r.season,
                    r.round,
                    qr.position,
                    qr.provider,
                    qr.source_url,
                    qr.fetched_at
                FROM qualifying_results qr
                JOIN races r ON r.id = qr.race_id
                WHERE qr.driver_entity_id = :entity_id
                  {season_clause}
                ORDER BY r.season, r.round
                """
            ),
            params,
        )
    ).mappings().all()

    standings = (
        await db.execute(
            text(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (dss.season)
                        dss.id,
                        dss.season,
                        dss.after_round,
                        dss.provider,
                        dss.source_url,
                        dss.fetched_at
                    FROM driver_standings_snapshots dss
                    JOIN driver_standing_rows dsr
                      ON dsr.snapshot_id = dss.id
                    WHERE dsr.driver_entity_id = :entity_id
                      AND (
                          :season IS NULL
                          OR dss.season = :season
                      )
                    ORDER BY
                        dss.season,
                        dss.after_round DESC,
                        dss.fetched_at DESC
                )
                SELECT
                    latest.season,
                    latest.after_round,
                    dsr.position,
                    dsr.points,
                    latest.provider,
                    latest.source_url,
                    latest.fetched_at,
                    (
                        EXISTS (
                            SELECT 1
                            FROM races season_race
                            WHERE season_race.season = latest.season
                        )
                        AND NOT EXISTS (
                            SELECT 1
                            FROM races season_race
                            WHERE season_race.season = latest.season
                              AND season_race.status <> 'completed'
                        )
                    ) AS season_complete
                FROM latest
                JOIN driver_standing_rows dsr
                  ON dsr.snapshot_id = latest.id
                 AND dsr.driver_entity_id = :entity_id
                ORDER BY latest.season
                """
            ),
            params,
        )
    ).mappings().all()

    return (
        list(results),
        list(qualifying),
        list(standings),
        list(sprints),
    )


def _provenance(
    rows: list[Any],
    dataset: str,
) -> list[StatisticsProvenance]:
    grouped: dict[
        tuple[str, str | None, str | None],
        set[str],
    ] = defaultdict(set)

    for row in rows:
        provider = row.get("provider")
        if not provider:
            continue
        fetched = row.get("fetched_at")
        key = (
            provider,
            row.get("source_url"),
            fetched.isoformat() if fetched else None,
        )
        grouped[key].add(dataset)

    return [
        StatisticsProvenance(
            provider=key[0],
            source_url=key[1],
            fetched_at=key[2],
            datasets=sorted(datasets),
        )
        for key, datasets in sorted(grouped.items())
    ]


def _merge_provenance(
    *groups: list[StatisticsProvenance],
) -> list[StatisticsProvenance]:
    merged: dict[
        tuple[str, str | None, str | None],
        set[str],
    ] = defaultdict(set)

    for group in groups:
        for item in group:
            key = (
                item.provider,
                item.source_url,
                item.fetched_at,
            )
            merged[key].update(item.datasets)

    return [
        StatisticsProvenance(
            provider=key[0],
            source_url=key[1],
            fetched_at=key[2],
            datasets=sorted(datasets),
        )
        for key, datasets in sorted(merged.items())
    ]


async def driver_statistics(
    db: AsyncSession,
    driver_key: str,
    season: int | None = None,
) -> (
    DriverCareerStatisticsResponse
    | DriverSeasonStatisticsResponse
):
    entity_id = await _driver_id(db, driver_key)
    (
        results,
        qualifying,
        standings,
        sprints,
    ) = await _historical_rows(
        db,
        entity_id,
        season,
    )

    if not results:
        raise StatisticsNotFoundError(
            "No race statistics available for driver"
        )

    stats = aggregate_driver_statistics(
        [
            DriverResult(
                r["season"],
                r["round"],
                r["finish_position"],
                r["grid_position"],
                Decimal(r["points"]),
                r["status"],
                r["fastest_lap_rank"],
            )
            for r in results
        ],
        [
            DriverQualifying(
                r["season"],
                r["round"],
                r["position"],
            )
            for r in qualifying
        ],
        [
            DriverSeasonStanding(
                r["season"],
                r["after_round"],
                r["position"],
                Decimal(r["points"]),
                bool(r["season_complete"]),
            )
            for r in standings
        ],
        [
            DriverSprintResult(
                r["season"],
                r["round"],
                r["finish_position"],
                r["grid_position"],
                Decimal(r["points"]),
                r["status"],
            )
            for r in sprints
        ],
    )

    provenance = _merge_provenance(
        _provenance(results, "race_results"),
        _provenance(qualifying, "qualifying_results"),
        _provenance(standings, "driver_standings"),
        _provenance(sprints, "sprint_results"),
    )

    payload = {
        "driver_key": driver_key,
        **stats.__dict__,
        "provenance": provenance,
    }

    if season is None:
        return DriverCareerStatisticsResponse(**payload)

    latest_standing = standings[-1] if standings else None
    return DriverSeasonStatisticsResponse(
        season=season,
        championship_position=(
            latest_standing["position"]
            if latest_standing
            else None
        ),
        season_complete=(
            bool(latest_standing["season_complete"])
            if latest_standing
            else False
        ),
        **payload,
    )


async def driver_modern_race_metrics(
    db: AsyncSession,
    driver_key: str,
    race_key: str,
    session_code: str = "race",
) -> DriverModernRaceMetricsResponse:
    entity_id = await _driver_id(db, driver_key)
    params = {
        "entity_id": entity_id,
        "race_key": race_key,
        "session_code": session_code,
    }

    laps = (
        await db.execute(
            text(
                """
                SELECT
                    sl.lap_number,
                    sl.lap_duration_seconds,
                    sl.is_pit_out_lap,
                    sl.provider,
                    sl.source_url,
                    sl.fetched_at
                FROM session_laps sl
                JOIN race_sessions rs ON rs.id = sl.session_id
                JOIN races r ON r.id = rs.race_id
                WHERE sl.driver_entity_id = :entity_id
                  AND r.slug = :race_key
                  AND rs.session_code = :session_code
                ORDER BY sl.lap_number
                """
            ),
            params,
        )
    ).mappings().all()

    stints = (
        await db.execute(
            text(
                """
                SELECT
                    ss.stint_number,
                    ss.lap_start,
                    ss.lap_end,
                    ss.compound,
                    ss.tyre_age_at_start,
                    ss.provider,
                    ss.source_url,
                    ss.fetched_at
                FROM session_stints ss
                JOIN race_sessions rs ON rs.id = ss.session_id
                JOIN races r ON r.id = rs.race_id
                WHERE ss.driver_entity_id = :entity_id
                  AND r.slug = :race_key
                  AND rs.session_code = :session_code
                ORDER BY ss.stint_number
                """
            ),
            params,
        )
    ).mappings().all()

    if not laps and not stints:
        raise StatisticsNotFoundError(
            "No granular OpenF1 metrics available"
        )

    metrics = aggregate_modern_race_metrics(
        [
            LapMetricInput(
                r["lap_number"],
                r["lap_duration_seconds"],
                r["is_pit_out_lap"],
            )
            for r in laps
        ],
        [
            StintMetricInput(
                r["stint_number"],
                r["lap_start"],
                r["lap_end"],
                r["compound"],
                r["tyre_age_at_start"],
            )
            for r in stints
        ],
    )

    return DriverModernRaceMetricsResponse(
        driver_key=driver_key,
        race_key=race_key,
        session_code=session_code,
        **metrics.__dict__,
        provenance=_merge_provenance(
            _provenance(list(laps), "session_laps"),
            _provenance(list(stints), "session_stints"),
        ),
    )
