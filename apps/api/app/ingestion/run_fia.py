from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ingestion.entity_matcher import EntityAlias, EntityMention, match_entities
from app.ingestion.fia_rss import MatchTerm, StoryRule, choose_story, parse_fia_rss

SOURCE_KEY = "fia_press_release_rss"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    fetched: int = 0
    attached: int = 0
    unmatched: int = 0
    filtered: int = 0
    ambiguous: int = 0
    duplicates: int = 0
    entity_mentions: int = 0


async def fetch_items(limit: int) -> list:
    settings = get_settings()
    headers = {
        "User-Agent": settings.source_user_agent,
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    }
    timeout = httpx.Timeout(
        connect=settings.source_http_connect_timeout_seconds,
        read=settings.source_http_read_timeout_seconds,
        write=10.0,
        pool=10.0,
    )
    last_error: Exception | None = None

    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=timeout,
    ) as client:
        for attempt in range(1, settings.source_http_retries + 1):
            try:
                response = await client.get(settings.fia_press_release_feed_url)
                response.raise_for_status()
                return parse_fia_rss(response.text)[:limit]
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code not in RETRYABLE_STATUS_CODES:
                    raise
            except httpx.TransportError as exc:
                last_error = exc

            if attempt < settings.source_http_retries:
                delay = settings.source_http_retry_backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "FIA feed request failed on attempt %s/%s (%s); retrying in %.1fs",
                    attempt,
                    settings.source_http_retries,
                    type(last_error).__name__,
                    delay,
                )
                await asyncio.sleep(delay)

    raise RuntimeError(
        "FIA feed request failed after "
        f"{settings.source_http_retries} attempts: {type(last_error).__name__}"
    ) from last_error


async def ensure_source(session: AsyncSession) -> Any:
    settings = get_settings()
    result = await session.execute(
        text(
            """
            INSERT INTO ingestion_sources (key, provider, name, feed_url, source_type)
            VALUES (:key, 'fia', 'FIA Press Releases', :feed_url, 'official_feed')
            ON CONFLICT (key) DO UPDATE
            SET feed_url = EXCLUDED.feed_url,
                enabled = true,
                updated_at = now()
            RETURNING id
            """
        ),
        {"key": SOURCE_KEY, "feed_url": settings.fia_press_release_feed_url},
    )
    return result.scalar_one()


async def load_rules(session: AsyncSession) -> list[StoryRule]:
    result = await session.execute(
        text(
            """
            SELECT
                s.id AS story_id,
                s.slug,
                r.min_score,
                t.term,
                t.weight
            FROM story_ingestion_rules r
            JOIN stories s ON s.id = r.story_id
            JOIN story_match_terms t ON t.story_id = s.id
            WHERE r.enabled = true
              AND t.enabled = true
            ORDER BY s.slug, t.term
            """
        )
    )

    grouped: dict[Any, dict[str, Any]] = {}
    for row in result.mappings().all():
        story_id = row["story_id"]
        item = grouped.setdefault(
            story_id,
            {
                "story_id": story_id,
                "slug": row["slug"],
                "min_score": row["min_score"],
                "terms": [],
                "identifiers": [],
            },
        )
        item["terms"].append(MatchTerm(term=row["term"], weight=row["weight"]))

    identifiers = await session.execute(
        text(
            """
            SELECT story_id, value
            FROM story_identifiers
            WHERE enabled = true
            ORDER BY story_id, value
            """
        )
    )
    for row in identifiers.mappings().all():
        story_id = row["story_id"]
        if story_id in grouped:
            grouped[story_id]["identifiers"].append(row["value"])

    return [
        StoryRule(
            story_id=value["story_id"],
            slug=value["slug"],
            min_score=value["min_score"],
            terms=tuple(value["terms"]),
            identifiers=tuple(value["identifiers"]),
        )
        for value in grouped.values()
    ]


async def load_entity_aliases(session: AsyncSession) -> list[EntityAlias]:
    result = await session.execute(
        text(
            """
            SELECT
                a.entity_id,
                e.entity_type,
                e.slug,
                e.display_name,
                a.alias,
                a.alias_type,
                a.confidence,
                a.valid_from_season,
                a.valid_to_season
            FROM entity_aliases a
            JOIN entities e ON e.id = a.entity_id
            WHERE a.enabled = true
            ORDER BY e.entity_type, e.slug, length(a.alias) DESC
            """
        )
    )

    return [EntityAlias(**dict(row)) for row in result.mappings().all()]


async def existing_ingestion_item(
    session: AsyncSession,
    source_id: Any,
    external_id: str,
) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            """
            SELECT id, status, matched_story_id
            FROM ingestion_items
            WHERE source_id = :source_id
              AND external_id = :external_id
            """
        ),
        {"source_id": source_id, "external_id": external_id},
    )
    row = result.mappings().first()
    return dict(row) if row is not None else None


async def attach_evidence(
    session: AsyncSession,
    source_id: Any,
    item: Any,
    match: Any,
) -> Any:
    raw_metadata = json.dumps(
        {
            "origin": SOURCE_KEY,
            "external_id": item.external_id,
            "presentation_type": "source_claim",
            "categories": list(item.categories),
        }
    )

    evidence_result = await session.execute(
        text(
            """
            INSERT INTO evidence (
                story_id,
                source_type,
                source_name,
                source_url,
                published_at,
                normalized_claim,
                raw_excerpt_or_reference,
                reliability_class,
                directness,
                raw_metadata
            )
            VALUES (
                :story_id,
                'official_feed',
                'FIA',
                :source_url,
                :published_at,
                :normalized_claim,
                'Official FIA RSS item; article content is not mirrored.',
                'official_primary',
                'direct',
                CAST(:raw_metadata AS jsonb)
            )
            RETURNING id
            """
        ),
        {
            "story_id": match.story_id,
            "source_url": item.url,
            "published_at": item.published_at,
            "normalized_claim": item.title,
            "raw_metadata": raw_metadata,
        },
    )
    evidence_id = evidence_result.scalar_one()

    ingestion_result = await session.execute(
        text(
            """
            INSERT INTO ingestion_items (
                source_id,
                external_id,
                source_url,
                title,
                published_at,
                matched_story_id,
                evidence_id,
                status,
                match_score,
                raw_metadata
            )
            VALUES (
                :source_id,
                :external_id,
                :source_url,
                :title,
                :published_at,
                :story_id,
                :evidence_id,
                'attached',
                :match_score,
                CAST(:raw_metadata AS jsonb)
            )
            ON CONFLICT (source_id, external_id) DO UPDATE
            SET source_url = EXCLUDED.source_url,
                title = EXCLUDED.title,
                published_at = EXCLUDED.published_at,
                matched_story_id = EXCLUDED.matched_story_id,
                evidence_id = EXCLUDED.evidence_id,
                status = EXCLUDED.status,
                match_score = EXCLUDED.match_score,
                raw_metadata = EXCLUDED.raw_metadata,
                ingested_at = now()
            RETURNING id
            """
        ),
        {
            "source_id": source_id,
            "external_id": item.external_id,
            "source_url": item.url,
            "title": item.title,
            "published_at": item.published_at,
            "story_id": match.story_id,
            "evidence_id": evidence_id,
            "match_score": match.score,
            "raw_metadata": raw_metadata,
        },
    )
    ingestion_item_id = ingestion_result.scalar_one()

    await session.execute(
        text("UPDATE stories SET updated_at = now() WHERE id = :story_id"),
        {"story_id": match.story_id},
    )
    return ingestion_item_id


async def record_nonmatch(
    session: AsyncSession,
    source_id: Any,
    item: Any,
    status: str,
    score: int,
) -> Any:
    raw_metadata = json.dumps({"categories": list(item.categories), "origin": SOURCE_KEY})
    result = await session.execute(
        text(
            """
            INSERT INTO ingestion_items (
                source_id,
                external_id,
                source_url,
                title,
                published_at,
                status,
                match_score,
                raw_metadata
            )
            VALUES (
                :source_id,
                :external_id,
                :source_url,
                :title,
                :published_at,
                :status,
                :match_score,
                CAST(:raw_metadata AS jsonb)
            )
            ON CONFLICT (source_id, external_id) DO UPDATE
            SET source_url = EXCLUDED.source_url,
                title = EXCLUDED.title,
                published_at = EXCLUDED.published_at,
                matched_story_id = NULL,
                evidence_id = NULL,
                status = EXCLUDED.status,
                match_score = EXCLUDED.match_score,
                raw_metadata = EXCLUDED.raw_metadata,
                ingested_at = now()
            RETURNING id
            """
        ),
        {
            "source_id": source_id,
            "external_id": item.external_id,
            "source_url": item.url,
            "title": item.title,
            "published_at": item.published_at,
            "status": status,
            "match_score": score,
            "raw_metadata": raw_metadata,
        },
    )
    return result.scalar_one()


async def persist_entity_mentions(
    session: AsyncSession,
    ingestion_item_id: Any,
    story_id: Any | None,
    mentions: tuple[EntityMention, ...],
) -> None:
    await session.execute(
        text("DELETE FROM ingestion_item_entities WHERE ingestion_item_id = :item_id"),
        {"item_id": ingestion_item_id},
    )

    for mention in mentions:
        await session.execute(
            text(
                """
                INSERT INTO ingestion_item_entities (
                    ingestion_item_id,
                    entity_id,
                    matched_alias,
                    confidence,
                    match_method
                )
                VALUES (:item_id, :entity_id, :matched_alias, :confidence, :match_method)
                ON CONFLICT (ingestion_item_id, entity_id) DO UPDATE
                SET matched_alias = EXCLUDED.matched_alias,
                    confidence = EXCLUDED.confidence,
                    match_method = EXCLUDED.match_method,
                    updated_at = now()
                """
            ),
            {
                "item_id": ingestion_item_id,
                "entity_id": mention.entity_id,
                "matched_alias": mention.matched_alias,
                "confidence": mention.confidence,
                "match_method": mention.match_method,
            },
        )

        if story_id is not None:
            await session.execute(
                text(
                    """
                    INSERT INTO story_entities (
                        story_id,
                        entity_id,
                        relation_type,
                        confidence,
                        match_method,
                        matched_alias
                    )
                    VALUES (
                        :story_id,
                        :entity_id,
                        'mentioned',
                        :confidence,
                        :match_method,
                        :matched_alias
                    )
                    ON CONFLICT (story_id, entity_id) DO UPDATE
                    SET confidence = GREATEST(story_entities.confidence, EXCLUDED.confidence),
                        matched_alias = CASE
                            WHEN EXCLUDED.confidence >= story_entities.confidence
                            THEN EXCLUDED.matched_alias
                            ELSE story_entities.matched_alias
                        END,
                        updated_at = now()
                    """
                ),
                {
                    "story_id": story_id,
                    "entity_id": mention.entity_id,
                    "confidence": mention.confidence,
                    "match_method": mention.match_method,
                    "matched_alias": mention.matched_alias,
                },
            )


def item_entity_text(item: Any) -> str:
    return " ".join((item.title, *item.categories))


async def ingest(limit: int) -> IngestionStats:
    items = await fetch_items(limit)
    stats = IngestionStats(fetched=len(items))

    async with SessionLocal() as session:
        async with session.begin():
            source_id = await ensure_source(session)
            rules = await load_rules(session)
            entity_aliases = await load_entity_aliases(session)

            for item in items:
                existing = await existing_ingestion_item(session, source_id, item.external_id)
                match = choose_story(item, rules)

                should_extract_entities = match.status != "filtered" or (
                    existing is not None and existing["status"] == "attached"
                )
                season = item.published_at.year if item.published_at else datetime.now(UTC).year
                mentions = (
                    match_entities(item_entity_text(item), entity_aliases, season=season)
                    if should_extract_entities
                    else ()
                )
                stats.entity_mentions += len(mentions)

                if existing is not None and existing["status"] == "attached":
                    await persist_entity_mentions(
                        session,
                        existing["id"],
                        existing["matched_story_id"],
                        mentions,
                    )
                    stats.duplicates += 1
                    continue

                if match.status == "matched":
                    ingestion_item_id = await attach_evidence(session, source_id, item, match)
                    await persist_entity_mentions(
                        session,
                        ingestion_item_id,
                        match.story_id,
                        mentions,
                    )
                    stats.attached += 1
                else:
                    ingestion_item_id = await record_nonmatch(
                        session,
                        source_id,
                        item,
                        match.status,
                        match.score,
                    )
                    await persist_entity_mentions(session, ingestion_item_id, None, mentions)
                    if match.status == "ambiguous":
                        stats.ambiguous += 1
                    elif match.status == "filtered":
                        stats.filtered += 1
                    else:
                        stats.unmatched += 1

            await session.execute(
                text("UPDATE ingestion_sources SET last_checked_at = now() WHERE id = :source_id"),
                {"source_id": source_id},
            )

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest official FIA press-release RSS items")
    parser.add_argument("--limit", type=int, default=50, help="maximum RSS items to inspect")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    stats = await ingest(max(1, args.limit))
    print(json.dumps(asdict(stats), indent=2))


if __name__ == "__main__":
    asyncio.run(async_main())
