from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import asdict, dataclass, field

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
from app.ingestion.official_media_sources import (
    OFFICIAL_MEDIA_SOURCE_BY_KEY,
    OFFICIAL_MEDIA_SOURCES,
    OfficialMediaSource,
    access_block_reason,
    discover_source_pages,
    parse_official_media_page,
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
class MediaSourceStats:
    source: str
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
    unavailable: bool = False
    error: str | None = None


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
    sources: list[MediaSourceStats] = field(default_factory=list)


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
        r"\b(?:Formula\s*1|F1)\s+GP\b",
        "Grand Prix",
        value,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\bGP\b", "Grand Prix", normalized, flags=re.IGNORECASE)


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


def _timeout() -> httpx.Timeout:
    settings = get_settings()
    return httpx.Timeout(
        connect=settings.source_http_connect_timeout_seconds,
        read=settings.source_http_read_timeout_seconds,
        write=10.0,
        pool=10.0,
    )


def _headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "User-Agent": settings.source_user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    }


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


async def _persist_media_item(
    session,
    aliases,
    stats: MediaSourceStats,
    *,
    provider: str,
    page_title: str | None,
    page_url: str,
    caption: str | None,
    alt_text: str | None,
    image_url: str,
    content_role: str,
    team_slug: str | None = None,
    origin_provider: str | None = None,
    origin_asset_id: str | None = None,
    photographer: str | None = None,
    agency: str | None = None,
    rights_evidence_url: str | None = None,
    rights_note: str | None = None,
    season_hint: int | None = None,
    discovery_mode: str,
) -> None:
    stats.assets_seen += 1
    season = season_hint or _season_from_text(page_title, caption)
    normalized_title = _normalize_media_context(page_title)
    normalized_caption = _normalize_media_context(caption)

    classifications = classify_source_item_entities(
        SourceItemText(
            title=normalized_title
            or normalized_caption
            or "Formula 1 media",
            standfirst=normalized_caption,
            season=season,
            race_season=season,
            source_context_team_slug=team_slug,
        ),
        aliases,
    )
    race_id = await _race_id_from_classifications(session, classifications)

    if race_id is not None:
        stats.assets_with_race += 1
    if classifications:
        stats.assets_with_entities += 1
    if content_role == "generic":
        stats.generic_assets += 1

    asset_id = await upsert_media_asset(
        session,
        MediaAssetInput(
            source_provider=provider,
            discovered_via=provider,
            original_url=image_url,
            origin_provider=origin_provider,
            origin_asset_id=origin_asset_id,
            discovery_page_url=page_url,
            caption=caption,
            alt_text=alt_text,
            photographer=photographer,
            agency=agency,
            content_role=content_role,
            season=season,
            race_id=race_id,
            rights_evidence_url=rights_evidence_url,
            metadata={
                "page_title": page_title,
                "normalized_page_title": normalized_title,
                "rights_note": rights_note,
                "team_slug": team_slug,
                "discovery_mode": discovery_mode,
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
    stats.story_candidates += await match_media_asset_to_stories(
        session,
        asset_id,
    )


async def ingest_official_source(
    source: OfficialMediaSource,
    *,
    page_limit: int,
    asset_limit_per_page: int,
) -> MediaSourceStats:
    settings = get_settings()
    stats = MediaSourceStats(source=source.key)

    try:
        async with httpx.AsyncClient(
            headers=_headers(),
            follow_redirects=True,
            timeout=_timeout(),
        ) as client:
            listing = await _get_with_retries(client, source.discovery_url)
            blocked = access_block_reason(
                listing.text,
                response_url=str(listing.url),
            )
            if blocked:
                stats.unavailable = True
                stats.error = blocked
                return stats

            page_urls = discover_source_pages(listing.text, source=source)
            stats.galleries_discovered = len(page_urls)

            async with SessionLocal() as session:
                async with session.begin():
                    aliases = await load_entity_aliases(session)

                    for page_url in page_urls[: max(0, page_limit)]:
                        try:
                            response = await _get_with_retries(client, page_url)
                            blocked = access_block_reason(
                                response.text,
                                response_url=str(response.url),
                            )
                            if blocked:
                                stats.failures += 1
                                stats.error = blocked
                                continue
                            items = parse_official_media_page(
                                response.text,
                                page_url=str(response.url),
                                source=source,
                            )
                            stats.galleries_fetched += 1
                        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                            stats.failures += 1
                            stats.error = f"{type(exc).__name__}: {exc}"
                            continue

                        for item in items[: max(0, asset_limit_per_page)]:
                            await _persist_media_item(
                                session,
                                aliases,
                                stats,
                                provider=source.provider,
                                page_title=item.page_title,
                                page_url=item.page_url,
                                caption=item.caption,
                                alt_text=item.alt_text,
                                image_url=item.image_url,
                                content_role=item.content_role,
                                team_slug=source.team_slug,
                                origin_provider=item.origin_provider,
                                origin_asset_id=item.origin_asset_id,
                                photographer=item.photographer,
                                agency=item.agency,
                                rights_evidence_url=source.rights_evidence_url,
                                rights_note=item.rights_note,
                                season_hint=item.season,
                                discovery_mode="official_media_page",
                            )

                        if settings.editorial_source_min_interval_seconds:
                            await asyncio.sleep(
                                settings.editorial_source_min_interval_seconds
                            )
    except Exception as exc:  # isolate one provider from the rest of the run
        stats.failures += 1
        stats.error = f"{type(exc).__name__}: {exc}"
    return stats


async def ingest_f1_fansite(
    *,
    page_limit: int = 3,
    asset_limit_per_page: int = 100,
) -> MediaSourceStats:
    settings = get_settings()
    stats = MediaSourceStats(source="f1-fansite")

    try:
        async with httpx.AsyncClient(
            headers=_headers(),
            follow_redirects=True,
            timeout=_timeout(),
        ) as client:
            index = await _get_with_retries(client, F1_FANSITE_INDEX)
            blocked = access_block_reason(index.text, response_url=str(index.url))
            if blocked:
                stats.unavailable = True
                stats.error = blocked
                return stats

            gallery_urls = discover_gallery_urls(
                index.text,
                base_url=str(index.url),
            )
            stats.galleries_discovered = len(gallery_urls)

            async with SessionLocal() as session:
                async with session.begin():
                    aliases = await load_entity_aliases(session)

                    for gallery_url in gallery_urls[: max(0, page_limit)]:
                        try:
                            response = await _get_with_retries(client, gallery_url)
                            blocked = access_block_reason(
                                response.text,
                                response_url=str(response.url),
                            )
                            if blocked:
                                stats.failures += 1
                                stats.error = blocked
                                continue
                            items = parse_gallery_html(
                                response.text,
                                gallery_url=str(response.url),
                            )
                            stats.galleries_fetched += 1
                        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                            stats.failures += 1
                            stats.error = f"{type(exc).__name__}: {exc}"
                            continue

                        for item in items[: max(0, asset_limit_per_page)]:
                            await _persist_media_item(
                                session,
                                aliases,
                                stats,
                                provider="f1-fansite.com",
                                page_title=item.gallery_title,
                                page_url=item.gallery_url,
                                caption=item.caption,
                                alt_text=item.alt_text,
                                image_url=item.image_url,
                                content_role=item.content_role,
                                origin_provider=item.origin_provider,
                                origin_asset_id=item.origin_asset_id,
                                photographer=item.photographer,
                                agency=item.agency,
                                rights_evidence_url=(
                                    "https://www.f1-fansite.com/disclaimer/"
                                ),
                                rights_note=item.rights_note,
                                discovery_mode="wallpaper_gallery",
                            )

                        if settings.editorial_source_min_interval_seconds:
                            await asyncio.sleep(
                                settings.editorial_source_min_interval_seconds
                            )
    except Exception as exc:  # optional fallback must never abort official sources
        stats.failures += 1
        stats.error = f"{type(exc).__name__}: {exc}"
    return stats


def _merge_source_stats(
    output: MediaDiscoveryStats,
    item: MediaSourceStats,
) -> None:
    output.sources.append(item)
    for field_name in (
        "galleries_discovered",
        "galleries_fetched",
        "assets_seen",
        "assets_persisted",
        "assets_with_race",
        "assets_with_entities",
        "generic_assets",
        "entity_links",
        "story_candidates",
        "failures",
    ):
        setattr(
            output,
            field_name,
            getattr(output, field_name) + getattr(item, field_name),
        )


def _selected_source_keys(keys: list[str]) -> list[str]:
    if not keys or keys == ["all"]:
        return [source.key for source in OFFICIAL_MEDIA_SOURCES]

    known = set(OFFICIAL_MEDIA_SOURCE_BY_KEY) | {"f1-fansite"}
    unknown = sorted(set(keys).difference(known))
    if unknown:
        raise SystemExit(f"unknown media source(s): {', '.join(unknown)}")
    return keys


async def ingest_media(
    source_keys: list[str],
    *,
    page_limit: int,
    asset_limit_per_page: int,
) -> MediaDiscoveryStats:
    output = MediaDiscoveryStats()
    for key in source_keys:
        if key == "f1-fansite":
            item = await ingest_f1_fansite(
                page_limit=page_limit,
                asset_limit_per_page=asset_limit_per_page,
            )
        else:
            item = await ingest_official_source(
                OFFICIAL_MEDIA_SOURCE_BY_KEY[key],
                page_limit=page_limit,
                asset_limit_per_page=asset_limit_per_page,
            )
        _merge_source_stats(output, item)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover rights-aware F1 media references"
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help=(
            "media source key; repeatable. Defaults to formula1, williams and alpine. "
            "Use f1-fansite explicitly as an optional fallback."
        ),
    )
    parser.add_argument(
        "--page-limit",
        "--gallery-limit",
        dest="page_limit",
        type=int,
        default=3,
        help="maximum media/article pages to fetch per source",
    )
    parser.add_argument(
        "--asset-limit",
        type=int,
        default=100,
        help="maximum media assets to persist per fetched page",
    )
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    stats = await ingest_media(
        _selected_source_keys(args.source),
        page_limit=max(0, args.page_limit),
        asset_limit_per_page=max(0, args.asset_limit),
    )
    print(json.dumps(asdict(stats), indent=2))


if __name__ == "__main__":
    asyncio.run(async_main())
