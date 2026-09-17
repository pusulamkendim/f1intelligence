from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.context import (
    ContextFacet,
    ContextProvenance,
    ContextRelation,
    ContextResponse,
    ContextTarget,
    ContextTargetRef,
    ContextTargetType,
)


class ContextNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class ResolvedTarget:
    target: ContextTarget
    entity_id: Any | None = None
    resource_id: Any | None = None
    person_id: Any | None = None
    team_id: Any | None = None
    race_id: Any | None = None
    session_id: Any | None = None
    story_id: Any | None = None
    season: int | None = None


def _metadata(row: Any, *keys: str) -> dict[str, Any]:
    payload = dict(row.get("entity_metadata") or {})
    for key in keys:
        value = row.get(key)
        if value is not None:
            payload[key] = value
    return payload


def _target_ref(
    *,
    target_type: str,
    target_id: Any,
    key: str,
    label: str,
    subtype: str | None = None,
) -> ContextTargetRef:
    return ContextTargetRef(
        type=target_type,
        id=str(target_id),
        key=key,
        label=label,
        subtype=subtype,
    )


async def _first_mapping(db: AsyncSession, statement: str, params: dict[str, Any]) -> Any | None:
    result = await db.execute(text(statement), params)
    return result.mappings().first()


async def _resolve_driver(db: AsyncSession, key: str) -> ResolvedTarget:
    row = await _first_mapping(
        db,
        """
        SELECT
            e.id AS entity_id,
            e.slug,
            e.display_name,
            e.metadata AS entity_metadata,
            p.id AS person_id,
            p.nationality_code
        FROM entities e
        JOIN persons p ON p.entity_id = e.id
        WHERE e.entity_type = 'person'
          AND e.metadata->>'kind' = 'driver'
          AND (e.slug = :key OR e.id::text = :key)
        LIMIT 1
        """,
        {"key": key},
    )
    if row is None:
        raise ContextNotFoundError("Driver context not found")
    target = ContextTarget(
        type="driver",
        id=str(row["entity_id"]),
        key=row["slug"],
        slug=row["slug"],
        label=row["display_name"],
        subtype="driver",
        metadata=_metadata(row, "nationality_code"),
    )
    return ResolvedTarget(
        target=target,
        entity_id=row["entity_id"],
        resource_id=row["person_id"],
        person_id=row["person_id"],
    )


async def _resolve_team(db: AsyncSession, key: str) -> ResolvedTarget:
    row = await _first_mapping(
        db,
        """
        SELECT
            e.id AS entity_id,
            e.slug,
            e.display_name,
            e.metadata AS entity_metadata,
            t.id AS team_id,
            t.active_season
        FROM entities e
        JOIN teams t ON t.entity_id = e.id
        WHERE e.entity_type = 'team'
          AND (e.slug = :key OR e.id::text = :key)
        LIMIT 1
        """,
        {"key": key},
    )
    if row is None:
        raise ContextNotFoundError("Team context not found")
    target = ContextTarget(
        type="team",
        id=str(row["entity_id"]),
        key=row["slug"],
        slug=row["slug"],
        label=row["display_name"],
        season=row["active_season"],
        metadata=_metadata(row, "active_season"),
    )
    return ResolvedTarget(
        target=target,
        entity_id=row["entity_id"],
        resource_id=row["team_id"],
        team_id=row["team_id"],
        season=row["active_season"],
    )


async def _resolve_race(db: AsyncSession, key: str) -> ResolvedTarget:
    row = await _first_mapping(
        db,
        """
        SELECT
            e.id AS entity_id,
            e.slug,
            e.display_name,
            e.metadata AS entity_metadata,
            r.id AS race_id,
            r.season,
            r.round,
            r.official_name,
            r.circuit,
            r.country,
            r.status,
            r.start_at,
            r.provider,
            r.source_url,
            r.fetched_at
        FROM entities e
        JOIN races r ON r.entity_id = e.id
        WHERE e.entity_type = 'race'
          AND (e.slug = :key OR e.id::text = :key OR r.id::text = :key)
        LIMIT 1
        """,
        {"key": key},
    )
    if row is None:
        raise ContextNotFoundError("Race context not found")
    target = ContextTarget(
        type="race",
        id=str(row["entity_id"]),
        key=row["slug"],
        slug=row["slug"],
        label=row["display_name"],
        season=row["season"],
        metadata=_metadata(
            row,
            "round",
            "official_name",
            "circuit",
            "country",
            "status",
            "start_at",
        ),
    )
    return ResolvedTarget(
        target=target,
        entity_id=row["entity_id"],
        resource_id=row["race_id"],
        race_id=row["race_id"],
        season=row["season"],
    )


async def _resolve_session(db: AsyncSession, key: str) -> ResolvedTarget:
    row = await _first_mapping(
        db,
        """
        SELECT
            rs.id AS session_id,
            rs.session_code,
            rs.session_name,
            rs.session_type,
            rs.starts_at,
            rs.ends_at,
            rs.provider,
            rs.source_url,
            rs.fetched_at,
            r.id AS race_id,
            r.season,
            r.slug AS race_slug,
            r.entity_id AS race_entity_id,
            e.display_name AS race_label,
            r.slug || '-' || replace(rs.session_code, '_', '-') AS context_key
        FROM race_sessions rs
        JOIN races r ON r.id = rs.race_id
        LEFT JOIN entities e ON e.id = r.entity_id
        WHERE rs.id::text = :key
           OR r.slug || '-' || replace(rs.session_code, '_', '-') = :key
        LIMIT 1
        """,
        {"key": key},
    )
    if row is None:
        raise ContextNotFoundError("Session context not found")
    race_label = row["race_label"] or row["race_slug"]
    target = ContextTarget(
        type="session",
        id=str(row["session_id"]),
        key=row["context_key"],
        label=f"{race_label} · {row['session_name']}",
        subtype=row["session_code"],
        season=row["season"],
        metadata={
            "session_name": row["session_name"],
            "session_type": row["session_type"],
            "starts_at": row["starts_at"],
            "ends_at": row["ends_at"],
            "race_slug": row["race_slug"],
        },
    )
    return ResolvedTarget(
        target=target,
        resource_id=row["session_id"],
        race_id=row["race_id"],
        session_id=row["session_id"],
        season=row["season"],
    )


async def _resolve_season(db: AsyncSession, key: str) -> ResolvedTarget:
    try:
        season = int(key)
    except ValueError as exc:
        raise ContextNotFoundError("Season context not found") from exc
    row = await _first_mapping(
        db,
        """
        SELECT
            season,
            COUNT(*)::int AS race_count,
            MIN(weekend_start_date) AS starts_on,
            MAX(weekend_end_date) AS ends_on
        FROM races
        WHERE season = :season
        GROUP BY season
        """,
        {"season": season},
    )
    if row is None:
        raise ContextNotFoundError("Season context not found")
    target = ContextTarget(
        type="season",
        id=str(season),
        key=str(season),
        label=f"{season} Formula 1 season",
        season=season,
        metadata={
            "race_count": row["race_count"],
            "starts_on": row["starts_on"],
            "ends_on": row["ends_on"],
        },
    )
    return ResolvedTarget(target=target, season=season)


async def _resolve_story(db: AsyncSession, key: str) -> ResolvedTarget:
    row = await _first_mapping(
        db,
        """
        SELECT id, slug, title, status, significance, confidence, updated_at
        FROM stories
        WHERE slug = :key OR id::text = :key
        LIMIT 1
        """,
        {"key": key},
    )
    if row is None:
        raise ContextNotFoundError("Story context not found")
    target = ContextTarget(
        type="story",
        id=str(row["id"]),
        key=row["slug"],
        slug=row["slug"],
        label=row["title"],
        subtype=row["status"],
        metadata={
            "status": row["status"],
            "significance": row["significance"],
            "confidence": row["confidence"],
            "updated_at": row["updated_at"],
        },
    )
    return ResolvedTarget(target=target, resource_id=row["id"], story_id=row["id"])


async def resolve_target(db: AsyncSession, target_type: ContextTargetType, key: str) -> ResolvedTarget:
    resolvers = {
        "driver": _resolve_driver,
        "team": _resolve_team,
        "race": _resolve_race,
        "session": _resolve_session,
        "season": _resolve_season,
        "story": _resolve_story,
    }
    return await resolvers[target_type](db, key)


async def _driver_relations(db: AsyncSession, target: ResolvedTarget) -> list[ContextRelation]:
    result = await db.execute(
        text(
            """
            SELECT
                relation_type,
                target_id,
                target_key,
                target_label,
                season,
                source_url,
                session_count,
                first_session_at,
                last_session_at
            FROM (
                SELECT
                    'roster_driver_for'::text AS relation_type,
                    te.id AS target_id,
                    te.slug AS target_key,
                    te.display_name AS target_label,
                    tpr.season,
                    tpr.source_url,
                    NULL::int AS session_count,
                    NULL::timestamptz AS first_session_at,
                    NULL::timestamptz AS last_session_at
                FROM team_person_roles tpr
                JOIN persons p ON p.id = tpr.person_id
                JOIN teams t ON t.id = tpr.team_id
                JOIN entities te ON te.id = t.entity_id
                WHERE p.entity_id = :entity_id
                  AND tpr.role = 'driver'

                UNION ALL

                SELECT
                    'participated_for'::text AS relation_type,
                    te.id AS target_id,
                    te.slug AS target_key,
                    te.display_name AS target_label,
                    r.season,
                    NULL::text AS source_url,
                    COUNT(DISTINCT se.session_id)::int AS session_count,
                    MIN(rs.starts_at) AS first_session_at,
                    MAX(rs.starts_at) AS last_session_at
                FROM session_entries se
                JOIN race_sessions rs ON rs.id = se.session_id
                JOIN races r ON r.id = rs.race_id
                JOIN entities te ON te.id = se.team_entity_id
                WHERE se.driver_entity_id = :entity_id
                GROUP BY te.id, te.slug, te.display_name, r.season
            ) relations
            ORDER BY season DESC, relation_type, target_label
            """
        ),
        {"entity_id": target.entity_id},
    )
    relations: list[ContextRelation] = []
    for row in result.mappings().all():
        metadata = {
            key: row[key]
            for key in ("session_count", "first_session_at", "last_session_at")
            if row[key] is not None
        }
        relations.append(
            ContextRelation(
                type=row["relation_type"],
                target=_target_ref(
                    target_type="team",
                    target_id=row["target_id"],
                    key=row["target_key"],
                    label=row["target_label"],
                ),
                scope={"season": row["season"]},
                source=row["source_url"] or "session_entries",
                metadata=metadata,
            )
        )
    return relations


async def _team_relations(db: AsyncSession, target: ResolvedTarget) -> list[ContextRelation]:
    result = await db.execute(
        text(
            """
            SELECT
                relation_type,
                target_id,
                target_key,
                target_label,
                target_subtype,
                season,
                source_url,
                session_count
            FROM (
                SELECT
                    CASE
                        WHEN tpr.role = 'driver' THEN 'has_roster_driver'
                        ELSE 'has_team_member'
                    END::text AS relation_type,
                    pe.id AS target_id,
                    pe.slug AS target_key,
                    pe.display_name AS target_label,
                    pe.metadata->>'kind' AS target_subtype,
                    tpr.season,
                    tpr.source_url,
                    NULL::int AS session_count
                FROM team_person_roles tpr
                JOIN persons p ON p.id = tpr.person_id
                JOIN entities pe ON pe.id = p.entity_id
                WHERE tpr.team_id = :team_id

                UNION ALL

                SELECT
                    'fielded_driver'::text AS relation_type,
                    de.id AS target_id,
                    de.slug AS target_key,
                    de.display_name AS target_label,
                    'driver'::text AS target_subtype,
                    r.season,
                    NULL::text AS source_url,
                    COUNT(DISTINCT se.session_id)::int AS session_count
                FROM session_entries se
                JOIN race_sessions rs ON rs.id = se.session_id
                JOIN races r ON r.id = rs.race_id
                JOIN entities de ON de.id = se.driver_entity_id
                WHERE se.team_entity_id = :entity_id
                GROUP BY de.id, de.slug, de.display_name, r.season
            ) relations
            ORDER BY season DESC, relation_type, target_label
            """
        ),
        {"team_id": target.team_id, "entity_id": target.entity_id},
    )
    relations: list[ContextRelation] = []
    for row in result.mappings().all():
        target_type = "driver" if row["target_subtype"] == "driver" else "person"
        metadata = {"session_count": row["session_count"]} if row["session_count"] else {}
        relations.append(
            ContextRelation(
                type=row["relation_type"],
                target=_target_ref(
                    target_type=target_type,
                    target_id=row["target_id"],
                    key=row["target_key"],
                    label=row["target_label"],
                    subtype=row["target_subtype"],
                ),
                scope={"season": row["season"]},
                source=row["source_url"] or "session_entries",
                metadata=metadata,
            )
        )
    return relations


async def _race_relations(db: AsyncSession, target: ResolvedTarget) -> list[ContextRelation]:
    result = await db.execute(
        text(
            """
            SELECT
                rs.id,
                rs.session_code,
                rs.session_name,
                r.slug || '-' || replace(rs.session_code, '_', '-') AS context_key
            FROM race_sessions rs
            JOIN races r ON r.id = rs.race_id
            WHERE rs.race_id = :race_id
            ORDER BY rs.starts_at, rs.sequence NULLS LAST
            """
        ),
        {"race_id": target.race_id},
    )
    relations = [
        ContextRelation(
            type="has_session",
            target=_target_ref(
                target_type="session",
                target_id=row["id"],
                key=row["context_key"],
                label=row["session_name"],
                subtype=row["session_code"],
            ),
            scope={"season": target.season, "race_id": str(target.race_id)},
            source="race_sessions",
        )
        for row in result.mappings().all()
    ]
    relations.insert(
        0,
        ContextRelation(
            type="part_of_season",
            target=_target_ref(
                target_type="season",
                target_id=target.season,
                key=str(target.season),
                label=f"{target.season} Formula 1 season",
            ),
            scope={"season": target.season},
            source="races",
        ),
    )
    return relations


async def _session_relations(db: AsyncSession, target: ResolvedTarget) -> list[ContextRelation]:
    race_row = await _first_mapping(
        db,
        """
        SELECT r.entity_id, r.slug, e.display_name
        FROM races r
        LEFT JOIN entities e ON e.id = r.entity_id
        WHERE r.id = :race_id
        """,
        {"race_id": target.race_id},
    )
    relations: list[ContextRelation] = []
    if race_row is not None and race_row["entity_id"] is not None:
        relations.append(
            ContextRelation(
                type="part_of_race",
                target=_target_ref(
                    target_type="race",
                    target_id=race_row["entity_id"],
                    key=race_row["slug"],
                    label=race_row["display_name"] or race_row["slug"],
                ),
                scope={"season": target.season},
                source="race_sessions",
            )
        )
    relations.append(
        ContextRelation(
            type="part_of_season",
            target=_target_ref(
                target_type="season",
                target_id=target.season,
                key=str(target.season),
                label=f"{target.season} Formula 1 season",
            ),
            scope={"season": target.season},
            source="races",
        )
    )
    participant_result = await db.execute(
        text(
            """
            SELECT
                de.id AS driver_id,
                de.slug AS driver_key,
                de.display_name AS driver_label,
                te.id AS team_id,
                te.slug AS team_key,
                te.display_name AS team_label,
                se.driver_number
            FROM session_entries se
            JOIN entities de ON de.id = se.driver_entity_id
            LEFT JOIN entities te ON te.id = se.team_entity_id
            WHERE se.session_id = :session_id
            ORDER BY se.driver_number, de.display_name
            """
        ),
        {"session_id": target.session_id},
    )
    for row in participant_result.mappings().all():
        metadata: dict[str, Any] = {"driver_number": row["driver_number"]}
        if row["team_id"] is not None:
            metadata["team"] = {
                "type": "team",
                "id": str(row["team_id"]),
                "key": row["team_key"],
                "label": row["team_label"],
            }
        relations.append(
            ContextRelation(
                type="has_participant",
                target=_target_ref(
                    target_type="driver",
                    target_id=row["driver_id"],
                    key=row["driver_key"],
                    label=row["driver_label"],
                    subtype="driver",
                ),
                scope={"season": target.season, "session_id": str(target.session_id)},
                source="session_entries",
                metadata=metadata,
            )
        )
    return relations


async def _season_relations(db: AsyncSession, target: ResolvedTarget) -> list[ContextRelation]:
    result = await db.execute(
        text(
            """
            SELECT r.entity_id, r.slug, e.display_name, r.round
            FROM races r
            JOIN entities e ON e.id = r.entity_id
            WHERE r.season = :season
            ORDER BY r.round NULLS LAST, r.start_at NULLS LAST
            """
        ),
        {"season": target.season},
    )
    return [
        ContextRelation(
            type="has_race",
            target=_target_ref(
                target_type="race",
                target_id=row["entity_id"],
                key=row["slug"],
                label=row["display_name"],
            ),
            scope={"season": target.season, "round": row["round"]},
            source="races",
        )
        for row in result.mappings().all()
    ]


async def _story_relations(db: AsyncSession, target: ResolvedTarget) -> list[ContextRelation]:
    result = await db.execute(
        text(
            """
            SELECT
                e.id,
                e.entity_type,
                e.slug,
                e.display_name,
                e.metadata->>'kind' AS kind,
                se.relation_type,
                se.confidence,
                se.match_method,
                se.matched_alias
            FROM story_entities se
            JOIN entities e ON e.id = se.entity_id
            WHERE se.story_id = :story_id
            ORDER BY se.confidence DESC, e.display_name
            """
        ),
        {"story_id": target.story_id},
    )
    relations: list[ContextRelation] = []
    for row in result.mappings().all():
        target_type = row["entity_type"]
        if row["entity_type"] == "person" and row["kind"] == "driver":
            target_type = "driver"
        relations.append(
            ContextRelation(
                type=row["relation_type"],
                target=_target_ref(
                    target_type=target_type,
                    target_id=row["id"],
                    key=row["slug"],
                    label=row["display_name"],
                    subtype=row["kind"],
                ),
                source="story_entities",
                metadata={
                    "confidence": row["confidence"],
                    "match_method": row["match_method"],
                    "matched_alias": row["matched_alias"],
                },
            )
        )
    return relations


async def load_relations(db: AsyncSession, target: ResolvedTarget) -> list[ContextRelation]:
    loaders = {
        "driver": _driver_relations,
        "team": _team_relations,
        "race": _race_relations,
        "session": _session_relations,
        "season": _season_relations,
        "story": _story_relations,
    }
    return await loaders[target.target.type](db, target)


FACET_SQL: dict[str, str] = {
    "driver": """
        SELECT
            (SELECT COUNT(*) FROM race_results WHERE driver_entity_id = :entity_id)::int AS race_results,
            (SELECT COUNT(*) FROM qualifying_results WHERE driver_entity_id = :entity_id)::int AS qualifying_results,
            (SELECT COUNT(*) FROM session_results WHERE driver_entity_id = :entity_id)::int AS session_results,
            (SELECT COUNT(*) FROM session_laps WHERE driver_entity_id = :entity_id)::int AS laps,
            (SELECT COUNT(*) FROM session_stints WHERE driver_entity_id = :entity_id)::int AS stints,
            (SELECT COUNT(*) FROM session_positions WHERE driver_entity_id = :entity_id)::int AS positions,
            (SELECT COUNT(*) FROM session_intervals WHERE driver_entity_id = :entity_id)::int AS intervals,
            (SELECT COUNT(*) FROM session_pit_stops WHERE driver_entity_id = :entity_id)::int AS pit_stops,
            (SELECT COUNT(*) FROM session_starting_grid WHERE driver_entity_id = :entity_id)::int AS starting_grid,
            (SELECT COUNT(*) FROM session_overtakes
             WHERE overtaking_driver_entity_id = :entity_id OR overtaken_driver_entity_id = :entity_id)::int AS overtakes,
            (SELECT COUNT(*) FROM driver_standing_rows WHERE driver_entity_id = :entity_id)::int AS standings,
            (SELECT COUNT(*) FROM story_entities WHERE entity_id = :entity_id)::int AS stories,
            (SELECT COUNT(*) FROM race_document_entities WHERE entity_id = :entity_id)::int AS documents,
            (SELECT COUNT(*) FROM evidence WHERE driver_entity_id = :entity_id)::int AS evidence
    """,
    "team": """
        SELECT
            (SELECT COUNT(*) FROM race_results WHERE team_entity_id = :entity_id)::int AS race_results,
            (SELECT COUNT(*) FROM qualifying_results WHERE team_entity_id = :entity_id)::int AS qualifying_results,
            (SELECT COUNT(*) FROM session_results WHERE team_entity_id = :entity_id)::int AS session_results,
            (SELECT COUNT(*) FROM session_entries WHERE team_entity_id = :entity_id)::int AS session_entries,
            (SELECT COUNT(*) FROM session_starting_grid WHERE team_entity_id = :entity_id)::int AS starting_grid,
            (SELECT COUNT(*) FROM constructor_standing_rows WHERE team_entity_id = :entity_id)::int AS standings,
            (SELECT COUNT(*) FROM story_entities WHERE entity_id = :entity_id)::int AS stories,
            (SELECT COUNT(*) FROM race_document_entities WHERE entity_id = :entity_id)::int AS documents,
            (SELECT COUNT(*) FROM evidence WHERE team_entity_id = :entity_id)::int AS evidence
    """,
    "race": """
        SELECT
            (SELECT COUNT(*) FROM race_sessions WHERE race_id = :race_id)::int AS sessions,
            (SELECT COUNT(*) FROM race_results WHERE race_id = :race_id)::int AS race_results,
            (SELECT COUNT(*) FROM qualifying_results WHERE race_id = :race_id)::int AS qualifying_results,
            (SELECT COUNT(*) FROM session_results sr JOIN race_sessions rs ON rs.id = sr.session_id
             WHERE rs.race_id = :race_id)::int AS session_results,
            (SELECT COUNT(*) FROM session_laps sl JOIN race_sessions rs ON rs.id = sl.session_id
             WHERE rs.race_id = :race_id)::int AS laps,
            (SELECT COUNT(*) FROM session_stints ss JOIN race_sessions rs ON rs.id = ss.session_id
             WHERE rs.race_id = :race_id)::int AS stints,
            (SELECT COUNT(*) FROM session_positions sp JOIN race_sessions rs ON rs.id = sp.session_id
             WHERE rs.race_id = :race_id)::int AS positions,
            (SELECT COUNT(*) FROM session_intervals si JOIN race_sessions rs ON rs.id = si.session_id
             WHERE rs.race_id = :race_id)::int AS intervals,
            (SELECT COUNT(*) FROM session_pit_stops ps JOIN race_sessions rs ON rs.id = ps.session_id
             WHERE rs.race_id = :race_id)::int AS pit_stops,
            (SELECT COUNT(*) FROM session_starting_grid sg JOIN race_sessions rs ON rs.id = sg.session_id
             WHERE rs.race_id = :race_id)::int AS starting_grid,
            (SELECT COUNT(*) FROM session_overtakes so JOIN race_sessions rs ON rs.id = so.session_id
             WHERE rs.race_id = :race_id)::int AS overtakes,
            (SELECT COUNT(*) FROM session_race_control_events rc JOIN race_sessions rs ON rs.id = rc.session_id
             WHERE rs.race_id = :race_id)::int AS race_control,
            (SELECT COUNT(*) FROM session_weather sw JOIN race_sessions rs ON rs.id = sw.session_id
             WHERE rs.race_id = :race_id)::int AS weather,
            (SELECT COUNT(*) FROM race_documents WHERE race_id = :race_id)::int AS documents,
            (SELECT COUNT(*) FROM story_entities WHERE entity_id = :entity_id)::int AS stories,
            (SELECT COUNT(*) FROM evidence WHERE race_id = :race_id)::int AS evidence
    """,
    "session": """
        SELECT
            (SELECT COUNT(*) FROM session_entries WHERE session_id = :session_id)::int AS entries,
            (SELECT COUNT(*) FROM session_results WHERE session_id = :session_id)::int AS results,
            (SELECT COUNT(*) FROM session_laps WHERE session_id = :session_id)::int AS laps,
            (SELECT COUNT(*) FROM session_stints WHERE session_id = :session_id)::int AS stints,
            (SELECT COUNT(*) FROM session_positions WHERE session_id = :session_id)::int AS positions,
            (SELECT COUNT(*) FROM session_intervals WHERE session_id = :session_id)::int AS intervals,
            (SELECT COUNT(*) FROM session_pit_stops WHERE session_id = :session_id)::int AS pit_stops,
            (SELECT COUNT(*) FROM session_starting_grid WHERE session_id = :session_id)::int AS starting_grid,
            (SELECT COUNT(*) FROM session_overtakes WHERE session_id = :session_id)::int AS overtakes,
            (SELECT COUNT(*) FROM session_race_control_events WHERE session_id = :session_id)::int AS race_control,
            (SELECT COUNT(*) FROM session_weather WHERE session_id = :session_id)::int AS weather,
            (SELECT COUNT(*) FROM evidence WHERE session_id = :session_id)::int AS evidence
    """,
    "season": """
        SELECT
            (SELECT COUNT(*) FROM races WHERE season = :season)::int AS races,
            (SELECT COUNT(*) FROM race_results rr JOIN races r ON r.id = rr.race_id
             WHERE r.season = :season)::int AS race_results,
            (SELECT COUNT(*) FROM qualifying_results qr JOIN races r ON r.id = qr.race_id
             WHERE r.season = :season)::int AS qualifying_results,
            (SELECT COUNT(*) FROM race_sessions rs JOIN races r ON r.id = rs.race_id
             WHERE r.season = :season)::int AS sessions,
            (SELECT COUNT(*) FROM session_results sr JOIN race_sessions rs ON rs.id = sr.session_id
             JOIN races r ON r.id = rs.race_id WHERE r.season = :season)::int AS session_results,
            (SELECT COUNT(*) FROM race_documents rd JOIN races r ON r.id = rd.race_id
             WHERE r.season = :season)::int AS documents,
            (SELECT COUNT(DISTINCT se.story_id) FROM story_entities se JOIN races r ON r.entity_id = se.entity_id
             WHERE r.season = :season)::int AS stories
    """,
    "story": """
        SELECT
            (SELECT COUNT(*) FROM evidence WHERE story_id = :story_id)::int AS evidence,
            (SELECT COUNT(*) FROM story_entities WHERE story_id = :story_id)::int AS entities,
            (SELECT COUNT(*) FROM publication_stories WHERE story_id = :story_id)::int AS publications
    """,
}


async def load_facets(db: AsyncSession, target: ResolvedTarget) -> list[ContextFacet]:
    params = {
        "entity_id": target.entity_id,
        "race_id": target.race_id,
        "session_id": target.session_id,
        "story_id": target.story_id,
        "season": target.season,
    }
    result = await db.execute(text(FACET_SQL[target.target.type]), params)
    row = result.mappings().first()
    if row is None:
        return []
    return [
        ContextFacet(type=facet_type, count=int(count))
        for facet_type, count in row.items()
        if count is not None and int(count) > 0
    ]


async def load_provenance(db: AsyncSession, target: ResolvedTarget) -> list[ContextProvenance]:
    if target.target.type in {"driver", "team"}:
        result = await db.execute(
            text(
                """
                SELECT provider, source_url, updated_at AS fetched_at,
                       jsonb_build_object('provider_entity_type', provider_entity_type,
                                          'provider_id', provider_id) AS metadata
                FROM entity_provider_ids
                WHERE entity_id = :entity_id
                ORDER BY provider, provider_id
                """
            ),
            {"entity_id": target.entity_id},
        )
    elif target.target.type == "race":
        result = await db.execute(
            text(
                """
                SELECT provider, source_url, fetched_at, '{}'::jsonb AS metadata
                FROM races
                WHERE id = :race_id
                """
            ),
            {"race_id": target.race_id},
        )
    elif target.target.type == "session":
        result = await db.execute(
            text(
                """
                SELECT provider, source_url, fetched_at,
                       jsonb_build_object('provider_session_id', provider_session_id,
                                          'provider_meeting_id', provider_meeting_id) AS metadata
                FROM race_sessions
                WHERE id = :session_id
                """
            ),
            {"session_id": target.session_id},
        )
    else:
        return []

    provenance: list[ContextProvenance] = []
    for row in result.mappings().all():
        fetched_at = row["fetched_at"]
        provenance.append(
            ContextProvenance(
                provider=row["provider"],
                source_url=row["source_url"],
                fetched_at=fetched_at.isoformat() if fetched_at is not None else None,
                metadata=dict(row["metadata"] or {}),
            )
        )
    return provenance


async def build_context(
    db: AsyncSession,
    target_type: ContextTargetType,
    key: str,
) -> ContextResponse:
    target = await resolve_target(db, target_type, key)
    relations = await load_relations(db, target)
    facets = await load_facets(db, target)
    provenance = await load_provenance(db, target)
    return ContextResponse(
        target=target.target,
        relations=relations,
        facets=facets,
        provenance=provenance,
    )
