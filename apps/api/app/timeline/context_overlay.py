from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.resolver import ResolvedTarget
from app.schemas.context import (
    ContextProvenance,
    ContextTargetRef,
    ContextTimelineEvent,
)

CONTEXT_TIMELINE_LIMIT = 30


def _scope_clause(target: ResolvedTarget) -> tuple[str, dict[str, object]]:
    target_type = target.target.type
    if target_type in {"driver", "team"}:
        return (
            """
            EXISTS (
                SELECT 1
                FROM story_entities se
                WHERE se.story_id = p.item_id
                  AND se.entity_id = :entity_id
            )
            """,
            {"entity_id": target.entity_id},
        )
    if target_type == "race":
        return "p.race_id = :race_id", {"race_id": target.race_id}
    if target_type == "session":
        return "p.session_id = :session_id", {"session_id": target.session_id}
    if target_type == "season":
        return "p.season = :season", {"season": target.season}
    return "p.item_type = 'story' AND p.item_id = :story_id", {"story_id": target.story_id}


async def overlay_story_placements(
    db: AsyncSession,
    target: ResolvedTarget,
    legacy_events: list[ContextTimelineEvent],
) -> list[ContextTimelineEvent]:
    scope, params = _scope_clause(target)
    result = await db.execute(
        text(
            f"""
            SELECT
                s.id AS story_id,
                s.slug,
                s.title,
                s.status,
                COALESCE(p.timeline_at, p.reported_at, s.updated_at) AS occurred_at,
                p.timeline_at,
                p.reported_at,
                p.temporal_relation,
                p.precision,
                p.season,
                r.slug AS race_key,
                r.official_name AS race_label,
                rs.session_code,
                rs.session_name,
                de.slug AS driver_key,
                de.display_name AS driver_label,
                p.stint_number,
                p.lap_number,
                p.confidence AS placement_confidence,
                p.match_method,
                p.metadata,
                primary_source.provider,
                primary_source.source_url,
                primary_source.fetched_at
            FROM timeline_placements p
            JOIN stories s
              ON p.item_type = 'story' AND s.id = p.item_id
            LEFT JOIN races r ON r.id = p.race_id
            LEFT JOIN race_sessions rs ON rs.id = p.session_id
            LEFT JOIN entities de ON de.id = p.driver_entity_id
            LEFT JOIN LATERAL (
                SELECT si.provider, si.source_url, si.fetched_at
                FROM story_source_items ssi
                JOIN source_items si ON si.id = ssi.source_item_id
                WHERE ssi.story_id = s.id
                ORDER BY
                    CASE WHEN ssi.relation_type = 'primary' THEN 0 ELSE 1 END,
                    si.fetched_at DESC
                LIMIT 1
            ) primary_source ON true
            WHERE p.is_primary = true
              AND s.merged_into_story_id IS NULL
              AND {scope}
            ORDER BY COALESCE(p.timeline_at, p.reported_at, s.updated_at) DESC
            LIMIT :limit
            """
        ),
        {**params, "limit": CONTEXT_TIMELINE_LIMIT},
    )

    placement_events: list[ContextTimelineEvent] = []
    placed_story_ids: set[str] = set()
    for row in result.mappings().all():
        story_id = str(row["story_id"])
        placed_story_ids.add(story_id)
        metadata = dict(row["metadata"] or {})
        metadata.update(
            {
                "temporal_relation": row["temporal_relation"],
                "precision": row["precision"],
                "season": row["season"],
                "race_key": row["race_key"],
                "race_label": row["race_label"],
                "session_code": row["session_code"],
                "session_name": row["session_name"],
                "driver_key": row["driver_key"],
                "driver_label": row["driver_label"],
                "stint_number": row["stint_number"],
                "lap_number": row["lap_number"],
                "reported_at": (
                    row["reported_at"].isoformat()
                    if row["reported_at"] is not None
                    else None
                ),
                "placement_confidence": row["placement_confidence"],
                "match_method": row["match_method"],
            }
        )
        placement_events.append(
            ContextTimelineEvent(
                id=story_id,
                type="story",
                occurred_at=row["occurred_at"],
                label=row["title"],
                target=ContextTargetRef(
                    type="story",
                    id=story_id,
                    key=row["slug"],
                    label=row["title"],
                    subtype=row["status"],
                ),
                source="timeline_placements",
                metadata={key: value for key, value in metadata.items() if value is not None},
                provenance=(
                    ContextProvenance(
                        provider=row["provider"],
                        source_url=row["source_url"],
                        fetched_at=(
                            row["fetched_at"].isoformat()
                            if row["fetched_at"] is not None
                            else None
                        ),
                    )
                    if row["provider"] or row["source_url"] or row["fetched_at"]
                    else None
                ),
            )
        )

    retained = [
        event
        for event in legacy_events
        if event.type != "story" or event.id not in placed_story_ids
    ]
    merged = retained + placement_events
    merged.sort(key=lambda event: event.occurred_at, reverse=True)
    return merged[:CONTEXT_TIMELINE_LIMIT]
