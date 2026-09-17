from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.resolver import ResolvedTarget
from app.schemas.context import (
    ContextProvenance,
    ContextRelation,
    ContextTargetRef,
    ContextTimelineEvent,
)

TIMELINE_LIMIT = 30
PER_TYPE_LIMIT = 12
RELATED_LIMIT = 12


def _timeline_sql(events_sql: str) -> str:
    return f"""
        WITH events AS (
            {events_sql}
        ), ranked AS (
            SELECT
                events.*,
                row_number() OVER (
                    PARTITION BY event_type
                    ORDER BY occurred_at DESC NULLS LAST, event_id
                ) AS type_rank
            FROM events
            WHERE occurred_at IS NOT NULL
        )
        SELECT
            event_id,
            event_type,
            occurred_at,
            label,
            target_type,
            target_id,
            target_key,
            target_label,
            target_subtype,
            provider,
            source_url,
            fetched_at,
            metadata
        FROM ranked
        WHERE type_rank <= :per_type_limit
        ORDER BY occurred_at DESC, event_type, event_id
        LIMIT :timeline_limit
    """


DRIVER_TIMELINE_SQL = _timeline_sql(
    """
    SELECT
        rr.id::text AS event_id,
        'race_result'::text AS event_type,
        COALESCE(r.start_at, r.weekend_end_date::timestamptz, rr.fetched_at) AS occurred_at,
        r.official_name ||
            CASE WHEN rr.finish_position IS NOT NULL THEN ' · P' || rr.finish_position::text ELSE '' END
            AS label,
        'race'::text AS target_type,
        r.entity_id::text AS target_id,
        r.slug AS target_key,
        COALESCE(re.display_name, r.official_name) AS target_label,
        NULL::text AS target_subtype,
        rr.provider,
        rr.source_url,
        rr.fetched_at,
        jsonb_strip_nulls(jsonb_build_object(
            'grid_position', rr.grid_position,
            'finish_position', rr.finish_position,
            'points', rr.points,
            'status', rr.status,
            'team_key', te.slug,
            'team_name', te.display_name
        )) AS metadata
    FROM race_results rr
    JOIN races r ON r.id = rr.race_id
    LEFT JOIN entities re ON re.id = r.entity_id
    LEFT JOIN entities te ON te.id = rr.team_entity_id
    WHERE rr.driver_entity_id = :entity_id

    UNION ALL

    SELECT
        rc.id::text,
        'race_control'::text,
        rc.observed_at,
        rc.message,
        'session'::text,
        rs.id::text,
        r.slug || '-' || replace(rs.session_code, '_', '-'),
        r.official_name || ' · ' || rs.session_name,
        rs.session_code,
        rc.provider,
        rc.source_url,
        rc.fetched_at,
        jsonb_strip_nulls(jsonb_build_object(
            'race_key', r.slug,
            'session_code', rs.session_code,
            'category', rc.category,
            'flag', rc.flag,
            'scope', rc.scope,
            'lap_number', rc.lap_number,
            'sector', rc.sector
        ))
    FROM session_race_control_events rc
    JOIN race_sessions rs ON rs.id = rc.session_id
    JOIN races r ON r.id = rs.race_id
    WHERE rc.driver_entity_id = :entity_id

    UNION ALL

    SELECT
        s.id::text,
        'story'::text,
        s.updated_at,
        s.title,
        'story'::text,
        s.id::text,
        s.slug,
        s.title,
        s.status,
        NULL::text,
        NULL::text,
        s.updated_at,
        jsonb_strip_nulls(jsonb_build_object(
            'relation_type', se.relation_type,
            'relation_confidence', se.confidence,
            'significance', s.significance,
            'confidence', s.confidence
        ))
    FROM story_entities se
    JOIN stories s ON s.id = se.story_id
    WHERE se.entity_id = :entity_id

    UNION ALL

    SELECT
        e.id::text,
        'evidence'::text,
        COALESCE(e.source_timestamp, e.published_at, e.captured_at, e.created_at),
        COALESCE(e.normalized_claim, e.raw_excerpt_or_reference, e.source_name),
        CASE WHEN s.id IS NOT NULL THEN 'story'::text ELSE NULL::text END,
        s.id::text,
        s.slug,
        s.title,
        s.status,
        e.provider,
        e.source_url,
        e.fetched_at,
        jsonb_strip_nulls(jsonb_build_object(
            'evidence_type', e.evidence_type,
            'source_type', e.source_type,
            'source_name', e.source_name,
            'author_or_speaker', e.author_or_speaker,
            'reliability_class', e.reliability_class,
            'directness', e.directness
        ))
    FROM evidence e
    LEFT JOIN stories s ON s.id = e.story_id
    WHERE e.driver_entity_id = :entity_id
    """
)


TEAM_TIMELINE_SQL = _timeline_sql(
    """
    SELECT
        ('team-race:' || r.id::text || ':' || :entity_id::text) AS event_id,
        'race_result'::text AS event_type,
        COALESCE(r.start_at, r.weekend_end_date::timestamptz, MAX(rr.fetched_at)) AS occurred_at,
        r.official_name ||
            CASE WHEN MIN(rr.finish_position) IS NOT NULL
                 THEN ' · best P' || MIN(rr.finish_position)::text ELSE '' END AS label,
        'race'::text AS target_type,
        r.entity_id::text AS target_id,
        r.slug AS target_key,
        COALESCE(re.display_name, r.official_name) AS target_label,
        NULL::text AS target_subtype,
        MIN(rr.provider) AS provider,
        MAX(rr.source_url) AS source_url,
        MAX(rr.fetched_at) AS fetched_at,
        jsonb_strip_nulls(jsonb_build_object(
            'best_finish', MIN(rr.finish_position),
            'points', SUM(rr.points),
            'classified_cars', COUNT(*)
        )) AS metadata
    FROM race_results rr
    JOIN races r ON r.id = rr.race_id
    LEFT JOIN entities re ON re.id = r.entity_id
    WHERE rr.team_entity_id = :entity_id
    GROUP BY r.id, r.entity_id, r.slug, r.official_name, r.start_at, r.weekend_end_date, re.display_name

    UNION ALL

    SELECT
        s.id::text,
        'story'::text,
        s.updated_at,
        s.title,
        'story'::text,
        s.id::text,
        s.slug,
        s.title,
        s.status,
        NULL::text,
        NULL::text,
        s.updated_at,
        jsonb_strip_nulls(jsonb_build_object(
            'relation_type', se.relation_type,
            'relation_confidence', se.confidence,
            'significance', s.significance,
            'confidence', s.confidence
        ))
    FROM story_entities se
    JOIN stories s ON s.id = se.story_id
    WHERE se.entity_id = :entity_id

    UNION ALL

    SELECT
        e.id::text,
        'evidence'::text,
        COALESCE(e.source_timestamp, e.published_at, e.captured_at, e.created_at),
        COALESCE(e.normalized_claim, e.raw_excerpt_or_reference, e.source_name),
        CASE WHEN s.id IS NOT NULL THEN 'story'::text ELSE NULL::text END,
        s.id::text,
        s.slug,
        s.title,
        s.status,
        e.provider,
        e.source_url,
        e.fetched_at,
        jsonb_strip_nulls(jsonb_build_object(
            'evidence_type', e.evidence_type,
            'source_type', e.source_type,
            'source_name', e.source_name,
            'author_or_speaker', e.author_or_speaker
        ))
    FROM evidence e
    LEFT JOIN stories s ON s.id = e.story_id
    WHERE e.team_entity_id = :entity_id
    """
)


RACE_TIMELINE_SQL = _timeline_sql(
    """
    SELECT
        rs.id::text AS event_id,
        'session'::text AS event_type,
        rs.starts_at AS occurred_at,
        rs.session_name AS label,
        'session'::text AS target_type,
        rs.id::text AS target_id,
        r.slug || '-' || replace(rs.session_code, '_', '-') AS target_key,
        r.official_name || ' · ' || rs.session_name AS target_label,
        rs.session_code AS target_subtype,
        rs.provider,
        rs.source_url,
        rs.fetched_at,
        jsonb_strip_nulls(jsonb_build_object(
            'session_type', rs.session_type,
            'ends_at', rs.ends_at,
            'is_cancelled', rs.is_cancelled
        )) AS metadata
    FROM race_sessions rs
    JOIN races r ON r.id = rs.race_id
    WHERE rs.race_id = :race_id

    UNION ALL

    SELECT
        rd.id::text,
        'document'::text,
        COALESCE(rd.published_at, rd.created_at),
        rd.title,
        'document'::text,
        rd.id::text,
        COALESCE(rd.external_id, rd.id::text),
        rd.title,
        rd.document_type,
        rd.provider,
        rd.document_url,
        rd.updated_at,
        jsonb_strip_nulls(jsonb_build_object(
            'document_number', rd.document_number,
            'document_type', rd.document_type,
            'recalled', rd.recalled
        ))
    FROM race_documents rd
    WHERE rd.race_id = :race_id

    UNION ALL

    SELECT
        s.id::text,
        'story'::text,
        s.updated_at,
        s.title,
        'story'::text,
        s.id::text,
        s.slug,
        s.title,
        s.status,
        NULL::text,
        NULL::text,
        s.updated_at,
        jsonb_strip_nulls(jsonb_build_object(
            'relation_type', se.relation_type,
            'relation_confidence', se.confidence,
            'significance', s.significance
        ))
    FROM story_entities se
    JOIN stories s ON s.id = se.story_id
    JOIN races r ON r.entity_id = se.entity_id
    WHERE r.id = :race_id

    UNION ALL

    SELECT
        rc.id::text,
        'race_control'::text,
        rc.observed_at,
        rc.message,
        'session'::text,
        rs.id::text,
        r.slug || '-' || replace(rs.session_code, '_', '-'),
        r.official_name || ' · ' || rs.session_name,
        rs.session_code,
        rc.provider,
        rc.source_url,
        rc.fetched_at,
        jsonb_strip_nulls(jsonb_build_object(
            'category', rc.category,
            'flag', rc.flag,
            'scope', rc.scope,
            'lap_number', rc.lap_number,
            'sector', rc.sector
        ))
    FROM session_race_control_events rc
    JOIN race_sessions rs ON rs.id = rc.session_id
    JOIN races r ON r.id = rs.race_id
    WHERE rs.race_id = :race_id
    """
)


SESSION_TIMELINE_SQL = _timeline_sql(
    """
    SELECT
        ('session-start:' || rs.id::text) AS event_id,
        'session_start'::text AS event_type,
        rs.starts_at AS occurred_at,
        rs.session_name || ' started' AS label,
        'session'::text AS target_type,
        rs.id::text AS target_id,
        r.slug || '-' || replace(rs.session_code, '_', '-') AS target_key,
        r.official_name || ' · ' || rs.session_name AS target_label,
        rs.session_code AS target_subtype,
        rs.provider,
        rs.source_url,
        rs.fetched_at,
        jsonb_strip_nulls(jsonb_build_object('ends_at', rs.ends_at)) AS metadata
    FROM race_sessions rs
    JOIN races r ON r.id = rs.race_id
    WHERE rs.id = :session_id

    UNION ALL

    SELECT
        rc.id::text,
        'race_control'::text,
        rc.observed_at,
        rc.message,
        CASE WHEN d.id IS NOT NULL THEN 'driver'::text ELSE NULL::text END,
        d.id::text,
        d.slug,
        d.display_name,
        CASE WHEN d.id IS NOT NULL THEN 'driver'::text ELSE NULL::text END,
        rc.provider,
        rc.source_url,
        rc.fetched_at,
        jsonb_strip_nulls(jsonb_build_object(
            'category', rc.category,
            'flag', rc.flag,
            'scope', rc.scope,
            'lap_number', rc.lap_number,
            'sector', rc.sector
        ))
    FROM session_race_control_events rc
    LEFT JOIN entities d ON d.id = rc.driver_entity_id
    WHERE rc.session_id = :session_id

    UNION ALL

    SELECT
        ps.id::text,
        'pit_stop'::text,
        ps.observed_at,
        COALESCE(d.display_name, 'Driver ' || ps.provider_driver_number::text) ||
            ' pit stop · lap ' || ps.lap_number::text,
        CASE WHEN d.id IS NOT NULL THEN 'driver'::text ELSE NULL::text END,
        d.id::text,
        d.slug,
        d.display_name,
        CASE WHEN d.id IS NOT NULL THEN 'driver'::text ELSE NULL::text END,
        ps.provider,
        ps.source_url,
        ps.fetched_at,
        jsonb_strip_nulls(jsonb_build_object(
            'lap_number', ps.lap_number,
            'lane_duration_seconds', ps.lane_duration_seconds,
            'stop_duration_seconds', ps.stop_duration_seconds
        ))
    FROM session_pit_stops ps
    LEFT JOIN entities d ON d.id = ps.driver_entity_id
    WHERE ps.session_id = :session_id

    UNION ALL

    SELECT
        so.id::text,
        'overtake'::text,
        so.observed_at,
        COALESCE(od.display_name, 'Driver ' || so.overtaking_driver_number::text) ||
            ' overtook ' || COALESCE(dd.display_name, 'Driver ' || so.overtaken_driver_number::text),
        CASE WHEN od.id IS NOT NULL THEN 'driver'::text ELSE NULL::text END,
        od.id::text,
        od.slug,
        od.display_name,
        CASE WHEN od.id IS NOT NULL THEN 'driver'::text ELSE NULL::text END,
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

    UNION ALL

    SELECT
        e.id::text,
        'evidence'::text,
        COALESCE(e.source_timestamp, e.published_at, e.captured_at, e.created_at),
        COALESCE(e.normalized_claim, e.raw_excerpt_or_reference, e.source_name),
        CASE WHEN s.id IS NOT NULL THEN 'story'::text ELSE NULL::text END,
        s.id::text,
        s.slug,
        s.title,
        s.status,
        e.provider,
        e.source_url,
        e.fetched_at,
        jsonb_strip_nulls(jsonb_build_object(
            'evidence_type', e.evidence_type,
            'source_type', e.source_type,
            'source_name', e.source_name,
            'author_or_speaker', e.author_or_speaker
        ))
    FROM evidence e
    LEFT JOIN stories s ON s.id = e.story_id
    WHERE e.session_id = :session_id
    """
)


SEASON_TIMELINE_SQL = _timeline_sql(
    """
    SELECT
        r.id::text AS event_id,
        'race'::text AS event_type,
        COALESCE(r.start_at, r.weekend_end_date::timestamptz) AS occurred_at,
        r.official_name,
        'race'::text,
        r.entity_id::text,
        r.slug,
        COALESCE(re.display_name, r.official_name),
        NULL::text,
        r.provider,
        r.source_url,
        r.fetched_at,
        jsonb_strip_nulls(jsonb_build_object(
            'round', r.round,
            'circuit', r.circuit,
            'country', r.country,
            'status', r.status
        ))
    FROM races r
    LEFT JOIN entities re ON re.id = r.entity_id
    WHERE r.season = :season

    UNION ALL

    SELECT DISTINCT ON (s.id)
        s.id::text,
        'story'::text,
        s.updated_at,
        s.title,
        'story'::text,
        s.id::text,
        s.slug,
        s.title,
        s.status,
        NULL::text,
        NULL::text,
        s.updated_at,
        jsonb_strip_nulls(jsonb_build_object(
            'significance', s.significance,
            'confidence', s.confidence
        ))
    FROM stories s
    JOIN story_entities se ON se.story_id = s.id
    JOIN races r ON r.entity_id = se.entity_id
    WHERE r.season = :season
    ORDER BY s.id, s.updated_at DESC

    UNION ALL

    SELECT
        rd.id::text,
        'document'::text,
        COALESCE(rd.published_at, rd.created_at),
        rd.title,
        'document'::text,
        rd.id::text,
        COALESCE(rd.external_id, rd.id::text),
        rd.title,
        rd.document_type,
        rd.provider,
        rd.document_url,
        rd.updated_at,
        jsonb_strip_nulls(jsonb_build_object(
            'race_key', r.slug,
            'document_number', rd.document_number,
            'document_type', rd.document_type,
            'recalled', rd.recalled
        ))
    FROM race_documents rd
    JOIN races r ON r.id = rd.race_id
    WHERE r.season = :season
    """
)


STORY_TIMELINE_SQL = _timeline_sql(
    """
    SELECT
        e.id::text AS event_id,
        'evidence'::text AS event_type,
        COALESCE(e.source_timestamp, e.published_at, e.captured_at, e.created_at) AS occurred_at,
        COALESCE(e.normalized_claim, e.raw_excerpt_or_reference, e.source_name) AS label,
        CASE
            WHEN rs.id IS NOT NULL THEN 'session'::text
            WHEN re.id IS NOT NULL THEN 'race'::text
            WHEN de.id IS NOT NULL THEN 'driver'::text
            WHEN te.id IS NOT NULL THEN 'team'::text
            ELSE NULL::text
        END AS target_type,
        COALESCE(rs.id::text, re.id::text, de.id::text, te.id::text) AS target_id,
        COALESCE(
            r.slug || '-' || replace(rs.session_code, '_', '-'),
            r.slug,
            de.slug,
            te.slug
        ) AS target_key,
        COALESCE(
            r.official_name || ' · ' || rs.session_name,
            re.display_name,
            de.display_name,
            te.display_name
        ) AS target_label,
        CASE
            WHEN rs.id IS NOT NULL THEN rs.session_code
            WHEN de.id IS NOT NULL THEN 'driver'::text
            ELSE NULL::text
        END AS target_subtype,
        e.provider,
        e.source_url,
        e.fetched_at,
        jsonb_strip_nulls(jsonb_build_object(
            'evidence_type', e.evidence_type,
            'source_type', e.source_type,
            'source_name', e.source_name,
            'author_or_speaker', e.author_or_speaker,
            'reliability_class', e.reliability_class,
            'directness', e.directness
        )) AS metadata
    FROM evidence e
    LEFT JOIN race_sessions rs ON rs.id = e.session_id
    LEFT JOIN races r ON r.id = COALESCE(e.race_id, rs.race_id)
    LEFT JOIN entities re ON re.id = r.entity_id
    LEFT JOIN entities de ON de.id = e.driver_entity_id
    LEFT JOIN entities te ON te.id = e.team_entity_id
    WHERE e.story_id = :story_id

    UNION ALL

    SELECT
        p.id::text,
        'publication'::text,
        COALESCE(p.published_at, p.updated_at, p.created_at),
        p.headline,
        'publication'::text,
        p.id::text,
        p.slug,
        p.headline,
        p.type,
        NULL::text,
        NULL::text,
        p.updated_at,
        jsonb_strip_nulls(jsonb_build_object(
            'publication_type', p.type,
            'status', p.status
        ))
    FROM publication_stories ps
    JOIN publications p ON p.id = ps.publication_id
    WHERE ps.story_id = :story_id
    """
)


TIMELINE_SQL = {
    "driver": DRIVER_TIMELINE_SQL,
    "team": TEAM_TIMELINE_SQL,
    "race": RACE_TIMELINE_SQL,
    "session": SESSION_TIMELINE_SQL,
    "season": SEASON_TIMELINE_SQL,
    "story": STORY_TIMELINE_SQL,
}


def _params(target: ResolvedTarget) -> dict[str, Any]:
    return {
        "entity_id": target.entity_id,
        "race_id": target.race_id,
        "session_id": target.session_id,
        "story_id": target.story_id,
        "season": target.season,
        "per_type_limit": PER_TYPE_LIMIT,
        "timeline_limit": TIMELINE_LIMIT,
    }


def _timeline_target(row: Any) -> ContextTargetRef | None:
    if not row["target_type"] or not row["target_id"] or not row["target_key"] or not row["target_label"]:
        return None
    return ContextTargetRef(
        type=row["target_type"],
        id=str(row["target_id"]),
        key=row["target_key"],
        label=row["target_label"],
        subtype=row["target_subtype"],
    )


def _timeline_provenance(row: Any) -> ContextProvenance | None:
    if not row["provider"] and not row["source_url"] and row["fetched_at"] is None:
        return None
    fetched_at = row["fetched_at"]
    return ContextProvenance(
        provider=row["provider"],
        source_url=row["source_url"],
        fetched_at=fetched_at.isoformat() if hasattr(fetched_at, "isoformat") else fetched_at,
    )


async def load_timeline(db: AsyncSession, target: ResolvedTarget) -> list[ContextTimelineEvent]:
    result = await db.execute(text(TIMELINE_SQL[target.target.type]), _params(target))
    events: list[ContextTimelineEvent] = []
    for row in result.mappings().all():
        events.append(
            ContextTimelineEvent(
                id=row["event_id"],
                type=row["event_type"],
                occurred_at=row["occurred_at"],
                label=row["label"],
                target=_timeline_target(row),
                source=row["event_type"],
                metadata=dict(row["metadata"] or {}),
                provenance=_timeline_provenance(row),
            )
        )
    return events


def build_related(
    root: ResolvedTarget,
    relations: list[ContextRelation],
    timeline: list[ContextTimelineEvent],
) -> list[ContextTargetRef]:
    related: list[ContextTargetRef] = []
    seen = {(root.target.type, root.target.id)}

    def add(candidate: ContextTargetRef | None) -> None:
        if candidate is None:
            return
        identity = (candidate.type, candidate.id)
        if identity in seen:
            return
        seen.add(identity)
        related.append(candidate)

    for relation in relations:
        add(relation.target)
        if len(related) >= RELATED_LIMIT:
            return related

    for event in timeline:
        add(event.target)
        if len(related) >= RELATED_LIMIT:
            break

    return related
