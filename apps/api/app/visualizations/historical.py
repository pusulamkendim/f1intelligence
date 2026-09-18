from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.visualizations import VisualizationResponse
from app.visualizations.series import normalize_team_color
from app.visualizations.service import (
    VisualizationNotFoundError,
    _axis,
    _presentation,
)

StandingsKind = Literal["driver-standings", "constructor-standings"]
ClassificationKind = Literal["race-result", "qualifying-result"]


def _provenance(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str | None, str | None]] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        provider = row.get("provider")
        if not provider:
            continue
        fetched = row.get("fetched_at")
        fetched_text = fetched.isoformat() if fetched else None
        key = (provider, row.get("source_url"), fetched_text)
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                "provider": provider,
                "source_url": row.get("source_url"),
                "fetched_at": fetched_text,
                "datasets": [str(row.get("dataset") or "structured_results")],
            }
        )
    return result


async def _race(
    session: AsyncSession,
    race_key: str,
) -> dict[str, Any]:
    result = await session.execute(
        text(
            """
            SELECT id, season, round, slug, official_name
            FROM races
            WHERE slug = :race_key OR id::text = :race_key
            LIMIT 1
            """
        ),
        {"race_key": race_key},
    )
    row = result.mappings().first()
    if row is None:
        raise VisualizationNotFoundError(f"race not found: {race_key}")
    return dict(row)


async def race_classification(
    session: AsyncSession,
    race_key: str,
    chart: ClassificationKind,
) -> VisualizationResponse:
    race = await _race(session, race_key)
    if chart == "race-result":
        result = await session.execute(
            text(
                """
                SELECT rr.finish_position AS position,
                       rr.grid_position,
                       rr.points,
                       rr.laps,
                       rr.status,
                       rr.finish_time,
                       rr.fastest_lap_rank,
                       rr.fastest_lap_number,
                       rr.fastest_lap_time,
                       rr.car_number AS driver_number,
                       e.slug AS driver_key,
                       e.display_name AS driver_label,
                       COALESCE(se.name_acronym, code.alias) AS driver_acronym,
                       te.slug AS team_key,
                       te.display_name AS team_label,
                       se.team_colour AS team_color,
                       rr.provider,
                       rr.source_url,
                       rr.fetched_at,
                       'race_results'::text AS dataset
                FROM race_results rr
                LEFT JOIN entities e ON e.id = rr.driver_entity_id
                LEFT JOIN entities te ON te.id = rr.team_entity_id
                LEFT JOIN LATERAL (
                    SELECT entry.name_acronym, entry.team_colour
                    FROM race_sessions rs
                    JOIN session_entries entry ON entry.session_id = rs.id
                    WHERE rs.race_id = rr.race_id
                      AND entry.driver_entity_id = rr.driver_entity_id
                    ORDER BY rs.starts_at DESC
                    LIMIT 1
                ) se ON true
                LEFT JOIN LATERAL (
                    SELECT ea.alias
                    FROM entity_aliases ea
                    WHERE ea.entity_id = rr.driver_entity_id
                      AND ea.alias_type = 'driver_code'
                      AND ea.enabled = true
                    ORDER BY ea.confidence DESC
                    LIMIT 1
                ) code ON true
                WHERE rr.race_id = :race_id
                ORDER BY rr.finish_position NULLS LAST, rr.position_text
                """
            ),
            {"race_id": race["id"]},
        )
        rows = [dict(row) for row in result.mappings().all()]
        if not rows:
            raise VisualizationNotFoundError("race classification not available")
        series = [
            {
                "key": row["driver_key"] or f'car-{row["driver_number"]}',
                "label": row["driver_label"] or f'Car {row["driver_number"]}',
                "unit": "position",
                "driver_number": row["driver_number"],
                "driver_acronym": row["driver_acronym"],
                "classification_position": row["position"],
                "team_key": row["team_key"],
                "team_label": row["team_label"],
                "color": normalize_team_color(row["team_color"]),
                "points": [
                    {
                        "position": row["position"],
                        "grid_position": row["grid_position"],
                        "points": float(row["points"]),
                        "laps": row["laps"],
                        "status": row["status"],
                        "finish_time": row["finish_time"],
                        "fastest_lap_rank": row["fastest_lap_rank"],
                        "fastest_lap_number": row["fastest_lap_number"],
                        "fastest_lap_time": row["fastest_lap_time"],
                    }
                ],
            }
            for row in rows
        ]
        preset = "race-classification"
        title_suffix = "Race classification"
    else:
        result = await session.execute(
            text(
                """
                SELECT qr.position,
                       qr.q1,
                       qr.q2,
                       qr.q3,
                       qr.car_number AS driver_number,
                       e.slug AS driver_key,
                       e.display_name AS driver_label,
                       se.name_acronym AS driver_acronym,
                       te.slug AS team_key,
                       te.display_name AS team_label,
                       se.team_colour AS team_color,
                       qr.provider,
                       qr.source_url,
                       qr.fetched_at,
                       'qualifying_results'::text AS dataset
                FROM qualifying_results qr
                LEFT JOIN entities e ON e.id = qr.driver_entity_id
                LEFT JOIN entities te ON te.id = qr.team_entity_id
                LEFT JOIN LATERAL (
                    SELECT entry.name_acronym, entry.team_colour
                    FROM race_sessions rs
                    JOIN session_entries entry ON entry.session_id = rs.id
                    WHERE rs.race_id = qr.race_id
                      AND entry.driver_entity_id = qr.driver_entity_id
                    ORDER BY rs.starts_at DESC
                    LIMIT 1
                ) se ON true
                LEFT JOIN LATERAL (
                    SELECT ea.alias
                    FROM entity_aliases ea
                    WHERE ea.entity_id = qr.driver_entity_id
                      AND ea.alias_type = 'driver_code'
                      AND ea.enabled = true
                    ORDER BY ea.confidence DESC
                    LIMIT 1
                ) code ON true
                WHERE qr.race_id = :race_id
                ORDER BY qr.position
                """
            ),
            {"race_id": race["id"]},
        )
        rows = [dict(row) for row in result.mappings().all()]
        if not rows:
            raise VisualizationNotFoundError("qualifying classification not available")
        series = [
            {
                "key": row["driver_key"] or f'car-{row["driver_number"]}',
                "label": row["driver_label"] or f'Car {row["driver_number"]}',
                "unit": "position",
                "driver_number": row["driver_number"],
                "driver_acronym": row["driver_acronym"],
                "classification_position": row["position"],
                "team_key": row["team_key"],
                "team_label": row["team_label"],
                "color": normalize_team_color(row["team_color"]),
                "points": [
                    {
                        "position": row["position"],
                        "q1": row["q1"],
                        "q2": row["q2"],
                        "q3": row["q3"],
                    }
                ],
            }
            for row in rows
        ]
        preset = "qualifying-classification"
        title_suffix = "Qualifying classification"

    return VisualizationResponse(
        key=f'{race["slug"]}:{chart}',
        chart_type="timing_table",
        title=f'{race["official_name"]} — {title_suffix}',
        x_axis=_axis("position", "Position", unit="position", formatter="position"),
        y_axis=_axis("driver", "Driver"),
        presentation=_presentation(
            preset,
            show_legend=False,
            show_annotations=False,
        ),
        series=series,
        annotations=[],
        provenance=_provenance(rows),
    )


async def season_standings(
    session: AsyncSession,
    season: int,
    kind: StandingsKind,
) -> VisualizationResponse:
    if kind == "driver-standings":
        result = await session.execute(
            text(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (after_round)
                           id, after_round, provider, source_url, fetched_at
                    FROM driver_standings_snapshots
                    WHERE season = :season
                    ORDER BY after_round, fetched_at DESC
                )
                SELECT latest.after_round AS round,
                       dsr.position,
                       dsr.points,
                       dsr.wins,
                       e.slug AS entity_key,
                       e.display_name AS entity_label,
                       team.team_key,
                       team.team_label,
                       team.team_color,
                       team.driver_number,
                       COALESCE(team.driver_acronym, code.alias) AS driver_acronym,
                       latest.provider,
                       latest.source_url,
                       latest.fetched_at,
                       'driver_standings'::text AS dataset
                FROM latest
                JOIN driver_standing_rows dsr ON dsr.snapshot_id = latest.id
                LEFT JOIN entities e ON e.id = dsr.driver_entity_id
                LEFT JOIN LATERAL (
                    SELECT te.slug AS team_key,
                           te.display_name AS team_label,
                           entry.team_colour AS team_color,
                           entry.driver_number,
                           entry.name_acronym AS driver_acronym
                    FROM race_results rr
                    JOIN races r ON r.id = rr.race_id
                    LEFT JOIN entities te ON te.id = rr.team_entity_id
                    LEFT JOIN LATERAL (
                        SELECT se.team_colour, se.driver_number, se.name_acronym
                        FROM race_sessions rs
                        JOIN session_entries se ON se.session_id = rs.id
                        WHERE rs.race_id = rr.race_id
                          AND se.driver_entity_id = rr.driver_entity_id
                        ORDER BY rs.starts_at DESC
                        LIMIT 1
                    ) entry ON true
                    WHERE rr.driver_entity_id = dsr.driver_entity_id
                      AND r.season = :season
                      AND r.round <= latest.after_round
                    ORDER BY r.round DESC
                    LIMIT 1
                ) team ON true
                LEFT JOIN LATERAL (
                    SELECT ea.alias
                    FROM entity_aliases ea
                    WHERE ea.entity_id = dsr.driver_entity_id
                      AND ea.alias_type = 'driver_code'
                      AND ea.enabled = true
                    ORDER BY ea.confidence DESC
                    LIMIT 1
                ) code ON true
                WHERE e.id IS NOT NULL
                ORDER BY latest.after_round, dsr.position
                """
            ),
            {"season": season},
        )
    else:
        result = await session.execute(
            text(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (after_round)
                           id, after_round, provider, source_url, fetched_at
                    FROM constructor_standings_snapshots
                    WHERE season = :season
                    ORDER BY after_round, fetched_at DESC
                )
                SELECT latest.after_round AS round,
                       csr.position,
                       csr.points,
                       csr.wins,
                       e.slug AS entity_key,
                       e.display_name AS entity_label,
                       e.slug AS team_key,
                       e.display_name AS team_label,
                       team.team_color,
                       NULL::integer AS driver_number,
                       NULL::text AS driver_acronym,
                       latest.provider,
                       latest.source_url,
                       latest.fetched_at,
                       'constructor_standings'::text AS dataset
                FROM latest
                JOIN constructor_standing_rows csr ON csr.snapshot_id = latest.id
                LEFT JOIN entities e ON e.id = csr.team_entity_id
                LEFT JOIN LATERAL (
                    SELECT se.team_colour AS team_color
                    FROM race_results rr
                    JOIN races r ON r.id = rr.race_id
                    JOIN race_sessions rs ON rs.race_id = r.id
                    JOIN session_entries se
                      ON se.session_id = rs.id
                     AND se.team_entity_id = csr.team_entity_id
                    WHERE rr.team_entity_id = csr.team_entity_id
                      AND r.season = :season
                      AND r.round <= latest.after_round
                    ORDER BY r.round DESC, rs.starts_at DESC
                    LIMIT 1
                ) team ON true
                WHERE e.id IS NOT NULL
                ORDER BY latest.after_round, csr.position
                """
            ),
            {"season": season},
        )

    rows = [dict(row) for row in result.mappings().all()]
    if not rows:
        raise VisualizationNotFoundError(f"{kind} not available for {season}")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    metadata: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row["entity_key"]
        point = {
            "round": row["round"],
            "position": row["position"],
            "points": float(row["points"]),
            "wins": row["wins"],
            "team_key": row["team_key"],
            "team_label": row["team_label"],
            "color": normalize_team_color(row["team_color"]),
        }
        grouped[key].append(point)
        metadata[key] = row

    series = []
    for key, points in sorted(grouped.items()):
        row = metadata[key]
        series.append(
            {
                "key": key,
                "label": row["entity_label"],
                "unit": "points",
                "driver_number": row["driver_number"],
                "driver_acronym": row["driver_acronym"],
                "classification_position": points[-1]["position"],
                "team_key": row["team_key"],
                "team_label": row["team_label"],
                "color": normalize_team_color(row["team_color"]),
                "points": sorted(points, key=lambda point: point["round"]),
            }
        )

    return VisualizationResponse(
        key=f"{season}:{kind}",
        chart_type="multi_panel",
        title=f"{season} — {kind.replace('-', ' ').title()}",
        x_axis=_axis("round", "Round", unit="round", formatter="integer"),
        y_axis=_axis("points", "Points", unit="points", formatter="raw"),
        presentation=_presentation(
            "championship-standings"
            if kind == "driver-standings"
            else "constructor-standings",
            show_annotations=False,
        ),
        series=series,
        annotations=[],
        provenance=_provenance(rows),
    )


async def driver_season_results(
    session: AsyncSession,
    season: int,
    driver_key: str,
) -> VisualizationResponse:
    driver_result = await session.execute(
        text(
            """
            SELECT id, slug, display_name
            FROM entities
            WHERE entity_type = 'person'
              AND metadata->>'kind' = 'driver'
              AND (slug = :driver_key OR id::text = :driver_key)
            LIMIT 1
            """
        ),
        {"driver_key": driver_key},
    )
    driver = driver_result.mappings().first()
    if driver is None:
        raise VisualizationNotFoundError(f"driver not found: {driver_key}")

    result = await session.execute(
        text(
            """
            SELECT r.round,
                   r.slug AS race_key,
                   r.official_name AS race_label,
                   rr.grid_position,
                   qr.position AS qualifying_position,
                   rr.finish_position,
                   rr.points,
                   rr.status,
                   rr.fastest_lap_rank,
                   rr.fastest_lap_number,
                   rr.fastest_lap_time,
                   rr.car_number AS driver_number,
                   team.slug AS team_key,
                   team.display_name AS team_label,
                   entry.team_colour AS team_color,
                   COALESCE(entry.name_acronym, code.alias) AS driver_acronym,
                   rr.provider AS provider,
                   rr.source_url AS source_url,
                   rr.fetched_at AS fetched_at,
                   'race_results'::text AS dataset,
                   qr.provider AS qualifying_provider,
                   qr.source_url AS qualifying_source_url,
                   qr.fetched_at AS qualifying_fetched_at
            FROM races r
            LEFT JOIN race_results rr
              ON rr.race_id = r.id
             AND rr.driver_entity_id = :driver_id
            LEFT JOIN qualifying_results qr
              ON qr.race_id = r.id
             AND qr.driver_entity_id = :driver_id
            LEFT JOIN entities team ON team.id = rr.team_entity_id
            LEFT JOIN LATERAL (
                SELECT se.team_colour, se.name_acronym
                FROM race_sessions rs
                JOIN session_entries se ON se.session_id = rs.id
                WHERE rs.race_id = r.id
                  AND se.driver_entity_id = :driver_id
                ORDER BY rs.starts_at DESC
                LIMIT 1
            ) entry ON true
            LEFT JOIN LATERAL (
                SELECT ea.alias
                FROM entity_aliases ea
                WHERE ea.entity_id = :driver_id
                  AND ea.alias_type = 'driver_code'
                  AND ea.enabled = true
                ORDER BY ea.confidence DESC
                LIMIT 1
            ) code ON true
            WHERE r.season = :season
              AND (rr.id IS NOT NULL OR qr.id IS NOT NULL)
            ORDER BY r.round
            """
        ),
        {"season": season, "driver_id": driver["id"]},
    )
    rows = [dict(row) for row in result.mappings().all()]
    if not rows:
        raise VisualizationNotFoundError(
            f"no results for {driver['slug']} in {season}"
        )

    latest = rows[-1]
    points = [
        {
            "round": row["round"],
            "race_key": row["race_key"],
            "race_label": row["race_label"],
            "grid_position": row["grid_position"],
            "qualifying_position": row["qualifying_position"],
            "finish_position": row["finish_position"],
            "points": float(row["points"]) if row["points"] is not None else None,
            "status": row["status"],
            "fastest_lap_rank": row["fastest_lap_rank"],
            "fastest_lap_number": row["fastest_lap_number"],
            "fastest_lap_time": row["fastest_lap_time"],
            "team_key": row["team_key"],
            "team_label": row["team_label"],
            "color": normalize_team_color(row["team_color"]),
        }
        for row in rows
    ]

    provenance_rows = list(rows)
    for row in rows:
        if row.get("qualifying_provider"):
            provenance_rows.append(
                {
                    "provider": row["qualifying_provider"],
                    "source_url": row["qualifying_source_url"],
                    "fetched_at": row["qualifying_fetched_at"],
                    "dataset": "qualifying_results",
                }
            )

    return VisualizationResponse(
        key=f'{season}:{driver["slug"]}:results',
        chart_type="multi_panel",
        title=f'{driver["display_name"]} — {season} season',
        x_axis=_axis("round", "Round", unit="round", formatter="integer"),
        y_axis=_axis(
            "position",
            "Position",
            unit="position",
            direction="reversed",
            formatter="position",
        ),
        presentation=_presentation(
            "driver-season-results",
            show_annotations=False,
        ),
        series=[
            {
                "key": driver["slug"],
                "label": driver["display_name"],
                "unit": "position",
                "driver_number": latest["driver_number"],
                "driver_acronym": latest["driver_acronym"],
                "team_key": latest["team_key"],
                "team_label": latest["team_label"],
                "color": normalize_team_color(latest["team_color"]),
                "points": points,
            }
        ],
        annotations=[],
        provenance=_provenance(provenance_rows),
    )
