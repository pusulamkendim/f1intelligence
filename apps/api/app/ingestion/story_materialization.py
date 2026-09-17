from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.source_item_entities import SourceItemEntityClassification

AUTO_MATCH_SCORE = 92
MATERIALIZATION_METHOD = "source_item_v1"
AGGREGATION_METHOD = "source_aggregate_v1"
DECISION_METHOD = "story_worthy_v1"

_NON_STORY_PATTERNS = (
    "daily discussion thread",
    "ask r/formula1 anything",
    "featured comment:",
    "send us your questions",
    "q&a:",
    "in photos:",
    "in pictures:",
    "through our lens",
    "spotted in the paddock",
    "creator platform",
    "make your 2026 spanish gp predictions",
    "watch: behind the scenes",
)

_RELATION_PRIORITY = {
    "subject": 5,
    "directly_involved": 4,
    "affected": 3,
    "context": 2,
    "mentioned": 1,
}


@dataclass(frozen=True)
class StoryDecision:
    story_worthy: bool
    taxonomy: str
    reason: str


@dataclass(frozen=True)
class StoryMaterializationResult:
    action: str
    story_id: UUID | None
    taxonomy: str


@dataclass(frozen=True)
class StoryMaterializationBatchStats:
    created: int = 0
    attached: int = 0
    existing: int = 0
    merged: int = 0
    skipped: int = 0


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    ascii_like = "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_like).strip()


def _taxonomy(title: str) -> str:
    value = _normalize(title)
    if any(token in value for token in ("academy", "junior team", "rookie test")):
        return "academy_feeder"
    if any(token in value for token in ("rule", "regulation", "vsc", "penalty", "directive")):
        return "regulation"
    if any(
        token in value
        for token in (
            "joins",
            "hires",
            "appoints",
            "chief technical",
            "team principal",
            "driver line up",
            "driver lineup",
            "personnel",
            "injury recovery",
        )
    ):
        return "personnel"
    if any(
        token in value
        for token in ("upgrade", "floor", "aero", "technical", "development", "design")
    ):
        return "technical"
    if any(
        token in value
        for token in ("partner", "sponsor", "budget", "licensing", "management structure")
    ):
        return "team_business"
    if any(
        token in value
        for token in ("collection", "livery", "creator", "merchandise", "launch event")
    ):
        return "media_marketing"
    if any(
        token in value
        for token in (
            "grand prix",
            "qualifying",
            "race recap",
            "race report",
            "race results",
            "sprint",
            "calendar",
        )
    ):
        return "sporting"
    return "general"


def classify_story_worthiness(
    *,
    source_class: str,
    title: str,
    classifications: tuple[SourceItemEntityClassification, ...],
) -> StoryDecision:
    taxonomy = _taxonomy(title)
    normalized = _normalize(title)
    if any(_normalize(pattern) in normalized for pattern in _NON_STORY_PATTERNS):
        return StoryDecision(False, taxonomy, "non_story_container")

    if source_class == "community_signal":
        has_strong_entity = any(
            item.relation_type in {"subject", "directly_involved"}
            for item in classifications
        )
        if not has_strong_entity:
            return StoryDecision(False, taxonomy, "community_without_strong_entity")
        return StoryDecision(True, taxonomy, "community_with_strong_entity")

    # Editorial and first-party articles are retained as stories by default. Taxonomy
    # controls later ranking/surfaces; it is intentionally not a destructive filter.
    return StoryDecision(True, taxonomy, "article_default")


def _slugify(title: str, source_item_id: UUID) -> str:
    value = _normalize(title).replace(" ", "-")
    base = value[:90].strip("-") or "story"
    return f"{base}-{str(source_item_id)[:12]}"


def _source_title_score(row: dict[str, object]) -> int:
    source_class = str(row.get("source_class") or "")
    rank = {
        "first_party_team": 35,
        "independent_editorial": 30,
        "community_signal": 10,
    }.get(source_class, 20)
    title = str(row.get("title") or "")
    token_count = len(_normalize(title).split())
    score = rank + min(token_count, 12)
    lowered = _normalize(title)
    if lowered.startswith(("video ", "social media ", "watch ")):
        score -= 4
    return score


async def _persist_decision(
    session: AsyncSession,
    source_item_id: UUID,
    decision: StoryDecision,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO source_item_story_decisions (
                source_item_id, story_worthy, taxonomy, reason, decision_method
            ) VALUES (
                :source_item_id, :story_worthy, :taxonomy, :reason, :decision_method
            )
            ON CONFLICT (source_item_id) DO UPDATE SET
                story_worthy = EXCLUDED.story_worthy,
                taxonomy = EXCLUDED.taxonomy,
                reason = EXCLUDED.reason,
                decision_method = EXCLUDED.decision_method,
                updated_at = now()
            """
        ),
        {
            "source_item_id": source_item_id,
            "story_worthy": decision.story_worthy,
            "taxonomy": decision.taxonomy,
            "reason": decision.reason,
            "decision_method": DECISION_METHOD,
        },
    )


async def _existing_story_id(session: AsyncSession, source_item_id: UUID) -> UUID | None:
    result = await session.execute(
        text(
            """
            SELECT s.id
            FROM story_source_items ssi
            JOIN stories s ON s.id = ssi.story_id
            WHERE ssi.source_item_id = :source_item_id
              AND s.merged_into_story_id IS NULL
            ORDER BY
                CASE WHEN s.materialization_method = :method THEN 0 ELSE 1 END,
                s.created_at,
                s.id
            LIMIT 1
            """
        ),
        {"source_item_id": source_item_id, "method": MATERIALIZATION_METHOD},
    )
    return result.scalar_one_or_none()


async def _matching_story(
    session: AsyncSession,
    source_item_id: UUID,
) -> tuple[UUID, int, str, str, UUID] | None:
    result = await session.execute(
        text(
            """
            SELECT
                s.id AS story_id,
                c.score,
                c.method,
                c.status,
                CASE
                    WHEN c.left_source_item_id = :source_item_id THEN c.right_source_item_id
                    ELSE c.left_source_item_id
                END AS neighbor_source_item_id
            FROM source_item_cluster_candidates c
            JOIN story_source_items ssi
              ON ssi.source_item_id = CASE
                    WHEN c.left_source_item_id = :source_item_id THEN c.right_source_item_id
                    ELSE c.left_source_item_id
                 END
            JOIN stories s ON s.id = ssi.story_id
            WHERE (c.left_source_item_id = :source_item_id OR c.right_source_item_id = :source_item_id)
              AND s.merged_into_story_id IS NULL
              AND (
                    c.status = 'accepted'
                    OR (c.status = 'candidate' AND c.score >= :auto_score)
                  )
            ORDER BY
                CASE WHEN c.status = 'accepted' THEN 0 ELSE 1 END,
                c.score DESC,
                s.created_at,
                s.id
            LIMIT 1
            """
        ),
        {"source_item_id": source_item_id, "auto_score": AUTO_MATCH_SCORE},
    )
    row = result.mappings().first()
    if row is None:
        return None
    return (
        row["story_id"],
        row["score"],
        row["method"],
        row["status"],
        row["neighbor_source_item_id"],
    )


async def _accept_candidate(
    session: AsyncSession,
    left_source_item_id: UUID,
    right_source_item_id: UUID,
) -> None:
    pair = sorted((left_source_item_id, right_source_item_id), key=str)
    await session.execute(
        text(
            """
            UPDATE source_item_cluster_candidates
            SET status = 'accepted',
                reasons = reasons || '{"accepted_by":"story_materializer_v1"}'::jsonb,
                updated_at = now()
            WHERE left_source_item_id = :left_id
              AND right_source_item_id = :right_id
              AND status = 'candidate'
            """
        ),
        {"left_id": pair[0], "right_id": pair[1]},
    )


async def _merge_auto_stories(
    session: AsyncSession,
    left_story_id: UUID,
    right_story_id: UUID,
) -> UUID | None:
    if left_story_id == right_story_id:
        return left_story_id
    result = await session.execute(
        text(
            """
            SELECT id, created_at, materialization_method
            FROM stories
            WHERE id IN (:left_story_id, :right_story_id)
              AND merged_into_story_id IS NULL
            ORDER BY created_at, id
            """
        ),
        {"left_story_id": left_story_id, "right_story_id": right_story_id},
    )
    rows = result.mappings().all()
    if len(rows) != 2 or any(row["materialization_method"] != MATERIALIZATION_METHOD for row in rows):
        return None

    survivor = rows[0]["id"]
    loser = rows[1]["id"]
    await session.execute(
        text(
            """
            INSERT INTO story_source_items (
                story_id, source_item_id, relation_type, cluster_method,
                cluster_confidence, metadata
            )
            SELECT
                :survivor, source_item_id, relation_type, cluster_method,
                cluster_confidence, metadata
            FROM story_source_items
            WHERE story_id = :loser
            ON CONFLICT (story_id, source_item_id) DO UPDATE SET
                cluster_confidence = GREATEST(
                    story_source_items.cluster_confidence,
                    EXCLUDED.cluster_confidence
                ),
                updated_at = now()
            """
        ),
        {"survivor": survivor, "loser": loser},
    )
    await session.execute(
        text("DELETE FROM story_source_items WHERE story_id = :loser"),
        {"loser": loser},
    )
    await session.execute(
        text(
            """
            UPDATE stories
            SET merged_into_story_id = :survivor,
                status = 'superseded',
                source_count = 0,
                updated_at = now()
            WHERE id = :loser
            """
        ),
        {"survivor": survivor, "loser": loser},
    )
    # Flatten previous redirects so old story slugs resolve directly to the survivor.
    await session.execute(
        text(
            """
            UPDATE stories
            SET merged_into_story_id = :survivor,
                updated_at = now()
            WHERE merged_into_story_id = :loser
            """
        ),
        {"survivor": survivor, "loser": loser},
    )
    return survivor


async def _create_story(
    session: AsyncSession,
    *,
    source_item_id: UUID,
    title: str,
    summary: str | None,
    taxonomy: str,
    published_at: datetime | None,
) -> UUID:
    result = await session.execute(
        text(
            """
            INSERT INTO stories (
                slug, title, summary, taxonomy, materialization_method,
                canonical_source_item_id, first_published_at, last_published_at,
                source_count, confidence, materialization_metadata
            ) VALUES (
                :slug, :title, :summary, :taxonomy, :method,
                :source_item_id, :published_at, :published_at,
                1, 'tentative', '{"version":1}'::jsonb
            )
            RETURNING id
            """
        ),
        {
            "slug": _slugify(title, source_item_id),
            "title": title,
            "summary": summary,
            "taxonomy": taxonomy,
            "method": MATERIALIZATION_METHOD,
            "source_item_id": source_item_id,
            "published_at": published_at,
        },
    )
    return result.scalar_one()


async def _attach_source(
    session: AsyncSession,
    *,
    story_id: UUID,
    source_item_id: UUID,
    cluster_method: str,
    cluster_confidence: int,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO story_source_items (
                story_id, source_item_id, relation_type, cluster_method, cluster_confidence
            ) VALUES (
                :story_id, :source_item_id, 'corroborating', :cluster_method, :cluster_confidence
            )
            ON CONFLICT (story_id, source_item_id) DO UPDATE SET
                cluster_method = EXCLUDED.cluster_method,
                cluster_confidence = GREATEST(
                    story_source_items.cluster_confidence,
                    EXCLUDED.cluster_confidence
                ),
                updated_at = now()
            """
        ),
        {
            "story_id": story_id,
            "source_item_id": source_item_id,
            "cluster_method": cluster_method,
            "cluster_confidence": cluster_confidence,
        },
    )


async def refresh_story_aggregate(session: AsyncSession, story_id: UUID) -> None:
    source_result = await session.execute(
        text(
            """
            SELECT
                si.id,
                si.provider,
                si.source_class,
                COALESCE(NULLIF(si.raw_metadata->>'classification_title', ''), si.title) AS title,
                si.standfirst,
                si.summary,
                si.published_at,
                si.fetched_at,
                d.taxonomy
            FROM story_source_items ssi
            JOIN source_items si ON si.id = ssi.source_item_id
            LEFT JOIN source_item_story_decisions d ON d.source_item_id = si.id
            WHERE ssi.story_id = :story_id
            ORDER BY COALESCE(si.published_at, si.fetched_at), si.id
            """
        ),
        {"story_id": story_id},
    )
    sources = [dict(row) for row in source_result.mappings().all()]
    if not sources:
        return

    primary = max(
        sources,
        key=lambda row: (
            _source_title_score(row),
            -(row["published_at"] or row["fetched_at"]).timestamp(),
            str(row["id"]),
        ),
    )
    source_dates = [row["published_at"] or row["fetched_at"] for row in sources]
    source_count = len(sources)
    summary = primary.get("standfirst") or primary.get("summary")
    taxonomy = str(primary.get("taxonomy") or _taxonomy(str(primary["title"])))

    await session.execute(
        text(
            """
            UPDATE story_source_items
            SET relation_type = CASE
                    WHEN source_item_id = :primary_source_item_id THEN 'primary'
                    ELSE 'corroborating'
                END,
                updated_at = now()
            WHERE story_id = :story_id
            """
        ),
        {"story_id": story_id, "primary_source_item_id": primary["id"]},
    )
    await session.execute(
        text(
            """
            UPDATE stories
            SET title = :title,
                summary = :summary,
                taxonomy = :taxonomy,
                canonical_source_item_id = :primary_source_item_id,
                first_published_at = :first_published_at,
                last_published_at = :last_published_at,
                source_count = :source_count,
                confidence = :confidence,
                updated_at = now()
            WHERE id = :story_id
            """
        ),
        {
            "story_id": story_id,
            "title": primary["title"],
            "summary": summary,
            "taxonomy": taxonomy,
            "primary_source_item_id": primary["id"],
            "first_published_at": min(source_dates),
            "last_published_at": max(source_dates),
            "source_count": source_count,
            "confidence": "corroborated" if source_count >= 2 else "tentative",
        },
    )

    # Rebuild only automatically aggregated story entities. Manual relations survive.
    await session.execute(
        text(
            """
            DELETE FROM story_entities
            WHERE story_id = :story_id
              AND aggregation_method = :aggregation_method
            """
        ),
        {"story_id": story_id, "aggregation_method": AGGREGATION_METHOD},
    )
    entity_result = await session.execute(
        text(
            """
            SELECT
                sie.entity_id,
                sie.relation_type,
                sie.confidence,
                sie.matched_alias
            FROM story_source_items ssi
            JOIN source_item_entities sie ON sie.source_item_id = ssi.source_item_id
            WHERE ssi.story_id = :story_id
              AND sie.match_method <> 'source_context'
            """
        ),
        {"story_id": story_id},
    )
    best: dict[UUID, dict[str, object]] = {}
    for raw_row in entity_result.mappings().all():
        row = dict(raw_row)
        entity_id = row["entity_id"]
        rank = (_RELATION_PRIORITY.get(str(row["relation_type"]), 0), int(row["confidence"]))
        current = best.get(entity_id)
        if current is None:
            best[entity_id] = row
            continue
        current_rank = (
            _RELATION_PRIORITY.get(str(current["relation_type"]), 0),
            int(current["confidence"]),
        )
        if rank > current_rank:
            best[entity_id] = row

    for entity_id, row in best.items():
        await session.execute(
            text(
                """
                INSERT INTO story_entities (
                    story_id, entity_id, relation_type, confidence,
                    match_method, matched_alias, aggregation_method
                ) VALUES (
                    :story_id, :entity_id, :relation_type, :confidence,
                    :match_method, :matched_alias, :aggregation_method
                )
                ON CONFLICT (story_id, entity_id) DO UPDATE SET
                    relation_type = EXCLUDED.relation_type,
                    confidence = EXCLUDED.confidence,
                    match_method = EXCLUDED.match_method,
                    matched_alias = EXCLUDED.matched_alias,
                    aggregation_method = EXCLUDED.aggregation_method,
                    updated_at = now()
                WHERE story_entities.aggregation_method = :aggregation_method
                """
            ),
            {
                "story_id": story_id,
                "entity_id": entity_id,
                "relation_type": row["relation_type"],
                "confidence": row["confidence"],
                "match_method": AGGREGATION_METHOD,
                "matched_alias": row["matched_alias"],
                "aggregation_method": AGGREGATION_METHOD,
            },
        )


async def materialize_source_item(
    session: AsyncSession,
    *,
    source_item_id: UUID,
    source_class: str,
    title: str,
    summary: str | None,
    published_at: datetime | None,
    classifications: tuple[SourceItemEntityClassification, ...],
) -> StoryMaterializationResult:
    decision = classify_story_worthiness(
        source_class=source_class,
        title=title,
        classifications=classifications,
    )
    await _persist_decision(session, source_item_id, decision)
    if not decision.story_worthy:
        return StoryMaterializationResult("skipped", None, decision.taxonomy)

    existing_story_id = await _existing_story_id(session, source_item_id)
    match = await _matching_story(session, source_item_id)
    action = "existing" if existing_story_id is not None else "created"
    story_id = existing_story_id
    cluster_method = "singleton_v1"
    cluster_confidence = 100

    if match is not None:
        matched_story_id, score, candidate_method, _status, neighbor_source_item_id = match
        cluster_method = candidate_method
        cluster_confidence = score
        await _accept_candidate(session, source_item_id, neighbor_source_item_id)
        if story_id is None:
            story_id = matched_story_id
            action = "attached"
        elif story_id != matched_story_id:
            merged_story_id = await _merge_auto_stories(session, story_id, matched_story_id)
            if merged_story_id is not None:
                story_id = merged_story_id
                action = "merged"

    if story_id is None:
        story_id = await _create_story(
            session,
            source_item_id=source_item_id,
            title=title,
            summary=summary,
            taxonomy=decision.taxonomy,
            published_at=published_at,
        )

    await _attach_source(
        session,
        story_id=story_id,
        source_item_id=source_item_id,
        cluster_method=cluster_method,
        cluster_confidence=cluster_confidence,
    )
    await refresh_story_aggregate(session, story_id)
    return StoryMaterializationResult(action, story_id, decision.taxonomy)


async def _load_classifications(
    session: AsyncSession,
    source_item_id: UUID,
) -> tuple[SourceItemEntityClassification, ...]:
    result = await session.execute(
        text(
            """
            SELECT
                sie.entity_id,
                e.entity_type,
                e.slug,
                e.display_name,
                sie.relation_type,
                sie.confidence,
                sie.match_method,
                COALESCE(sie.matched_alias, e.display_name) AS matched_alias,
                sie.detected_in,
                sie.classification_method
            FROM source_item_entities sie
            JOIN entities e ON e.id = sie.entity_id
            WHERE sie.source_item_id = :source_item_id
            """
        ),
        {"source_item_id": source_item_id},
    )
    return tuple(
        SourceItemEntityClassification(
            entity_id=row["entity_id"],
            entity_type=row["entity_type"],
            slug=row["slug"],
            display_name=row["display_name"],
            relation_type=row["relation_type"],
            confidence=row["confidence"],
            match_method=row["match_method"],
            matched_alias=row["matched_alias"],
            detected_in=tuple(row["detected_in"] or []),
            classification_method=row["classification_method"],
        )
        for row in result.mappings().all()
    )


async def materialize_existing_source_items(
    session: AsyncSession,
    *,
    limit: int = 500,
) -> StoryMaterializationBatchStats:
    result = await session.execute(
        text(
            """
            SELECT
                id,
                source_class,
                COALESCE(NULLIF(raw_metadata->>'classification_title', ''), title) AS title,
                COALESCE(standfirst, summary) AS summary,
                published_at
            FROM source_items
            ORDER BY COALESCE(published_at, fetched_at), id
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    counts = {"created": 0, "attached": 0, "existing": 0, "merged": 0, "skipped": 0}
    for row in result.mappings().all():
        classifications = await _load_classifications(session, row["id"])
        materialized = await materialize_source_item(
            session,
            source_item_id=row["id"],
            source_class=row["source_class"],
            title=row["title"],
            summary=row["summary"],
            published_at=row["published_at"],
            classifications=classifications,
        )
        counts[materialized.action] += 1
    return StoryMaterializationBatchStats(**counts)
