from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import get_settings
from app.ingestion.editorial_sources import discover_listing_urls, parse_article_html, parse_feed
from app.ingestion.formula1_com import discover_formula1_article_urls, parse_formula1_article
from app.ingestion.source_registry import SOURCES


@pytest.mark.asyncio
async def test_live_source_smoke_diagnostic() -> None:
    settings = get_settings()
    headers = {
        "User-Agent": "F1Intelligence/0.1 live-source-smoke",
        "Accept": "application/rss+xml, application/atom+xml, text/html;q=0.9, */*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    }
    timeout = httpx.Timeout(connect=10.0, read=25.0, write=10.0, pool=10.0)
    results: list[dict[str, object]] = []

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=timeout) as client:
        # Formula1.com adapter
        f1_result: dict[str, object] = {"source": "formula1.com", "mode": "listing"}
        try:
            response = await client.get(settings.formula1_latest_url)
            response.raise_for_status()
            urls = discover_formula1_article_urls(response.text, base_url=str(response.url))
            f1_result["status"] = response.status_code
            f1_result["discovered"] = len(urls)
            if urls:
                article_response = await client.get(urls[0])
                article_response.raise_for_status()
                article = parse_formula1_article(article_response.text, requested_url=str(article_response.url))
                f1_result["article"] = article.title
                f1_result["ok"] = True
            else:
                f1_result["ok"] = False
                f1_result["error"] = "no article links discovered"
        except Exception as exc:
            f1_result["ok"] = False
            f1_result["error"] = f"{type(exc).__name__}: {exc}"
        results.append(f1_result)

        # Generic configured sources
        for source in SOURCES:
            result: dict[str, object] = {
                "source": source.key,
                "provider": source.provider,
                "mode": source.mode,
            }
            try:
                response = await client.get(source.discovery_url)
                response.raise_for_status()
                result["status"] = response.status_code
                result["content_type"] = response.headers.get("content-type")
                if source.mode == "rss":
                    items = parse_feed(response.text, source)
                    result["discovered"] = len(items)
                    if items:
                        result["item"] = items[0].title
                        result["ok"] = True
                    else:
                        result["ok"] = False
                        result["error"] = "feed parsed but returned zero items"
                else:
                    urls = discover_listing_urls(response.text, source)
                    result["discovered"] = len(urls)
                    if not urls:
                        result["ok"] = False
                        result["error"] = "listing fetched but path matcher found zero article URLs"
                    else:
                        article_response = await client.get(urls[0])
                        article_response.raise_for_status()
                        article = parse_article_html(
                            article_response.text,
                            requested_url=str(article_response.url),
                            source=source,
                        )
                        result["article_url"] = article.canonical_url
                        result["article"] = article.title
                        result["ok"] = True
            except Exception as exc:
                result["ok"] = False
                result["error"] = f"{type(exc).__name__}: {exc}"
            results.append(result)

    # Diagnostic branch only: always fail so GitHub Actions exposes the complete
    # captured result payload in the job log. This file must never be merged.
    raise AssertionError("LIVE_SOURCE_SMOKE_RESULTS\n" + json.dumps(results, indent=2, default=str))
