from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.timeline import (
    TimelineCoordinate,
    TimelineItem,
    TimelineProvenance,
    UnifiedTimelineResponse,
)


async def _resolve_race(db: AsyncSession, season: int, race_key: str | None):
    if race_key is None:
        return None
    result = await db.execute(
        text(
            """
            SELECT id, entity_id, slug, official_name, start_at, weekend_start_date
            FROM races
            WHERE season = :season AND slug = :race_key
            LIMIT 1
            """
        ),
        {"season": season, "race_key": race_key},
    )
    return result.mappings().first()


async def _resolve_session(
    db: AsyncSession,
    race_id: UUID | None,
    session_code: str | None,
):
    if race_id is None or session_code is None:
        return None
    result = await db.execute(
        text(
            """
            SELECT id, session_code, session_name, starts_at, ends_at
            FROM race_sessions
            WHERE race_id = :race_id
              AND session_code = :session_code
              AND is_cancelled = false
            LIMIT 1
            """
        ),
        {"race_id": race_id, "session_code": session_code},
    )
    return result.mappings().first()


async def _resolve_driver(db: AsyncSession, driver_key: str | None):
    if driver_key is None:
        return None
    result = await db.execute(
        text(
            """
            SELECT id, slug, display_name
            FROM entities
            WHERE entity_type = 'person' AND slug = :driver_key
            LIMIT 1
            """
        ),
        {"driver_key": driver_key},
    )
    return result.mappings().first()


def _coordinate(row: Any) -> TimelineCoordinate:
    return TimelineCoordinate(
        season=row["season"],
        race_id=str(row["race_id"]) if row.get("race_id") else None,
        race_key=row.get("race_key"),
        race_label=row.get("race_label"),
        session_id=str(row["session_id"]) if row.get("session_id") else None,
        session_code=row.get("session_code"),
        session_label=row.get("session_label"),
        driver_id=str(row["driver_id"]) if row.get("driver_id") else None,
        driver_key=row.get("driver_key"),
        driver_label=row.get("driver_label"),
        stint_number=row.get("stint_number"),
        lap_number=row.get("lap_number"),
    )


def _provenance(row: Any) -> TimelineProvenance | None:
    if not row.get("provider") and not row.get("source_url") and not row.get("fetched_at"):
        return None
    return TimelineProvenance(
        provider=row.get("provider"),
        source_url=row.get("source_url"),
        fetched_at=row.get("fetched_at"),
    )


def _timeline_item(row: Any) -> TimelineItem:
    return TimelineItem(
        id=str(row["event_id"]),
        type=row["event_type"],
        label=row["label"],
        timeline_at=row.get("timeline_at"),
        reported_at=row.get("reported_at"),
        temporal_relation=row["temporal_relation"],
        precision=row["precision"],
        coordinate=_coordinate(row),
        source=row["source"],
        metadata=dict(row.get("metadata") or {}),
        provenance=_provenance(row),
    )


def _placement_sql(
    *,
    race_filter: bool,
    session_filter: bool,
    driver_filter: bool,
    lap_filter: bool,
) -> str:
    clauses = ["p.season = :season", "p.is_primary = true"]
    if race_filter:
        clauses.append("p.race_id = :race_id")
    if session_filter:
        clauses.append("p.session_id = :session_id")
    if driver_filter:
        clauses.append(
            """(
                p.driver_entity_id = :driver_id
                OR (
                    p.item_type = 'story'
                    AND EXISTS (
                        SELECT 1 FROM story_entities se
                        WHERE se.story_id = p.item_id
                          AND se.entity_id = :driver_id
                    )
                )
            )"""
        )
    if lap_filter:
        clauses.append("p.lap_number = :lap_number")

    where = " AND ".join(clauses)
    return f"""
        SELECT
            ('placement:' || p.id::text) AS event_id,
            p.item_type AS event_type,
            COALESCE(s.title, p.item_type || ' ' || p.item_id::text) AS label,
            p.timeline_at,
            p.reported_at,
            p.temporal_relation,
            p.precision,
            p.season,
            p.race_id,
            r.slug AS race_key,
            r.official_name AS race_label,
            p.session_id,
            rs.session_code,
            rs.session_name AS session_label,
            p.driver_entity_id AS driver_id,
            de.slug AS driver_key,
            de.display_name AS driver_label,
            p.stint_number,
            p.lap_number,
            'timeline_placements'::text AS source,
            primary_source.provider,
            primary_source.source_url,
            primary_source.fetched_at,
            jsonb_strip_nulls(
                p.metadata || jsonb_build_object(
                    'item_id', p.item_id,
                    'confidence', p.confidence,
                    'match_method', p.match_method,
                    'story_key', s.slug,
                    'story_status', s.status
                )
            ) AS metadata
        FROM timeline_placements p
        LEFT JOIN stories s
          ON p.item_type = 'story' AND s.id = p.item_id
        LEFT JOIN races r ON r.id = p.race_id
        LEFT JOIN race_sessions rs ON rs.id = p.session_id
        LEFT JOIN entities de ON de.id = p.driver_entity_id
        LEFT JOIN LATERAL (
            SELECT si.provider, si.source_url, si.fetched_at
            FROM story_source_items ssi
            JOIN source_items si ON si.id = ssi.source_item_id
            WHERE p.item_type = 'story'
              AND ssi.story_id = p.item_id
            ORDER BY CASE WHEN ssi.relation_type = 'primary' THEN 0 ELSE 1 END,
                     si.fetched_at DESC
            LIMIT 1
        ) primary_source ON true
        WHERE {where}
          AND (s.id IS NULL OR s.merged_into_story_id IS NULL)
    """


async def _load_placements(
    db: AsyncSession,
    *,
    season: int,
    race_id: UUID | None,
    session_id: UUID | None,
    driver_id: UUID | None,
    lap_number: int | None,
) -> list[TimelineItem]:
    result = await db.execute(
        text(
            _placement_sql(
                race_filter=race_id is not None,
                session_filter=session_id is not None,
                driver_filter=driver_id is not None,
                lap_filter=lap_number is not None,
            )
        ),
        {
            "season": season,
            "race_id": race_id,
            "session_id": session_id,
            "driver_id": driver_id,
            "lap_number": lap_number,
        },
    )
    return [_timeline_item(row) for row in result.mappings().all()]


async def _load_season_races(db: AsyncSession, season: int) -> list[TimelineItem]:
    result = await db.execute(
        text(
            """
            SELECT
                ('race:' || r.id::text) AS event_id,
                'race'::text AS event_type,
                r.official_name AS label,
                COALESCE(r.start_at, r.weekend_start_date::timestamptz) AS timeline_at,
                NULL::timestamptz AS reported_at,
                CASE
                    WHEN COALESCE(r.start_at, r.weekend_start_date::timestamptz) > now()
                    THEN 'scheduled_for'::text
                    ELSE 'occurred_at'::text
                END AS temporal_relation,
                'race'::text AS precision,
                r.season,
                r.id AS race_id,
                r.slug AS race_key,
                r.official_name AS race_label,
                NULL::uuid AS session_id,
                NULL::text AS session_code,
                NULL::text AS session_label,
                NULL::uuid AS driver_id,
                NULL::text AS driver_key,
                NULL::text AS driver_label,
                NULL::int AS stint_number,
                NULL::int AS lap_number,
                'races'::text AS source,
                r.provider,
                r.source_url,
                r.fetched_at,
                jsonb_strip_nulls(jsonb_build_object(
                    'round', r.round,
                    'circuit', r.circuit,
                    'country', r.country,
                    'status', r.status
                )) AS metadata
            FROM races r
            WHERE r.season = :season
            ORDER BY r.round NULLS LAST, timeline_at NULLS LAST
            """
        ),
        {"season": season},
    )
    return [_timeline_item(row) for row in result.mappings().all()]


async def _load_race_sessions(
    db: AsyncSession,
    *,
    season: int,
    race_id: UUID,
    race_key: str,
    race_label: str,
) -> list[TimelineItem]:
    result = await db.execute(
        text(
            """
            SELECT
                ('session:' || rs.id::text) AS event_id,
                'session'::text AS event_type,
                rs.session_name AS label,
                rs.starts_at AS timeline_at,
                NULL::timestamptz AS reported_at,
                CASE WHEN rs.starts_at > now()
                    THEN 'scheduled_for'::text ELSE 'occurred_at'::text END
                    AS temporal_relation,
                'session'::text AS precision,
                :season AS season,
                :race_id AS race_id,
                :race_key AS race_key,
                :race_label AS race_label,
                rs.id AS session_id,
                rs.session_code,
                rs.session_name AS session_label,
                NULL::uuid AS driver_id,
                NULL::text AS driver_key,
                NULL::text AS driver_label,
                NULL::int AS stint_number,
                NULL::int AS lap_number,
                'race_sessions'::text AS source,
                rs.provider,
                rs.source_url,
                rs.fetched_at,
                jsonb_strip_nulls(jsonb_build_object(
                    'ends_at', rs.ends_at,
                    'session_type', rs.session_type,
                    'sequence', rs.sequence
                )) AS metadata
            FROM race_sessions rs
            WHERE rs.race_id = :race_id
              AND rs.is_cancelled = false
            ORDER BY rs.starts_at
            """
        ),
        {
            "season": season,
            "race_id": race_id,
            "race_key": race_key,
            "race_label": race_label,
        },
    )
    return [_timeline_item(row) for row in result.mappings().all()]


async def _load_session_events(
    db: AsyncSession,
    *,
    season: int,
    race: Any,
    session_row: Any,
    driver_id: UUID | None,
    lap_number: int | None,
) -> list[TimelineItem]:
    params = {
        "season": season,
        "race_id": race["id"],
        "race_key": race["slug"],
        "race_label": race["official_name"],
        "session_id": session_row["id"],
        "session_code": session_row["session_code"],
        "session_label": session_row["session_name"],
        "driver_id": driver_id,
        "lap_number": lap_number,
    }
    driver_clause_rc = ""
    driver_clause_pit = ""
    driver_clause_ot = ""
    lap_clause_rc = ""
    lap_clause_pit = ""
    if driver_id is not None:
        driver_clause_rc = "AND rc.driver_entity_id = :driver_id"
        driver_clause_pit = "AND ps.driver_entity_id = :driver_id"
        driver_clause_ot = "AND (so.overtaking_driver_entity_id = :driver_id OR so.overtaken_driver_entity_id = :driver_id)"
    if lap_number is not None:
        lap_clause_rc = "AND rc.lap_number = :lap_number"
        lap_clause_pit = "AND ps.lap_number = :lap_number"

    sql = f"""
        SELECT
            ('race-control:' || rc.id::text) AS event_id,
            'race_control'::text AS event_type,
            rc.message AS label,
            rc.observed_at AS timeline_at,
            NULL::timestamptz AS reported_at,
            'occurred_at'::text AS temporal_relation,
            CASE WHEN rc.lap_number IS NULL THEN 'timestamp'::text ELSE 'lap'::text END AS precision,
            :season AS season,
            :race_id AS race_id,
            :race_key AS race_key,
            :race_label AS race_label,
            :session_id AS session_id,
            :session_code AS session_code,
            :session_label AS session_label,
            rc.driver_entity_id AS driver_id,
            de.slug AS driver_key,
            de.display_name AS driver_label,
            NULL::int AS stint_number,
            rc.lap_number,
            'session_race_control_events'::text AS source,
            rc.provider,
            rc.source_url,
            rc.fetched_at,
            jsonb_strip_nulls(jsonb_build_object(
                'category', rc.category,
                'flag', rc.flag,
                'scope', rc.scope,
                'sector', rc.sector
            )) AS metadata
        FROM session_race_control_events rc
        LEFT JOIN entities de ON de.id = rc.driver_entity_id
        WHERE rc.session_id = :session_id
        {driver_clause_rc}
        {lap_clause_rc}

        UNION ALL

        SELECT
            ('pit-stop:' || ps.id::text),
            'pit_stop'::text,
            COALESCE(de.display_name, 'Driver ' || ps.provider_driver_number::text)
                || ' pit stop',
            ps.observed_at,
            NULL::timestamptz,
            'occurred_at'::text,
            'lap'::text,
            :season,
            :race_id,
            :race_key,
            :race_label,
            :session_id,
            :session_code,
            :session_label,
            ps.driver_entity_id,
            de.slug,
            de.display_name,
            NULL::int,
            ps.lap_number,
            'session_pit_stops'::text,
            ps.provider,
            ps.source_url,
            ps.fetched_at,
            jsonb_strip_nulls(jsonb_build_object(
                'lane_duration_seconds', ps.lane_duration_seconds,
                'stop_duration_seconds', ps.stop_duration_seconds
            ))
        FROM session_pit_stops ps
        LEFT JOIN entities de ON de.id = ps.driver_entity_id
        WHERE ps.session_id = :session_id
        {driver_clause_pit}
        {lap_clause_pit}

        UNION ALL

        SELECT
            ('overtake:' || so.id::text),
            'overtake'::text,
            COALESCE(od.display_name, 'Driver ' || so.overtaking_driver_number::text)
                || ' overtook '
                || COALESCE(dd.display_name, 'Driver ' || so.overtaken_driver_number::text),
            so.observed_at,
            NULL::timestamptz,
            'occurred_at'::text,
            'timestamp'::text,
            :season,
            :race_id,
            :race_key,
            :race_label,
            :session_id,
            :session_code,
            :session_label,
            so.overtaking_driver_entity_id,
            od.slug,
            od.display_name,
            NULL::int,
            NULL::int,
            'session_overtakes'::text,
            so.provider,
            so.source_url,
            so.fetched_at,
            jsonb_strip_nulls(jsonb_build_object(
                'position', so.position,
                'overtaken_driver_key', dd.slug,
                'overtaken_driver_name', dd.display_name
            ))
        FROM session_overtakes so
        LEFT JOIN entities od ON od.id = so.overtaking_driver_entity_id
        LEFT JOIN entities dd ON dd.id = so.overtaken_driver_entity_id
        WHERE so.session_id = :session_id
        {driver_clause_ot}
    """
    result = await db.execute(text(sql), params)
    return [_timeline_item(row) for row in result.mappings().all()]


async def _load_driver_laps_and_stints(
    db: AsyncSession,
    *,
    season: int,
    race: Any,
    session_row: Any,
    driver: Any,
    lap_number: int | None,
) -> list[TimelineItem]:
    lap_clause = "AND sl.lap_number = :lap_number" if lap_number is not None else ""
    stint_clause = (
        "AND :lap_number BETWEEN ss.lap_start AND ss.lap_end"
        if lap_number is not None
        else ""
    )
    result = await db.execute(
        text(
            f"""
            SELECT
                ('lap:' || sl.id::text) AS event_id,
                'lap'::text AS event_type,
                de.display_name || ' · lap ' || sl.lap_number::text AS label,
                COALESCE(sl.started_at, rs.starts_at) AS timeline_at,
                NULL::timestamptz AS reported_at,
                'occurred_at'::text AS temporal_relation,
                'lap'::text AS precision,
                :season AS season,
                :race_id AS race_id,
                :race_key AS race_key,
                :race_label AS race_label,
                :session_id AS session_id,
                :session_code AS session_code,
                :session_label AS session_label,
                sl.driver_entity_id AS driver_id,
                de.slug AS driver_key,
                de.display_name AS driver_label,
                NULL::int AS stint_number,
                sl.lap_number,
                'session_laps'::text AS source,
                sl.provider,
                sl.source_url,
                sl.fetched_at,
                jsonb_strip_nulls(jsonb_build_object(
                    'lap_duration_seconds', sl.lap_duration_seconds,
                    'is_pit_out_lap', sl.is_pit_out_lap,
                    'sector_1_duration_seconds', sl.sector_1_duration_seconds,
                    'sector_2_duration_seconds', sl.sector_2_duration_seconds,
                    'sector_3_duration_seconds', sl.sector_3_duration_seconds
                )) AS metadata
            FROM session_laps sl
            JOIN race_sessions rs ON rs.id = sl.session_id
            JOIN entities de ON de.id = sl.driver_entity_id
            WHERE sl.session_id = :session_id
              AND sl.driver_entity_id = :driver_id
            {lap_clause}

            UNION ALL

            SELECT
                ('stint:' || ss.id::text),
                'stint'::text,
                de.display_name || ' · stint ' || ss.stint_number::text,
                COALESCE(anchor.started_at, rs.starts_at),
                NULL::timestamptz,
                'occurred_at'::text,
                'stint'::text,
                :season,
                :race_id,
                :race_key,
                :race_label,
                :session_id,
                :session_code,
                :session_label,
                ss.driver_entity_id,
                de.slug,
                de.display_name,
                ss.stint_number,
                ss.lap_start,
                'session_stints'::text,
                ss.provider,
                ss.source_url,
                ss.fetched_at,
                jsonb_strip_nulls(jsonb_build_object(
                    'lap_start', ss.lap_start,
                    'lap_end', ss.lap_end,
                    'compound', ss.compound,
                    'tyre_age_at_start', ss.tyre_age_at_start
                ))
            FROM session_stints ss
            JOIN race_sessions rs ON rs.id = ss.session_id
            JOIN entities de ON de.id = ss.driver_entity_id
            LEFT JOIN LATERAL (
                SELECT sl.started_at
                FROM session_laps sl
                WHERE sl.session_id = ss.session_id
                  AND sl.driver_entity_id = ss.driver_entity_id
                  AND sl.lap_number = ss.lap_start
                LIMIT 1
            ) anchor ON true
            WHERE ss.session_id = :session_id
              AND ss.driver_entity_id = :driver_id
            {stint_clause}
            """
        ),
        {
            "season": season,
            "race_id": race["id"],
            "race_key": race["slug"],
            "race_label": race["official_name"],
            "session_id": session_row["id"],
            "session_code": session_row["session_code"],
            "session_label": session_row["session_name"],
            "driver_id": driver["id"],
            "lap_number": lap_number,
        },
    )
    return [_timeline_item(row) for row in result.mappings().all()]


def _sort_key(item: TimelineItem) -> tuple[int, float, int, int, str]:
    timestamp = item.timeline_at or item.reported_at
    numeric_time = timestamp.timestamp() if isinstance(timestamp, datetime) else 0.0
    return (
        1 if timestamp is None else 0,
        numeric_time,
        item.coordinate.lap_number or 0,
        item.coordinate.stint_number or 0,
        item.id,
    )


async def build_unified_timeline(
    db: AsyncSession,
    *,
    season: int,
    race_key: str | None = None,
    session_code: str | None = None,
    driver_key: str | None = None,
    lap_number: int | None = None,
    limit: int = 200,
) -> UnifiedTimelineResponse:
    race = await _resolve_race(db, season, race_key)
    if race_key is not None and race is None:
        return UnifiedTimelineResponse(
            season=season,
            race_key=race_key,
            session_code=session_code,
            driver_key=driver_key,
            lap_number=lap_number,
            items=[],
        )

    session_row = await _resolve_session(
        db,
        race["id"] if race else None,
        session_code,
    )
    driver = await _resolve_driver(db, driver_key)

    items: list[TimelineItem] = []
    if race is None:
        items.extend(await _load_season_races(db, season))
    elif session_row is None:
        items.extend(
            await _load_race_sessions(
                db,
                season=season,
                race_id=race["id"],
                race_key=race["slug"],
                race_label=race["official_name"],
            )
        )
    else:
        items.extend(
            await _load_session_events(
                db,
                season=season,
                race=race,
                session_row=session_row,
                driver_id=driver["id"] if driver else None,
                lap_number=lap_number,
            )
        )
        if driver is not None:
            items.extend(
                await _load_driver_laps_and_stints(
                    db,
                    season=season,
                    race=race,
                    session_row=session_row,
                    driver=driver,
                    lap_number=lap_number,
                )
            )

    items.extend(
        await _load_placements(
            db,
            season=season,
            race_id=race["id"] if race else None,
            session_id=session_row["id"] if session_row else None,
            driver_id=driver["id"] if driver else None,
            lap_number=lap_number,
        )
    )
    items.sort(key=_sort_key)

    return UnifiedTimelineResponse(
        season=season,
        race_key=race_key,
        session_code=session_code,
        driver_key=driver_key,
        lap_number=lap_number,
        items=items[:limit],
    )
