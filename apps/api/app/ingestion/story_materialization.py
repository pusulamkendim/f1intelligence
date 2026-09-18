from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.content_cleanup import clean_summary, clean_title
from app.ingestion.media_assets import refresh_story_media_from_sources
from app.ingestion.source_item_clustering import cluster_features, refresh_cluster_candidates
from app.ingestion.source_item_entities import SourceItemEntityClassification

AUTO_MATCH_SCORE = 94
EVENT_MATCH_SCORE = 88
MATERIALIZATION_METHOD = "source_item_v1"
AGGREGATION_METHOD = "source_aggregate_v2"
DECISION_METHOD = "story_worthy_v2"

_NON_STORY_PATTERNS = (
    "daily discussion thread",
    "ask r/formula1 anything",
    "featured comment",
    "send us your questions",
    "q&a",
    "in photos",
    "in pictures",
    "through our lens",
    "spotted in the paddock",
    "creator platform",
    "make your 2026 spanish gp predictions",
    "watch behind the scenes",
)

_FIRST_PARTY_NON_STORY_PATTERNS = (
    "a seat at the table",
    "five things you can t teach",
    "some assembly required",
    "the team takes over the farmer s dog pub",
    "explore budapest",
    "fan designed stickers",
    "time pieces",
    "hospitality experience",
    "football inspired livery and kit",
    "hot lap car",
)

_RELATION_PRIORITY = {
    "subject": 5,
    "directly_involved": 4,
    "affected": 3,
    "context": 2,
    "mentioned": 1,
}

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


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
    processed: int = 0
    story_worthy: int = 0
    created: int = 0
    attached: int = 0
    existing: int = 0
    merged: int = 0
    skipped: int = 0
    cluster_candidates: int = 0
    canonical_stories: int = 0
    multi_source_stories: int = 0
    singleton_stories: int = 0
    candidates_left: int = 0
    cleanup_changes: int = 0
    fingerprint_story_merges: int = 0
    taxonomy_counts: dict[str, int] = field(default_factory=dict)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    ascii_like = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_like).strip()


def _taxonomy(title: str) -> str:
    value = _normalize(title)
    if any(token in value for token in ("academy", "junior team", "rookie test")):
        return "academy_feeder"

    regulation_phrases = (
        "regulation",
        "regulations",
        "technical directive",
        "sporting directive",
        "penalty",
        "virtual safety car",
        "vsc",
        "rule change",
        "rules change",
        "new rule",
        "new rules",
    )
    if any(phrase in value for phrase in regulation_phrases):
        return "regulation"
    if any(
        token in value
        for token in (
            "licensing",
            "partner",
            "sponsor",
            "budget",
            "commercial",
            "brand management",
            "management structure",
        )
    ):
        return "team_business"
    if any(
        token in value
        for token in (
            "joins",
            "hires",
            "appoints",
            "appointed",
            "chief technical",
            "tech chief",
            "team principal",
            "driver line up",
            "driver lineup",
            "contract extension",
            "extends with",
            "continue with the team",
            "until the end of 2030",
            "injury recovery",
            "dropped him",
            "leaving the team",
        )
    ):
        return "personnel"
    if any(
        token in value
        for token in (
            "upgrade",
            "floor",
            "aero",
            "technical",
            "development",
            "design",
        )
    ):
        return "technical"
    if any(
        token in value
        for token in (
            "collection",
            "livery",
            "creator",
            "merchandise",
            "launch event",
            "stickers",
            "hospitality",
            "time pieces",
        )
    ):
        return "media_marketing"
    if any(
        token in value
        for token in (
            "grand prix",
            "qualifying",
            "practice recap",
            "race recap",
            "race report",
            "race results",
            "sprint",
            "calendar",
            "fp1",
            "fp2",
            "fp3",
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
    cleaned_title = clean_title(title)
    taxonomy = _taxonomy(cleaned_title)
    normalized = _normalize(cleaned_title)

    if any(_normalize(pattern) in normalized for pattern in _NON_STORY_PATTERNS):
        return StoryDecision(False, taxonomy, "non_story_container")

    if source_class == "first_party_team" and any(
        _normalize(pattern) in normalized for pattern in _FIRST_PARTY_NON_STORY_PATTERNS
    ):
        return StoryDecision(False, taxonomy, "first_party_evergreen_or_promo")

    if normalized.startswith("explore ") and source_class == "first_party_team":
        return StoryDecision(False, taxonomy, "first_party_destination_content")

    if source_class == "community_signal":
        has_strong_entity = any(
            item.relation_type in {"subject", "directly_involved"}
            for item in classifications
        )
        if not has_strong_entity:
            return StoryDecision(False, taxonomy, "community_without_strong_entity")
        return StoryDecision(True, taxonomy, "community_with_strong_entity")

    return StoryDecision(True, taxonomy, "article_default_v2")


def _slugify(title: str, source_item_id: UUID) -> str:
    value = _normalize(clean_title(title)).replace(" ", "-")
    base = value[:90].strip("-") or "story"
    return f"{base}-{str(source_item_id)[:12]}"


def _source_title_score(row: dict[str, object]) -> int:
    source_class = str(row.get("source_class") or "")
    rank = {
        "first_party_team": 35,
        "independent_editorial": 30,
        "community_signal": 10,
    }.get(source_class, 20)
    title = clean_title(str(row.get("title") or ""))
    token_count = len(_normalize(title).split())
    score = rank + min(token_count, 12)
    lowered = _normalize(title)
    if lowered.startswith(("video ", "social media ", "watch ")):
        score -= 4
    return score


def _text_similarity(left: str, right: str) -> float:
    left_tokens = set(_normalize(left).split())
    right_tokens = set(_normalize(right).split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _summary_sentences(value: str | None) -> list[str]:
    cleaned = clean_summary(value)
    if not cleaned:
        return []
    sentences = [item.strip() for item in _SENTENCE_SPLIT_RE.split(cleaned)]
    return [item for item in sentences if len(item) >= 24]


def _synthesize_summary(
    sources: list[dict[str, object]],
    primary: dict[str, object],
) -> str | None:
    ordered = sorted(
        sources,
        key=lambda row: (
            _source_title_score(row),
            (row.get("published_at") or row.get("fetched_at")),
        ),
        reverse=True,
    )
    if primary in ordered:
        ordered.remove(primary)
        ordered.insert(0, primary)

    selected: list[str] = []
    max_sentences = 2 if len(sources) >= 2 else 1
    for row in ordered:
        value = row.get("standfirst") or row.get("summary")
        for sentence in _summary_sentences(str(value) if value else None):
            if any(_text_similarity(sentence, existing) >= 0.72 for existing in selected):
                continue
            selected.append(sentence)
            break
        if len(selected) >= max_sentences:
            break

    return " ".join(selected) or None


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


async def _existing_story_id(
    session: AsyncSession,
    source_item_id: UUID,
) -> UUID | None:
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


async def _existing_auto_story_id(
    session: AsyncSession,
    source_item_id: UUID,
) -> UUID | None:
    result = await session.execute(
        text(
            """
            SELECT s.id
            FROM story_source_items ssi
            JOIN stories s ON s.id = ssi.story_id
            WHERE ssi.source_item_id = :source_item_id
              AND s.materialization_method = :method
              AND s.merged_into_story_id IS NULL
            ORDER BY s.created_at, s.id
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
                    WHEN c.left_source_item_id = :source_item_id
                    THEN c.right_source_item_id
                    ELSE c.left_source_item_id
                END AS neighbor_source_item_id
            FROM source_item_cluster_candidates c
            JOIN story_source_items ssi
              ON ssi.source_item_id = CASE
                    WHEN c.left_source_item_id = :source_item_id
                    THEN c.right_source_item_id
                    ELSE c.left_source_item_id
                 END
            JOIN stories s ON s.id = ssi.story_id
            WHERE (
                    c.left_source_item_id = :source_item_id
                    OR c.right_source_item_id = :source_item_id
                  )
              AND s.merged_into_story_id IS NULL
              AND (
                    c.status = 'accepted'
                    OR (c.status = 'candidate' AND c.score >= :auto_score)
                    OR (
                        c.status = 'candidate'
                        AND c.method = 'event_fingerprint_v3'
                        AND c.score >= :event_score
                    )
                  )
            ORDER BY
                CASE WHEN c.status = 'accepted' THEN 0 ELSE 1 END,
                c.score DESC,
                s.created_at,
                s.id
            LIMIT 1
            """
        ),
        {
            "source_item_id": source_item_id,
            "auto_score": AUTO_MATCH_SCORE,
            "event_score": EVENT_MATCH_SCORE,
        },
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
                reasons = reasons || jsonb_build_object(
                    'accepted_by', 'story_materializer_v2'
                ),
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
    if len(rows) != 2 or any(
        row["materialization_method"] != MATERIALIZATION_METHOD for row in rows
    ):
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
            INSERT INTO story_media_candidates (
                story_id,
                media_asset_id,
                story_role,
                match_reason,
                confidence,
                selected,
                manual_override,
                metadata
            )
            SELECT
                :survivor,
                media_asset_id,
                story_role,
                match_reason,
                confidence,
                selected,
                manual_override,
                metadata
            FROM story_media_candidates
            WHERE story_id = :loser
            ON CONFLICT (story_id, media_asset_id, story_role) DO UPDATE SET
                confidence = GREATEST(
                    story_media_candidates.confidence,
                    EXCLUDED.confidence
                ),
                selected = (
                    story_media_candidates.selected
                    OR EXCLUDED.selected
                ),
                manual_override = (
                    story_media_candidates.manual_override
                    OR EXCLUDED.manual_override
                ),
                metadata = story_media_candidates.metadata || EXCLUDED.metadata,
                updated_at = now()
            """
        ),
        {"survivor": survivor, "loser": loser},
    )
    await session.execute(
        text("DELETE FROM story_media_candidates WHERE story_id = :loser"),
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


async def _converge_event_fingerprint_stories(
    session: AsyncSession,
) -> int:
    result = await session.execute(
        text(
            """
            SELECT
                si.raw_metadata->>'event_fingerprint' AS fingerprint,
                ARRAY_AGG(DISTINCT s.id) AS story_ids
            FROM source_items si
            JOIN story_source_items ssi
              ON ssi.source_item_id = si.id
            JOIN stories s
              ON s.id = ssi.story_id
            WHERE NULLIF(
                    si.raw_metadata->>'event_fingerprint',
                    ''
                  ) IS NOT NULL
              AND s.materialization_method = :method
              AND s.merged_into_story_id IS NULL
            GROUP BY si.raw_metadata->>'event_fingerprint'
            HAVING COUNT(DISTINCT s.id) > 1
            """
        ),
        {"method": MATERIALIZATION_METHOD},
    )

    merges = 0
    for row in result.mappings().all():
        fingerprint = row["fingerprint"]
        story_ids = list(row["story_ids"] or [])
        if len(story_ids) < 2:
            continue

        survivor = story_ids[0]
        for story_id in story_ids[1:]:
            merged = await _merge_auto_stories(
                session,
                survivor,
                story_id,
            )
            if merged is None:
                continue
            survivor = merged
            merges += 1

        await session.execute(
            text(
                """
                UPDATE source_item_cluster_candidates c
                SET
                    status = 'accepted',
                    reasons = reasons || jsonb_build_object(
                        'accepted_by',
                        'event_fingerprint_convergence_v1'
                    ),
                    updated_at = now()
                FROM source_items left_item,
                     source_items right_item
                WHERE c.status = 'candidate'
                  AND c.method = 'event_fingerprint_v3'
                  AND left_item.id = c.left_source_item_id
                  AND right_item.id = c.right_source_item_id
                  AND left_item.raw_metadata->>'event_fingerprint'
                      = :fingerprint
                  AND right_item.raw_metadata->>'event_fingerprint'
                      = :fingerprint
                """
            ),
            {"fingerprint": fingerprint},
        )
        await refresh_story_aggregate(session, survivor)
        await refresh_story_media_from_sources(session, survivor)

    return merges


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
                1, 'tentative', jsonb_build_object('version', 2)
            )
            RETURNING id
            """
        ),
        {
            "slug": _slugify(title, source_item_id),
            "title": clean_title(title),
            "summary": clean_summary(summary),
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
                story_id, source_item_id, relation_type,
                cluster_method, cluster_confidence
            ) VALUES (
                :story_id, :source_item_id, 'corroborating',
                :cluster_method, :cluster_confidence
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


async def _detach_filtered_source(
    session: AsyncSession,
    source_item_id: UUID,
) -> None:
    story_id = await _existing_auto_story_id(session, source_item_id)
    if story_id is None:
        return
    await session.execute(
        text(
            """
            DELETE FROM story_source_items
            WHERE story_id = :story_id
              AND source_item_id = :source_item_id
            """
        ),
        {"story_id": story_id, "source_item_id": source_item_id},
    )
    remaining = await session.execute(
        text(
            """
            SELECT COUNT(*)::int
            FROM story_source_items
            WHERE story_id = :story_id
            """
        ),
        {"story_id": story_id},
    )
    if remaining.scalar_one() == 0:
        await session.execute(
            text(
                """
                DELETE FROM stories
                WHERE id = :story_id
                  AND materialization_method = :method
                """
            ),
            {"story_id": story_id, "method": MATERIALIZATION_METHOD},
        )
    else:
        await refresh_story_aggregate(session, story_id)


async def refresh_story_aggregate(session: AsyncSession, story_id: UUID) -> None:
    source_result = await session.execute(
        text(
            """
            SELECT
                si.id,
                si.provider,
                si.source_class,
                COALESCE(
                    NULLIF(si.raw_metadata->>'classification_title', ''),
                    si.title
                ) AS title,
                si.standfirst,
                si.summary,
                si.published_at,
                si.fetched_at,
                d.taxonomy
            FROM story_source_items ssi
            JOIN source_items si ON si.id = ssi.source_item_id
            LEFT JOIN source_item_story_decisions d
              ON d.source_item_id = si.id
            WHERE ssi.story_id = :story_id
            ORDER BY COALESCE(si.published_at, si.fetched_at), si.id
            """
        ),
        {"story_id": story_id},
    )
    sources = [dict(row) for row in source_result.mappings().all()]
    if not sources:
        return

    for source in sources:
        source["title"] = clean_title(str(source.get("title") or ""))
        source["standfirst"] = clean_summary(
            str(source["standfirst"]) if source.get("standfirst") else None
        )
        source["summary"] = clean_summary(
            str(source["summary"]) if source.get("summary") else None
        )

    primary = max(
        sources,
        key=lambda row: (
            _source_title_score(row),
            -(row["published_at"] or row["fetched_at"]).timestamp(),
            str(row["id"]),
        ),
    )
    published_dates = [row["published_at"] for row in sources if row["published_at"]]
    observed_dates = [row["fetched_at"] for row in sources if row["fetched_at"]]
    source_count = len(sources)
    summary = _synthesize_summary(sources, primary)
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
                first_observed_at = :first_observed_at,
                last_observed_at = :last_observed_at,
                source_count = :source_count,
                confidence = :confidence,
                materialization_metadata = materialization_metadata
                    || jsonb_build_object(
                        'version', 2,
                        'summary_method', 'deterministic_v2'
                    ),
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
            "first_published_at": min(published_dates) if published_dates else None,
            "last_published_at": max(published_dates) if published_dates else None,
            "first_observed_at": min(observed_dates) if observed_dates else None,
            "last_observed_at": max(observed_dates) if observed_dates else None,
            "source_count": source_count,
            "confidence": "corroborated" if source_count >= 2 else "tentative",
        },
    )

    await session.execute(
        text(
            """
            DELETE FROM story_entities
            WHERE story_id = :story_id
              AND aggregation_method IN (
                    'source_aggregate_v1',
                    'source_aggregate_v2'
                  )
            """
        ),
        {"story_id": story_id},
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
            JOIN source_item_entities sie
              ON sie.source_item_id = ssi.source_item_id
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
        rank = (
            _RELATION_PRIORITY.get(str(row["relation_type"]), 0),
            int(row["confidence"]),
        )
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
                WHERE story_entities.aggregation_method IN (
                    'source_aggregate_v1',
                    'source_aggregate_v2'
                )
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
    title = clean_title(title)
    summary = clean_summary(summary)
    decision = classify_story_worthiness(
        source_class=source_class,
        title=title,
        classifications=classifications,
    )
    await _persist_decision(session, source_item_id, decision)
    if not decision.story_worthy:
        await _detach_filtered_source(session, source_item_id)
        return StoryMaterializationResult("skipped", None, decision.taxonomy)

    existing_story_id = await _existing_story_id(session, source_item_id)
    match = await _matching_story(session, source_item_id)
    action = "existing" if existing_story_id is not None else "created"
    story_id = existing_story_id
    cluster_method = "singleton_v2"
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
            merged_story_id = await _merge_auto_stories(
                session,
                story_id,
                matched_story_id,
            )
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
    await refresh_story_media_from_sources(session, story_id)
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


async def _story_audit_counts(session: AsyncSession) -> tuple[int, int, int, int]:
    story_result = await session.execute(
        text(
            """
            SELECT
                COUNT(*)::int AS canonical_stories,
                COUNT(*) FILTER (WHERE source_count > 1)::int AS multi_source_stories,
                COUNT(*) FILTER (WHERE source_count = 1)::int AS singleton_stories
            FROM stories
            WHERE materialization_method = :method
              AND merged_into_story_id IS NULL
            """
        ),
        {"method": MATERIALIZATION_METHOD},
    )
    row = story_result.mappings().one()
    candidate_result = await session.execute(
        text(
            """
            SELECT COUNT(*)::int
            FROM source_item_cluster_candidates
            WHERE status = 'candidate'
            """
        )
    )
    return (
        int(row["canonical_stories"]),
        int(row["multi_source_stories"]),
        int(row["singleton_stories"]),
        int(candidate_result.scalar_one()),
    )


async def materialize_existing_source_items(
    session: AsyncSession,
    *,
    limit: int | None = None,
) -> StoryMaterializationBatchStats:
    limit_clause = "LIMIT :limit" if limit is not None else ""
    result = await session.execute(
        text(
            f"""
            SELECT
                id,
                provider,
                source_class,
                COALESCE(
                    NULLIF(raw_metadata->>'classification_title', ''),
                    title
                ) AS title,
                COALESCE(standfirst, summary) AS summary,
                published_at
            FROM source_items
            ORDER BY COALESCE(published_at, fetched_at), id
            {limit_clause}
            """
        ),
        {"limit": limit} if limit is not None else {},
    )
    rows = result.mappings().all()
    counts = {
        "created": 0,
        "attached": 0,
        "existing": 0,
        "merged": 0,
        "skipped": 0,
    }
    taxonomy_counts: dict[str, int] = {}
    story_worthy = 0
    cluster_candidate_count = 0
    cleanup_changes = 0

    for row in rows:
        classifications = await _load_classifications(session, row["id"])
        raw_title = str(row["title"])
        raw_summary = str(row["summary"]) if row["summary"] else None
        title = clean_title(raw_title)
        summary = clean_summary(raw_summary)
        if title != raw_title or summary != raw_summary:
            cleanup_changes += 1

        cluster_candidate_count += await refresh_cluster_candidates(
            session,
            source_item_id=row["id"],
            features=cluster_features(
                provider=row["provider"],
                title=title,
                published_at=row["published_at"],
                classifications=classifications,
            ),
        )
        materialized = await materialize_source_item(
            session,
            source_item_id=row["id"],
            source_class=row["source_class"],
            title=title,
            summary=summary,
            published_at=row["published_at"],
            classifications=classifications,
        )
        counts[materialized.action] += 1
        taxonomy_counts[materialized.taxonomy] = (
            taxonomy_counts.get(materialized.taxonomy, 0) + 1
        )
        if materialized.action != "skipped":
            story_worthy += 1

    fingerprint_story_merges = await _converge_event_fingerprint_stories(
        session
    )
    canonical, multi, singleton, candidates_left = await _story_audit_counts(session)
    return StoryMaterializationBatchStats(
        processed=len(rows),
        story_worthy=story_worthy,
        cluster_candidates=cluster_candidate_count,
        canonical_stories=canonical,
        multi_source_stories=multi,
        singleton_stories=singleton,
        candidates_left=candidates_left,
        cleanup_changes=cleanup_changes,
        fingerprint_story_merges=fingerprint_story_merges,
        taxonomy_counts=taxonomy_counts,
        **counts,
    )
