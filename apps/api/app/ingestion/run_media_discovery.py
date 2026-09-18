from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import asdict, dataclass

import httpx
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ingestion.f1_fansite_media import (
    discover_gallery_urls,
    parse_gallery_html,
)
from app.ingestion.media_assets import (
    MediaAssetInput,
    match_media_asset_to_stories,
    reconcile_media_entities,
    upsert_media_asset,
)
from app.ingestion.source_item_entities import (
    SourceItemText,
    classify_source_item_entities,
)
from app.ingestion.source_item_store import load_entity_aliases

F1_FANSITE_INDEX = "https://www.f1-fansite.com/f1-wallpapers/"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_SEASON_RE = re.compile(r"\b(20\d{2})\b")


@dataclass
class MediaDiscoveryStats:
    galleries_discovered: int = 0
    galleries_fetched: int = 0
    assets_seen: int = 0
    assets_persisted: int = 0
    assets_with_race: int = 0
    assets_with_entities: int = 0
    generic_assets: int = 0
    entity_links: int = 0
    story_candidates: int = 0
    failures: int = 0


def _season_from_text(*values: str | None) -> int | None:
    for value in values:
        if not value:
            continue
        match = _SEASON_RE.search(value)
        if match:
            return int(match.group(1))
    return None


def _normalize_media_context(value: str | None) -> str | None:
    """Expand common gallery shorthand so canonical race aliases can match."""
    if not value:
        return value
    normalized = re.sub(
        r"\\b(?:Formula\\s*1|F1)\\s+GP\\b",
        "Grand Prix",
        value,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\\bGP\\b", "Grand Prix", normalized, flags=re.IGNORECASE)


async def _race_id_from_classifications(session, classifications):
    for item in classifications:
        if item.entity_type != "race":
            continue
        result = await session.execute(
            text(
                """
                SELECT id
                FROM races
                WHERE entity_id = :entity_id
                LIMIT 1
                """
            ),
            {"entity_id": item.entity_id},
        )
        race_id = result.scalar_one_or_none()
        if race_id is not None:
            return race_id
    return None


async def _get_with_retries(
    client: httpx.AsyncClient,
    url: str,
) -> httpx.Response:
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
            await asyncio.sleep(
                settings.source_http_retry_backoff_seconds * (2 ** (attempt - 1))
            )
    raise RuntimeError(f"media discovery request failed for {url}") from last_error


async def ingest_f1_fansite(
    *,
    gallery_limit: int = 3,
    asset_limit_per_gallery: int = 100,
) -> MediaDiscoveryStats:
    settings = get_settings()
    stats = MediaDiscoveryStats()
    headers = {
        "User-Agent": settings.source_user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    }
    timeout = httpx.Timeout(
        connect=settings.source_http_connect_timeout_seconds,
        read=settings.source_http_read_timeout_seconds,
        write=10.0,
        pool=10.0,
    )

    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=timeout,
    ) as client:
        index = await _get_with_retries(client, F1_FANSITE_INDEX)
        gallery_urls = discover_gallery_urls(
            index.text,
            base_url=str(index.url),
        )
        stats.galleries_discovered = len(gallery_urls)

        async with SessionLocal() as session:
            async with session.begin():
                aliases = await load_entity_aliases(session)

                for gallery_url in gallery_urls[: max(0, gallery_limit)]:
                    try:
                        response = await _get_with_retries(client, gallery_url)
                        items = parse_gallery_html(
                            response.text,
                            gallery_url=str(response.url),
                        )
                        stats.galleries_fetched += 1
                    except (httpx.HTTPError, RuntimeError, ValueError):
                        stats.failures += 1
                        continue

                    for item in items[: max(0, asset_limit_per_gallery)]:
                        stats.assets_seen += 1
                        season = _season_from_text(
                            item.gallery_title,
                            item.caption,
                        )
                        normalized_gallery_title = _normalize_media_context(
                            item.gallery_title
                        )
                        normalized_caption = _normalize_media_context(item.caption)
                        classification_text = SourceItemText(
                            title=normalized_gallery_title
                            or normalized_caption
                            or "Formula 1 media",
                            standfirst=normalized_caption,
                            season=season,
                            race_season=season,
                        )
                        classifications = classify_source_item_entities(
                            classification_text,
                            aliases,
                        )
                        race_id = await _race_id_from_classifications(
                            session,
                            classifications,
                        )
                        if race_id is not None:
                            stats.assets_with_race += 1
                        if classifications:
                            stats.assets_with_entities += 1
                        if item.content_role == "generic":
                            stats.generic_assets += 1

                        asset_id = await upsert_media_asset(
                            session,
                            MediaAssetInput(
                                source_provider="f1-fansite.com",
                                discovered_via="f1-fansite.com",
                                original_url=item.image_url,
                                origin_provider=item.origin_provider,
                                origin_asset_id=item.origin_asset_id,
                                discovery_page_url=item.gallery_url,
                                caption=item.caption,
                                alt_text=item.alt_text,
                                photographer=item.photographer,
                                agency=item.agency,
                                content_role=item.content_role,
                                season=season,
                                race_id=race_id,
                                rights_evidence_url=(
                                    "https://www.f1-fansite.com/disclaimer/"
                                ),
                                metadata={
                                    "gallery_title": item.gallery_title,
                                    "normalized_gallery_title": normalized_gallery_title,
                                    "rights_note": item.rights_note,
                                    "discovery_mode": "wallpaper_gallery",
                                },
                            ),
                        )
                        await reconcile_media_entities(
                            session,
                            media_asset_id=asset_id,
                            classifications=classifications,
                        )
                        stats.assets_persisted += 1
                        stats.entity_links += len(classifications)
                        stats.story_candidates += (
                            await match_media_asset_to_stories(
                                session,
                                asset_id,
                            )
                        )

                    if settings.editorial_source_min_interval_seconds:
                        await asyncio.sleep(
                            settings.editorial_source_min_interval_seconds
                        )

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover rights-aware F1 media references"
    )
    parser.add_argument("--gallery-limit", type=int, default=3)
    parser.add_argument("--asset-limit", type=int, default=100)
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    stats = await ingest_f1_fansite(
        gallery_limit=max(0, args.gallery_limit),
        asset_limit_per_gallery=max(0, args.asset_limit),
    )
    print(json.dumps(asdict(stats), indent=2))


if __name__ == "__main__":
    asyncio.run(async_main())
