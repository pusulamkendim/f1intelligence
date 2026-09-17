from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import asdict, dataclass

import httpx

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ingestion.formula1_com import (
    Formula1Article,
    discover_formula1_article_urls,
    parse_formula1_article,
)
from app.ingestion.source_item_store import (
    SourceItemRecord,
    load_entity_aliases,
    persist_source_item_with_entities,
)

PROVIDER = "formula1.com"
SOURCE_CLASS = "official_editorial"
RIGHTS_POLICY = "metadata_summary_excerpt_only"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    discovered: int = 0
    fetched: int = 0
    persisted: int = 0
    entity_links: int = 0
    failures: int = 0


def article_to_source_item(article: Formula1Article) -> SourceItemRecord:
    return SourceItemRecord(
        provider=PROVIDER,
        external_id=article.external_id,
        source_type="article",
        source_class=SOURCE_CLASS,
        source_url=article.canonical_url,
        title=article.title,
        standfirst=article.description,
        body_excerpt=article.body_excerpt,
        author=article.author,
        language=article.language,
        published_at=article.published_at,
        content_hash=article.content_hash,
        rights_policy=RIGHTS_POLICY,
        raw_metadata=article.raw_metadata,
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
            delay = settings.source_http_retry_backoff_seconds * (2 ** (attempt - 1))
            logger.warning(
                "Formula1.com request failed on attempt %s/%s for %s (%s); retrying in %.1fs",
                attempt,
                settings.source_http_retries,
                url,
                type(last_error).__name__,
                delay,
            )
            await asyncio.sleep(delay)

    raise RuntimeError(
        f"Formula1.com request failed after {settings.source_http_retries} attempts for {url}"
    ) from last_error


async def discover_urls(client: httpx.AsyncClient, *, limit: int, pages: int) -> list[str]:
    settings = get_settings()
    urls: list[str] = []
    seen: set[str] = set()
    for page in range(1, pages + 1):
        page_url = settings.formula1_latest_url
        if page > 1:
            separator = "&" if "?" in page_url else "?"
            page_url = f"{page_url}{separator}page={page}"
        response = await _get_with_retries(client, page_url)
        for url in discover_formula1_article_urls(response.text, base_url=str(response.url)):
            if url in seen:
                continue
            seen.add(url)
            urls.append(url)
            if len(urls) >= limit:
                return urls
    return urls


async def fetch_articles(*, limit: int, pages: int) -> tuple[list[Formula1Article], int, int]:
    settings = get_settings()
    headers = {
        "User-Agent": settings.source_user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    }
    articles: list[Formula1Article] = []
    failures = 0

    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=_timeout(),
    ) as client:
        urls = await discover_urls(client, limit=limit, pages=pages)
        for url in urls:
            try:
                response = await _get_with_retries(client, url)
                articles.append(parse_formula1_article(response.text, requested_url=str(response.url)))
            except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                failures += 1
                logger.warning("Skipping Formula1.com article %s: %s", url, exc)

    return articles, len(urls), failures


async def ingest(*, limit: int, pages: int) -> IngestionStats:
    articles, discovered, failures = await fetch_articles(limit=limit, pages=pages)
    stats = IngestionStats(discovered=discovered, fetched=len(articles), failures=failures)

    async with SessionLocal() as session:
        async with session.begin():
            aliases = await load_entity_aliases(session)
            for article in articles:
                season = article.published_at.year if article.published_at is not None else None
                _, classifications = await persist_source_item_with_entities(
                    session,
                    article_to_source_item(article),
                    season=season,
                    aliases=aliases,
                )
                stats.persisted += 1
                stats.entity_links += len(classifications)

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest recent Formula1.com editorial articles")
    parser.add_argument("--limit", type=int, default=25, help="maximum articles to fetch")
    parser.add_argument("--pages", type=int, default=3, help="maximum /en/latest pages to scan")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    stats = await ingest(limit=max(1, args.limit), pages=max(1, args.pages))
    print(json.dumps(asdict(stats), indent=2))


if __name__ == "__main__":
    asyncio.run(async_main())
