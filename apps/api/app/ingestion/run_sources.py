from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field

import httpx

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ingestion.editorial_sources import (
    EditorialItem,
    EditorialSource,
    discover_listing_urls,
    parse_article_html,
    parse_feed,
)
from app.ingestion.source_item_clustering import cluster_features, refresh_cluster_candidates
from app.ingestion.source_item_entities import SourceItemText, classify_source_item_entities
from app.ingestion.source_item_store import (
    SourceItemRecord,
    load_entity_aliases,
    load_team_context_aliases,
    reconcile_source_item_entities,
    upsert_source_item,
)
from app.ingestion.source_registry import (
    DISABLED_SOURCE_REASONS,
    DISABLED_SOURCES,
    SOURCE_BY_KEY,
    SOURCES,
)
from app.ingestion.source_semantics import classification_title
from app.ingestion.story_materialization import materialize_source_item

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
COMMUNITY_SOURCE_GAP_SECONDS = 5.0
logger = logging.getLogger(__name__)


@dataclass
class SourceStats:
    source: str
    discovered: int = 0
    fetched: int = 0
    persisted: int = 0
    entity_links: int = 0
    cluster_candidates: int = 0
    stories_created: int = 0
    stories_attached: int = 0
    stories_existing: int = 0
    stories_merged: int = 0
    stories_skipped: int = 0
    failures: int = 0
    error: str | None = None


@dataclass
class IngestionStats:
    sources: list[SourceStats] = field(default_factory=list)

    @property
    def persisted(self) -> int:
        return sum(item.persisted for item in self.sources)

    @property
    def entity_links(self) -> int:
        return sum(item.entity_links for item in self.sources)

    @property
    def cluster_candidates(self) -> int:
        return sum(item.cluster_candidates for item in self.sources)

    @property
    def stories_created(self) -> int:
        return sum(item.stories_created for item in self.sources)

    @property
    def stories_attached(self) -> int:
        return sum(item.stories_attached for item in self.sources)

    @property
    def stories_existing(self) -> int:
        return sum(item.stories_existing for item in self.sources)

    @property
    def stories_merged(self) -> int:
        return sum(item.stories_merged for item in self.sources)

    @property
    def stories_skipped(self) -> int:
        return sum(item.stories_skipped for item in self.sources)

    @property
    def failures(self) -> int:
        return sum(item.failures for item in self.sources)


def item_to_source_record(source: EditorialSource, item: EditorialItem) -> SourceItemRecord:
    semantic_title = classification_title(source.key, item.title)
    metadata = dict(item.raw_metadata)
    metadata.update(
        {
            "source_key": source.key,
            "source_class": source.source_class,
            "team_slug": source.team_slug,
            "classification_title": semantic_title,
        }
    )
    return SourceItemRecord(
        provider=source.provider,
        external_id=item.external_id,
        source_type="community_post" if source.source_class == "community_signal" else "article",
        source_class=source.source_class,
        source_url=item.canonical_url,
        title=item.title,
        standfirst=item.summary,
        body_excerpt=(
            None if source.source_class == "community_signal" else item.body_excerpt
        ),
        author=item.author,
        language=item.language,
        published_at=item.published_at,
        content_hash=item.content_hash,
        rights_policy=source.rights_policy,
        raw_metadata=metadata,
    )


def _timeout() -> httpx.Timeout:
    settings = get_settings()
    return httpx.Timeout(
        connect=settings.source_http_connect_timeout_seconds,
        read=settings.source_http_read_timeout_seconds,
        write=10.0,
        pool=10.0,
    )


async def _get_with_retries(client: httpx.AsyncClient, url: str) -> httpx.Response:
    settings = get_settings()
    last_error: Exception | None = None
    for attempt in range(1, settings.source_http_retries + 1):
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code not in RETRYABLE_STATUS_CODES:
                raise
        except httpx.TransportError as exc:
            last_error = exc

        if attempt < settings.source_http_retries:
            await asyncio.sleep(settings.source_http_retry_backoff_seconds * (2 ** (attempt - 1)))

    raise RuntimeError(
        f"request failed after {settings.source_http_retries} attempts for {url}"
    ) from last_error


async def _fetch_source_items(
    client: httpx.AsyncClient,
    source: EditorialSource,
    *,
    limit: int,
) -> tuple[list[EditorialItem], int, int]:
    settings = get_settings()
    response = await _get_with_retries(client, source.discovery_url)

    if source.mode == "rss":
        items = parse_feed(response.text, source)[:limit]
        return items, len(items), 0

    urls = discover_listing_urls(response.text, source)
    items: list[EditorialItem] = []
    failures = 0
    candidate_limit = min(len(urls), max(limit * 4, limit))
    for url in urls[:candidate_limit]:
        if len(items) >= limit:
            break
        try:
            article_response = await _get_with_retries(client, url)
            items.append(
                parse_article_html(
                    article_response.text,
                    requested_url=str(article_response.url),
                    source=source,
                )
            )
        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
            failures += 1
            logger.warning("Skipping %s item %s: %s", source.key, url, exc)
        if settings.editorial_source_min_interval_seconds:
            await asyncio.sleep(settings.editorial_source_min_interval_seconds)
    return items, len(urls), failures


def _reset_transaction_stats(stats: SourceStats) -> None:
    stats.persisted = 0
    stats.entity_links = 0
    stats.cluster_candidates = 0
    stats.stories_created = 0
    stats.stories_attached = 0
    stats.stories_existing = 0
    stats.stories_merged = 0
    stats.stories_skipped = 0


def _record_story_action(stats: SourceStats, action: str) -> None:
    if action == "created":
        stats.stories_created += 1
    elif action == "attached":
        stats.stories_attached += 1
    elif action == "existing":
        stats.stories_existing += 1
    elif action == "merged":
        stats.stories_merged += 1
    elif action == "skipped":
        stats.stories_skipped += 1


async def ingest_source(source: EditorialSource, *, limit: int) -> SourceStats:
    settings = get_settings()
    headers = {
        "User-Agent": settings.source_user_agent,
        "Accept": "application/rss+xml, application/atom+xml, text/html;q=0.9, */*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    }
    stats = SourceStats(source=source.key)

    try:
        async with httpx.AsyncClient(
            headers=headers,
            follow_redirects=True,
            timeout=_timeout(),
        ) as client:
            items, discovered, fetch_failures = await _fetch_source_items(
                client,
                source,
                limit=limit,
            )
        stats.discovered = discovered
        stats.fetched = len(items)
        stats.failures += fetch_failures

        async with SessionLocal() as session:
            async with session.begin():
                aliases = await load_entity_aliases(session)
                team_alias_cache: dict[int | None, list] = {}
                for item in items:
                    record = item_to_source_record(source, item)
                    season = item.published_at.year if item.published_at else None
                    semantic_title = str(record.raw_metadata["classification_title"])
                    source_item_id = await upsert_source_item(session, record)

                    item_aliases = aliases
                    if source.team_slug:
                        if season not in team_alias_cache:
                            team_alias_cache[season] = await load_team_context_aliases(
                                session,
                                team_slug=source.team_slug,
                                season=season,
                            )
                        item_aliases = aliases + team_alias_cache[season]

                    classifications = classify_source_item_entities(
                        SourceItemText(
                            title=semantic_title,
                            standfirst=record.standfirst,
                            summary=record.summary,
                            body_excerpt=record.body_excerpt,
                            season=season,
                            source_context_team_slug=source.team_slug,
                        ),
                        item_aliases,
                    )
                    await reconcile_source_item_entities(
                        session,
                        source_item_id,
                        classifications,
                    )
                    stats.persisted += 1
                    stats.entity_links += len(classifications)
                    stats.cluster_candidates += await refresh_cluster_candidates(
                        session,
                        source_item_id=source_item_id,
                        features=cluster_features(
                            provider=record.provider,
                            title=semantic_title,
                            published_at=record.published_at,
                            classifications=classifications,
                        ),
                    )
                    materialized = await materialize_source_item(
                        session,
                        source_item_id=source_item_id,
                        source_class=record.source_class,
                        title=semantic_title,
                        summary=record.standfirst or record.summary,
                        published_at=record.published_at,
                        classifications=classifications,
                    )
                    _record_story_action(stats, materialized.action)
    except Exception as exc:  # source isolation: one provider must not abort the whole run
        _reset_transaction_stats(stats)
        stats.failures += 1
        stats.error = f"{type(exc).__name__}: {exc}"
        logger.exception("Source ingestion failed for %s", source.key)

    return stats


async def ingest(sources: list[EditorialSource], *, limit: int) -> IngestionStats:
    output = IngestionStats()
    previous_was_community = False
    for source in sources:
        if previous_was_community and source.source_class == "community_signal":
            await asyncio.sleep(COMMUNITY_SOURCE_GAP_SECONDS)
        output.sources.append(await ingest_source(source, limit=limit))
        previous_was_community = source.source_class == "community_signal"
    return output


def _selected_sources(keys: list[str]) -> list[EditorialSource]:
    if not keys or keys == ["all"]:
        return list(SOURCES)
    unknown = sorted(set(keys).difference(SOURCE_BY_KEY))
    if unknown:
        raise SystemExit(f"unknown source key(s): {', '.join(unknown)}")
    disabled = [key for key in keys if key in DISABLED_SOURCE_REASONS]
    if disabled:
        details = "; ".join(
            f"{key}: {DISABLED_SOURCE_REASONS[key]}" for key in disabled
        )
        raise SystemExit(f"disabled source(s): {details}")
    return [SOURCE_BY_KEY[key] for key in keys]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest configured F1 editorial/team/community sources")
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="source key to ingest; repeatable; defaults to all active sources",
    )
    parser.add_argument("--limit", type=int, default=20, help="maximum items per source")
    parser.add_argument("--list-sources", action="store_true", help="print configured source keys")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    if args.list_sources:
        for source in SOURCES:
            print(f"{source.key}\tactive")
        for source in DISABLED_SOURCES:
            print(
                f"{source.key}\tdisabled\t"
                f"{DISABLED_SOURCE_REASONS[source.key]}"
            )
        return
    stats = await ingest(_selected_sources(args.source), limit=max(1, args.limit))
    print(
        json.dumps(
            {
                "persisted": stats.persisted,
                "entity_links": stats.entity_links,
                "cluster_candidates": stats.cluster_candidates,
                "stories_created": stats.stories_created,
                "stories_attached": stats.stories_attached,
                "stories_existing": stats.stories_existing,
                "stories_merged": stats.stories_merged,
                "stories_skipped": stats.stories_skipped,
                "failures": stats.failures,
                "sources": [asdict(item) for item in stats.sources],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(async_main())
