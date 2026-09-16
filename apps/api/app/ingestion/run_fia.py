from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ingestion.fia_rss import MatchTerm, StoryRule, choose_story, parse_fia_rss

SOURCE_KEY = "fia_press_release_rss"


@dataclass
class IngestionStats:
    fetched: int = 0
    attached: int = 0
    unmatched: int = 0
    ambiguous: int = 0
    duplicates: int = 0


async def fetch_items(limit: int) -> list:
    settings = get_settings()
    headers = {"User-Agent": settings.source_user_agent}

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=20) as client:
        response = await client.get(settings.fia_press_release_feed_url)
        response.raise_for_status()

    return parse_fia_rss(response.text)[:limit]


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
            },
        )
        item["terms"].append(MatchTerm(term=row["term"], weight=row["weight"]))

    return [
        StoryRule(
            story_id=value["story_id"],
            slug=value["slug"],
            min_score=value["min_score"],
            terms=tuple(value["terms"]),
        )
        for value in grouped.values()
    ]


async def already_ingested(session: AsyncSession, source_id: Any, external_id: str) -> bool:
    result = await session.execute(
        text(
            """
            SELECT 1
            FROM ingestion_items
            WHERE source_id = :source_id
              AND external_id = :external_id
            """
        ),
        {"source_id": source_id, "external_id": external_id},
    )
    return result.first() is not None


async def attach_evidence(
    session: AsyncSession,
    source_id: Any,
    item: Any,
    match: Any,
) -> None:
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
) -> None:
    raw_metadata = json.dumps({"categories": list(item.categories), "origin": SOURCE_KEY})
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


async def ingest(limit: int) -> IngestionStats:
    items = await fetch_items(limit)
    stats = IngestionStats(fetched=len(items))

    async with SessionLocal() as session:
        async with session.begin():
            source_id = await ensure_source(session)
            rules = await load_rules(session)

            for item in items:
                if await already_ingested(session, source_id, item.external_id):
                    stats.duplicates += 1
                    continue

                match = choose_story(item, rules)
                if match.status == "matched":
                    await attach_evidence(session, source_id, item, match)
                    stats.attached += 1
                else:
                    await record_nonmatch(session, source_id, item, match.status, match.score)
                    if match.status == "ambiguous":
                        stats.ambiguous += 1
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
