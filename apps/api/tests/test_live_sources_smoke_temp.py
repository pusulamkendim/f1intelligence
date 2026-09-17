import asyncio
import json

import httpx
import pytest

from app.core.config import get_settings
from app.ingestion.formula1_com import (
    discover_formula1_article_urls,
    parse_formula1_article,
)
from app.ingestion.run_sources import (
    COMMUNITY_SOURCE_GAP_SECONDS,
    _fetch_source_items,
)
from app.ingestion.source_registry import SOURCES


@pytest.mark.asyncio
async def test_live_source_smoke_diagnostic() -> None:
    settings = get_settings()
    headers = {
        "User-Agent": settings.source_user_agent,
        "Accept": "application/rss+xml, application/atom+xml, text/html;q=0.9, */*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    }
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
    results: list[dict[str, object]] = []

    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=timeout,
    ) as client:
        formula1: dict[str, object] = {"source": "formula1.com"}
        try:
            response = await client.get(settings.formula1_latest_url)
            response.raise_for_status()
            urls = discover_formula1_article_urls(response.text, base_url=str(response.url))
            formula1["discovered"] = len(urls)
            if not urls:
                raise RuntimeError("no article links discovered")
            article_response = await client.get(urls[0])
            article_response.raise_for_status()
            article = parse_formula1_article(
                article_response.text,
                requested_url=str(article_response.url),
            )
            formula1["item"] = article.title
            formula1["ok"] = True
        except Exception as exc:
            formula1["ok"] = False
            formula1["error"] = f"{type(exc).__name__}: {exc}"
        results.append(formula1)

        previous_was_community = False
        for source in SOURCES:
            if previous_was_community and source.source_class == "community_signal":
                await asyncio.sleep(COMMUNITY_SOURCE_GAP_SECONDS)
            result: dict[str, object] = {
                "source": source.key,
                "provider": source.provider,
                "mode": source.mode,
            }
            try:
                items, discovered, failures = await _fetch_source_items(
                    client,
                    source,
                    limit=1,
                )
                result["discovered"] = discovered
                result["failures"] = failures
                result["fetched"] = len(items)
                if not items:
                    raise RuntimeError("no usable item parsed")
                result["item"] = items[0].title
                result["url"] = items[0].canonical_url
                result["ok"] = True
            except Exception as exc:
                result["ok"] = False
                result["error"] = f"{type(exc).__name__}: {exc}"
            results.append(result)
            previous_was_community = source.source_class == "community_signal"

    raise AssertionError(
        "LIVE_SOURCE_SMOKE_RESULTS\n" + json.dumps(results, indent=2, default=str)
    )
