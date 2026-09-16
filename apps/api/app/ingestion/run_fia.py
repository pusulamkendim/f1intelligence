from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ingestion.fia_rss import (
    MatchTerm,
    StoryRule,
    choose_story,
    extract_identifiers,
    is_f1_relevant,
    parse_fia_rss,
)

SOURCE_KEY = "fia_press_release_rss"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    fetched: int = 0
    attached: int = 0
    unmatched: int = 0
    irrelevant: int = 0
    ambiguous: int = 0
    duplicates: int = 0


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
    rules_result = await session.execute(
        text(
            """
            SELECT s.id AS story_id, s.slug, r.min_score
            FROM story_ingestion_rules r
            JOIN stories s ON s.id = r.story_id
            WHERE r.enabled = true
            ORDER BY s.slug
            """
        )
    )

    grouped: dict[Any, dict[str, Any]] = {
        row["story_id"]: {
            "story_id": row["story_id"],
            "slug": row["slug"],
            "min_score": row["min_score"],
            "terms": [],
            "identifiers": [],
        }
        for row in rules_result.mappings().all()
    }

    terms_result = await session.execute(
        text(
            """
            SELECT story_id, term, weight
            FROM story_match_terms
            WHERE enabled = true
            ORDER BY story_id, term
            """
        )
    )
    for row in terms_result.mappings().all():
        if row["story_id"] in grouped:
            grouped[row["story_id"]]["terms"].append(
                MatchTerm(term=row["term"], weight=row["weight"])
            )

    identifiers_result = await session.execute(
        text(
            """
            SELECT story_id, identifier
            FROM story_identifiers
            WHERE enabled = true
            ORDER BY story_id, identifier
            """
        )
    )
    for row in identifiers_result.mappings().all():
        if row["story_id"] in grouped:
            grouped[row["story_id"]]["identifiers"].append(row["identifier"])

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


async def get_existing_item(
    session: AsyncSession,
    source_id: Any,
    external_id: str,
) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            """
            SELECT id, status, evidence_id
            FROM ingestion_items
            WHERE source_id = :source_id
              AND external_id = :external_id
            """
        ),
        {"source_id": source_id, "external_id": external_id},
    )
    row = result.mappings().first()
    return dict(row) if row is not None else None


def item_metadata(item: Any, status: str, score: int) -> str:
    return json.dumps(
        {
            "origin": SOURCE_KEY,
            "external_id": item.external_id,
            "presentation_type": "source_claim",
            "categories": list(item.categories),
            "identifiers": list(extract_identifiers(item)),
            "f1_relevant": is_f1_relevant(item),
            "match_status": status,
            "match_score": score,
        }
    )


async def attach_evidence(
    session: AsyncSession,
    source_id: Any,
    item: Any,
    match: Any,
    existing_item_id: Any | None = None,
) -> None:
    raw_metadata = item_metadata(item, match.status, match.score)

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

    params = {
        "source_id": source_id,
        "external_id": item.external_id,
        "source_url": item.url,
        "title": item.title,
        "published_at": item.published_at,
        "story_id": match.story_id,
        "evidence_id": evidence_id,
        "match_score": match.score,
        "raw_metadata": raw_metadata,
    }

    if existing_item_id is None:
        await session.execute(
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
                """
            ),
            params,
        )
    else:
        await session.execute(
            text(
                """
                UPDATE ingestion_items
                SET source_url = :source_url,
                    title = :title,
                    published_at = :published_at,
                    matched_story_id = :story_id,
                    evidence_id = :evidence_id,
                    status = 'attached',
                    match_score = :match_score,
                    raw_metadata = CAST(:raw_metadata AS jsonb),
                    ingested_at = now()
                WHERE id = :item_id
                """
            ),
            {**params, "item_id": existing_item_id},
        )

    await session.execute(
        text("UPDATE stories SET updated_at = now() WHERE id = :story_id"),
        {"story_id": match.story_id},
    )


async def record_nonmatch(
    session: AsyncSession,
    source_id: Any,
    item: Any,
    status: str,
    score: int,
    existing_item_id: Any | None = None,
) -> None:
    raw_metadata = item_metadata(item, status, score)
    params = {
        "source_id": source_id,
        "external_id": item.external_id,
        "source_url": item.url,
        "title": item.title,
        "published_at": item.published_at,
        "status": status,
        "match_score": score,
        "raw_metadata": raw_metadata,
    }

    if existing_item_id is None:
        await session.execute(
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
                """
            ),
            params,
        )
    else:
        await session.execute(
            text(
                """
                UPDATE ingestion_items
                SET source_url = :source_url,
                    title = :title,
                    published_at = :published_at,
                    matched_story_id = NULL,
                    evidence_id = NULL,
                    status = :status,
                    match_score = :match_score,
                    raw_metadata = CAST(:raw_metadata AS jsonb),
                    ingested_at = now()
                WHERE id = :item_id
                """
            ),
            {**params, "item_id": existing_item_id},
        )


async def ingest(limit: int) -> IngestionStats:
    items = await fetch_items(limit)
    stats = IngestionStats(fetched=len(items))

    async with SessionLocal() as session:
        async with session.begin():
            source_id = await ensure_source(session)
            rules = await load_rules(session)

            for item in items:
                match = choose_story(item, rules)
                existing = await get_existing_item(session, source_id, item.external_id)

                if existing and (existing["status"] == "attached" or existing["evidence_id"]):
                    stats.duplicates += 1
                    continue

                existing_item_id = existing["id"] if existing else None
                if match.status == "matched":
                    await attach_evidence(
                        session,
                        source_id,
                        item,
                        match,
                        existing_item_id=existing_item_id,
                    )
                    stats.attached += 1
                    continue

                await record_nonmatch(
                    session,
                    source_id,
                    item,
                    match.status,
                    match.score,
                    existing_item_id=existing_item_id,
                )
                if match.status == "ambiguous":
                    stats.ambiguous += 1
                elif match.status == "irrelevant":
                    stats.irrelevant += 1
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
