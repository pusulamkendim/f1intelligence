from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from uuid import UUID

from sqlalchemy import text

from app.db.session import SessionLocal
from app.ingestion.media_assets import (
    MediaAssetInput,
    link_media_asset_entity,
    upsert_media_asset,
)


@dataclass(frozen=True)
class DriverPortraitRow:
    entity_id: UUID
    person_slug: str
    display_name: str
    team_name: str
    car_number: int | None
    headshot_url: str | None
    source_url: str | None


@dataclass(frozen=True)
class GroupPhotoSeed:
    source_asset_id: str
    page_url: str
    image_url: str
    caption: str


GROUP_PHOTOS: tuple[GroupPhotoSeed, ...] = (
    GroupPhotoSeed(
        source_asset_id="2026-f1-class-preseason-group",
        page_url=(
            "https://www.formula1.com/en/video/"
            "behind-the-scenes-of-the-class-of-2026-shoot."
            "1857390752347742667"
        ),
        image_url=(
            "https://d2n9h2wits23hf.cloudfront.net/image/v1/static/"
            "6057949432001/9795013a-532b-4e5a-b264-58ff07b1b54a/"
            "a028cecf-75c1-44c7-921a-1c44039987c8/864x486/match/image.jpg"
        ),
        caption="2026 Formula 1 drivers official pre-season group photo",
    ),
)


@dataclass
class DriverMediaStats:
    season: int
    grid_drivers: int = 0
    headshots_found: int = 0
    portraits_persisted: int = 0
    portrait_entity_links: int = 0
    group_photos_persisted: int = 0
    group_photo_entity_links: int = 0
    failures: int = 0


async def load_grid_driver_portraits(
    session,
    *,
    season: int,
) -> list[DriverPortraitRow]:
    result = await session.execute(
        text(
            """
            SELECT
                p.entity_id,
                p.slug AS person_slug,
                p.display_name,
                t.name AS team_name,
                tpr.car_number,
                portrait.headshot_reference_url,
                portrait.source_url
            FROM team_person_roles tpr
            JOIN persons p ON p.id = tpr.person_id
            JOIN teams t ON t.id = tpr.team_id
            LEFT JOIN LATERAL (
                SELECT
                    se.headshot_reference_url,
                    se.source_url
                FROM session_entries se
                JOIN race_sessions rs ON rs.id = se.session_id
                JOIN races r ON r.id = rs.race_id
                WHERE se.driver_entity_id = p.entity_id
                  AND r.season = :season
                  AND NULLIF(se.headshot_reference_url, '') IS NOT NULL
                ORDER BY rs.starts_at DESC NULLS LAST, se.fetched_at DESC
                LIMIT 1
            ) portrait ON true
            WHERE tpr.role = 'driver'
              AND tpr.season = :season
            ORDER BY t.name, tpr.car_number NULLS LAST, p.display_name
            """
        ),
        {"season": season},
    )
    return [
        DriverPortraitRow(
            entity_id=row["entity_id"],
            person_slug=str(row["person_slug"]),
            display_name=str(row["display_name"]),
            team_name=str(row["team_name"]),
            car_number=row["car_number"],
            headshot_url=row["headshot_reference_url"],
            source_url=row["source_url"],
        )
        for row in result.mappings().all()
    ]


async def _persist_portrait(
    session,
    *,
    row: DriverPortraitRow,
    season: int,
) -> bool:
    if not row.headshot_url:
        return False

    source_url = row.source_url or "https://api.openf1.org/v1/drivers"
    asset_id = await upsert_media_asset(
        session,
        MediaAssetInput(
            source_provider="openf1_headshot",
            discovered_via="openf1_headshot",
            original_url=row.headshot_url,
            discovery_page_url=source_url,
            caption=f"{row.display_name} — {season} Formula 1 driver portrait",
            alt_text=f"{row.display_name} {season} Formula 1 driver portrait",
            content_role="driver_portrait",
            season=season,
            metadata={
                "media_kind": "canonical_driver_portrait",
                "canonical_key": f"{season}:{row.person_slug}",
                "person_slug": row.person_slug,
                "driver_name": row.display_name,
                "team_name": row.team_name,
                "car_number": row.car_number,
                "season": season,
                "provider": "openf1",
            },
        ),
    )
    await link_media_asset_entity(
        session,
        media_asset_id=asset_id,
        entity_id=row.entity_id,
        relation_type="depicted",
        confidence=100,
        match_method="openf1_driver_portrait_v1",
    )
    return True


async def _persist_group_photo(
    session,
    *,
    seed: GroupPhotoSeed,
    season: int,
    driver_entity_ids: list[UUID],
) -> int:
    asset_id = await upsert_media_asset(
        session,
        MediaAssetInput(
            source_provider="formula1.com",
            discovered_via="formula1.com",
            original_url=seed.image_url,
            discovery_page_url=seed.page_url,
            caption=seed.caption,
            alt_text=seed.caption,
            content_role="generic",
            season=season,
            metadata={
                "media_kind": "grid_group",
                "seed_id": seed.source_asset_id,
                "group_scope": f"{season}_formula_1_grid",
                "season": season,
                "driver_count": len(driver_entity_ids),
                "rights_note": (
                    "Official Formula1.com discovery reference; "
                    "publication rights remain restricted."
                ),
            },
        ),
    )

    for entity_id in driver_entity_ids:
        await link_media_asset_entity(
            session,
            media_asset_id=asset_id,
            entity_id=entity_id,
            relation_type="depicted",
            confidence=100,
            match_method="official_grid_group_v1",
        )
    return len(driver_entity_ids)


async def ingest_driver_media(*, season: int = 2026) -> DriverMediaStats:
    stats = DriverMediaStats(season=season)

    async with SessionLocal() as session:
        async with session.begin():
            rows = await load_grid_driver_portraits(session, season=season)
            stats.grid_drivers = len(rows)
            driver_entity_ids = [row.entity_id for row in rows]

            for row in rows:
                if row.headshot_url:
                    stats.headshots_found += 1
                try:
                    async with session.begin_nested():
                        persisted = await _persist_portrait(
                            session,
                            row=row,
                            season=season,
                        )
                except Exception:
                    stats.failures += 1
                    continue
                if persisted:
                    stats.portraits_persisted += 1
                    stats.portrait_entity_links += 1

            if driver_entity_ids:
                for seed in GROUP_PHOTOS:
                    try:
                        async with session.begin_nested():
                            links = await _persist_group_photo(
                                session,
                                seed=seed,
                                season=season,
                                driver_entity_ids=driver_entity_ids,
                            )
                    except Exception:
                        stats.failures += 1
                        continue
                    stats.group_photos_persisted += 1
                    stats.group_photo_entity_links += links

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest canonical F1 driver portraits and grid group photos"
    )
    parser.add_argument("--season", type=int, default=2026)
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    stats = await ingest_driver_media(season=args.season)
    print(json.dumps(asdict(stats), indent=2))


if __name__ == "__main__":
    asyncio.run(async_main())
