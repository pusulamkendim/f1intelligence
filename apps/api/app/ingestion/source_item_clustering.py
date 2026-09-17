from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.source_item_entities import SourceItemEntityClassification

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "the",
    "to",
    "with",
}


@dataclass(frozen=True)
class ClusterFeatures:
    provider: str
    title: str
    published_at: datetime | None
    strong_entity_ids: frozenset[UUID]
    race_entity_ids: frozenset[UUID]


@dataclass(frozen=True)
class SameStoryScore:
    score: int
    method: str
    reasons: dict[str, object]


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    ascii_like = "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_like).strip()


def _tokens(value: str) -> frozenset[str]:
    return frozenset(
        token
        for token in _normalize(value).split()
        if token not in _STOPWORDS and len(token) > 1
    )


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / len(left.union(right))


def cluster_features(
    *,
    provider: str,
    title: str,
    published_at: datetime | None,
    classifications: tuple[SourceItemEntityClassification, ...],
) -> ClusterFeatures:
    strong = frozenset(
        classification.entity_id
        for classification in classifications
        if classification.relation_type in {"subject", "directly_involved"}
    )
    races = frozenset(
        classification.entity_id
        for classification in classifications
        if classification.entity_type == "race"
        and classification.relation_type == "context"
    )
    return ClusterFeatures(
        provider=provider,
        title=title,
        published_at=published_at,
        strong_entity_ids=strong,
        race_entity_ids=races,
    )


def score_same_story(left: ClusterFeatures, right: ClusterFeatures) -> SameStoryScore | None:
    """Score conservative cross-source same-story candidates.

    The thresholds are calibrated for candidate generation, not automatic merging.
    Multiple shared semantic entities can compensate for publisher headline wording,
    while one shared entity needs much stronger lexical or event-context support.
    """
    if left.provider == right.provider:
        return None

    left_normalized = _normalize(left.title)
    right_normalized = _normalize(right.title)
    if not left_normalized or not right_normalized:
        return None

    shared_strong = left.strong_entity_ids.intersection(right.strong_entity_ids)
    shared_races = left.race_entity_ids.intersection(right.race_entity_ids)
    similarity = _jaccard(_tokens(left.title), _tokens(right.title))

    time_close: bool | None = None
    time_delta_hours: float | None = None
    if left.published_at is not None and right.published_at is not None:
        delta_seconds = abs((left.published_at - right.published_at).total_seconds())
        time_delta_hours = delta_seconds / (60 * 60)
        time_close = delta_seconds <= 72 * 60 * 60

    reasons: dict[str, object] = {
        "title_similarity": round(similarity, 3),
        "shared_strong_entities": len(shared_strong),
        "shared_race_entities": len(shared_races),
        "time_within_72h": time_close,
        "time_delta_hours": round(time_delta_hours, 2) if time_delta_hours is not None else None,
    }

    if left_normalized == right_normalized and len(left_normalized) >= 12:
        return SameStoryScore(score=100, method="exact_title_v2", reasons=reasons)

    if time_close is False:
        return None

    if len(shared_strong) >= 2:
        threshold = 0.20 if time_close is True else 0.40
        if similarity >= threshold:
            score = 88
            score += min(4, len(shared_strong) * 2)
            score += 2 if shared_races else 0
            score += min(4, max(0, round((similarity - threshold) * 10)))
            return SameStoryScore(
                score=min(98, score),
                method="multi_entity_title_v2",
                reasons=reasons,
            )

    if shared_strong and similarity >= 0.40:
        score = 86 + min(6, max(0, round((similarity - 0.40) * 15)))
        return SameStoryScore(
            score=min(94, score),
            method="single_entity_title_v2",
            reasons=reasons,
        )

    if shared_strong and shared_races and time_close is True and similarity >= 0.12:
        score = 84
        score += min(4, max(0, round((similarity - 0.12) * 20)))
        return SameStoryScore(
            score=min(90, score),
            method="entity_race_title_v2",
            reasons=reasons,
        )

    if similarity >= 0.90 and shared_races:
        return SameStoryScore(score=90, method="title_race_v2", reasons=reasons)

    return None


async def refresh_cluster_candidates(
    session: AsyncSession,
    *,
    source_item_id: UUID,
    features: ClusterFeatures,
) -> int:
    """Recompute non-destructive same-story candidate pairs for one source item."""
    await session.execute(
        text(
            """
            DELETE FROM source_item_cluster_candidates
            WHERE status = 'candidate'
              AND (left_source_item_id = :source_item_id OR right_source_item_id = :source_item_id)
            """
        ),
        {"source_item_id": source_item_id},
    )

    result = await session.execute(
        text(
            """
            SELECT
                si.id,
                si.provider,
                COALESCE(NULLIF(si.raw_metadata->>'classification_title', ''), si.title) AS title,
                si.published_at,
                ARRAY_REMOVE(
                    ARRAY_AGG(DISTINCT CASE
                        WHEN sie.relation_type IN ('subject', 'directly_involved')
                        THEN sie.entity_id
                    END),
                    NULL
                ) AS strong_entity_ids,
                ARRAY_REMOVE(
                    ARRAY_AGG(DISTINCT CASE
                        WHEN e.entity_type = 'race' AND sie.relation_type = 'context'
                        THEN sie.entity_id
                    END),
                    NULL
                ) AS race_entity_ids
            FROM source_items si
            LEFT JOIN source_item_entities sie ON sie.source_item_id = si.id
            LEFT JOIN entities e ON e.id = sie.entity_id
            WHERE si.id <> :source_item_id
              AND si.provider <> :provider
              AND si.fetched_at >= now() - interval '14 days'
            GROUP BY si.id
            ORDER BY si.fetched_at DESC
            LIMIT 200
            """
        ),
        {"source_item_id": source_item_id, "provider": features.provider},
    )

    written = 0
    for row in result.mappings().all():
        candidate = ClusterFeatures(
            provider=row["provider"],
            title=row["title"],
            published_at=row["published_at"],
            strong_entity_ids=frozenset(row["strong_entity_ids"] or []),
            race_entity_ids=frozenset(row["race_entity_ids"] or []),
        )
        score = score_same_story(features, candidate)
        if score is None:
            continue

        pair = sorted((source_item_id, row["id"]), key=str)
        await session.execute(
            text(
                """
                INSERT INTO source_item_cluster_candidates (
                    left_source_item_id,
                    right_source_item_id,
                    score,
                    method,
                    reasons
                ) VALUES (
                    :left_source_item_id,
                    :right_source_item_id,
                    :score,
                    :method,
                    CAST(:reasons AS jsonb)
                )
                ON CONFLICT (left_source_item_id, right_source_item_id) DO UPDATE
                SET score = EXCLUDED.score,
                    method = EXCLUDED.method,
                    reasons = EXCLUDED.reasons,
                    updated_at = now()
                WHERE source_item_cluster_candidates.status = 'candidate'
                """
            ),
            {
                "left_source_item_id": pair[0],
                "right_source_item_id": pair[1],
                "score": score.score,
                "method": score.method,
                "reasons": json.dumps(score.reasons),
            },
        )
        written += 1

    return written
