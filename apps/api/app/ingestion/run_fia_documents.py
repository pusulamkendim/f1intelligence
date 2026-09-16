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
from app.ingestion.entity_matcher import (
    EntityAlias,
    EntityMention,
    match_entities,
    normalize_entity_text,
)
from app.ingestion.fia_documents import FiaDecisionDocument, parse_fia_decision_documents

PROVIDER = "fia"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
logger = logging.getLogger(__name__)


@dataclass
class DocumentIngestionStats:
    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    unmatched_events: int = 0
    entity_mentions: int = 0


async def fetch_document_page() -> str:
    settings = get_settings()
    timeout = httpx.Timeout(
        connect=settings.source_http_connect_timeout_seconds,
        read=settings.source_http_read_timeout_seconds,
        write=10.0,
        pool=10.0,
    )
    headers = {
        "User-Agent": settings.source_user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }
    last_error: Exception | None = None

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=timeout) as client:
        for attempt in range(1, settings.source_http_retries + 1):
            try:
                response = await client.get(settings.fia_documents_season_url)
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code not in RETRYABLE_STATUS_CODES:
                    raise
            except httpx.TransportError as exc:
                last_error = exc

            if attempt < settings.source_http_retries:
                delay = settings.source_http_retry_backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "FIA document page failed on attempt %s/%s (%s); retrying in %.1fs",
                    attempt,
                    settings.source_http_retries,
                    type(last_error).__name__,
                    delay,
                )
                await asyncio.sleep(delay)

    raise RuntimeError(
        "FIA document page failed after "
        f"{settings.source_http_retries} attempts: {type(last_error).__name__}"
    ) from last_error


async def load_race_aliases(
    session: AsyncSession,
    season: int,
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    result = await session.execute(
        text(
            """
            SELECT
                r.id AS race_id,
                e.id AS entity_id,
                a.alias,
                a.confidence
            FROM races r
            JOIN entities e ON e.id = r.entity_id
            JOIN entity_aliases a ON a.entity_id = e.id
            WHERE r.season = :season
              AND a.enabled = true
              AND a.alias_type IN ('canonical', 'race_name', 'fia_event_name')
              AND (a.valid_from_season IS NULL OR a.valid_from_season <= :season)
              AND (a.valid_to_season IS NULL OR a.valid_to_season >= :season)
            ORDER BY a.confidence DESC, length(a.alias) DESC
            """
        ),
        {"season": season},
    )

    lookup: dict[str, dict[str, Any]] = {}
    names: set[str] = set()
    for row in result.mappings().all():
        alias = row["alias"]
        names.add(alias)
        lookup.setdefault(normalize_entity_text(alias), dict(row))
    return lookup, names


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


async def upsert_document(
    session: AsyncSession,
    *,
    race_id: Any,
    document: FiaDecisionDocument,
    source_page_url: str,
) -> tuple[Any, bool]:
    existing = await session.execute(
        text(
            """
            SELECT id
            FROM race_documents
            WHERE provider = :provider
              AND external_id = :external_id
            """
        ),
        {"provider": PROVIDER, "external_id": document.external_id},
    )
    existing_id = existing.scalar_one_or_none()

    raw_metadata = json.dumps(
        {
            "event_name": document.event_name,
            "document_number": document.document_number,
        }
    )

    if existing_id is not None:
        await session.execute(
            text(
                """
                UPDATE race_documents
                SET race_id = :race_id,
                    document_number = :document_number,
                    title = :title,
                    document_type = :document_type,
                    document_url = :document_url,
                    source_page_url = :source_page_url,
                    published_at = :published_at,
                    published_label = :published_label,
                    recalled = :recalled,
                    raw_metadata = CAST(:raw_metadata AS jsonb),
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {
                "id": existing_id,
                "race_id": race_id,
                "document_number": document.document_number,
                "title": document.title,
                "document_type": document.document_type,
                "document_url": document.document_url,
                "source_page_url": source_page_url,
                "published_at": document.published_at,
                "published_label": document.published_label,
                "recalled": document.recalled,
                "raw_metadata": raw_metadata,
            },
        )
        return existing_id, False

    result = await session.execute(
        text(
            """
            INSERT INTO race_documents (
                race_id,
                provider,
                external_id,
                document_number,
                title,
                document_type,
                document_url,
                source_page_url,
                published_at,
                published_label,
                recalled,
                raw_metadata
            )
            VALUES (
                :race_id,
                :provider,
                :external_id,
                :document_number,
                :title,
                :document_type,
                :document_url,
                :source_page_url,
                :published_at,
                :published_label,
                :recalled,
                CAST(:raw_metadata AS jsonb)
            )
            RETURNING id
            """
        ),
        {
            "race_id": race_id,
            "provider": PROVIDER,
            "external_id": document.external_id,
            "document_number": document.document_number,
            "title": document.title,
            "document_type": document.document_type,
            "document_url": document.document_url,
            "source_page_url": source_page_url,
            "published_at": document.published_at,
            "published_label": document.published_label,
            "recalled": document.recalled,
            "raw_metadata": raw_metadata,
        },
    )
    return result.scalar_one(), True


async def persist_document_entities(
    session: AsyncSession,
    document_id: Any,
    mentions: tuple[EntityMention, ...],
) -> None:
    await session.execute(
        text("DELETE FROM race_document_entities WHERE race_document_id = :document_id"),
        {"document_id": document_id},
    )

    for mention in mentions:
        await session.execute(
            text(
                """
                INSERT INTO race_document_entities (
                    race_document_id,
                    entity_id,
                    matched_alias,
                    confidence,
                    match_method
                )
                VALUES (:document_id, :entity_id, :matched_alias, :confidence, :match_method)
                """
            ),
            {
                "document_id": document_id,
                "entity_id": mention.entity_id,
                "matched_alias": mention.matched_alias,
                "confidence": mention.confidence,
                "match_method": mention.match_method,
            },
        )


async def ingest_documents(season: int) -> DocumentIngestionStats:
    settings = get_settings()
    html_text = await fetch_document_page()
    stats = DocumentIngestionStats()

    async with SessionLocal() as session:
        async with session.begin():
            race_lookup, event_names = await load_race_aliases(session, season)
            entity_aliases = await load_entity_aliases(session)
            documents = parse_fia_decision_documents(
                html_text,
                base_url=settings.fia_documents_season_url,
                known_event_names=event_names,
            )
            stats.fetched = len(documents)

            for document in documents:
                race = race_lookup.get(normalize_entity_text(document.event_name))
                if race is None:
                    stats.unmatched_events += 1
                    continue

                document_id, inserted = await upsert_document(
                    session,
                    race_id=race["race_id"],
                    document=document,
                    source_page_url=settings.fia_documents_season_url,
                )
                if inserted:
                    stats.inserted += 1
                else:
                    stats.updated += 1

                mentions = match_entities(
                    f"{document.event_name} {document.title}",
                    entity_aliases,
                    season=season,
                )
                stats.entity_mentions += len(mentions)
                await persist_document_entities(session, document_id, mentions)

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest FIA Formula 1 event-document metadata")
    parser.add_argument("--season", type=int, default=2026, help="season used for entity matching")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    stats = await ingest_documents(args.season)
    print(json.dumps(asdict(stats), indent=2))


if __name__ == "__main__":
    asyncio.run(async_main())
