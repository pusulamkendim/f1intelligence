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
class CuratedDriverPortrait:
    person_slug: str
    source_provider: str
    source_page_url: str
    image_url: str
    portrait_variant: str
    caption: str
    preferred_for: tuple[str, ...]


@dataclass(frozen=True)
class GroupPhotoSeed:
    source_asset_id: str
    page_url: str
    image_url: str
    caption: str


CURATED_DRIVER_PORTRAITS: tuple[CuratedDriverPortrait, ...] = (
    CuratedDriverPortrait(
        person_slug="lando-norris",
        source_provider="formula1.com",
        source_page_url="https://www.formula1.com/en/drivers/lando-norris",
        image_url=(
            "https://media.formula1.com/image/upload/"
            "c_fill,w_720/q_auto/v1740000001/common/f1/2026/"
            "mclaren/lannor01/2026mclarenlannor01right.webp"
        ),
        portrait_variant="primary_icon",
        caption="Lando Norris — 2026 Formula 1 official driver portrait",
        preferred_for=("charts", "driver_card", "standings"),
    ),
    CuratedDriverPortrait(
        person_slug="oscar-piastri",
        source_provider="formula1.com",
        source_page_url="https://www.formula1.com/en/drivers/oscar-piastri",
        image_url=(
            "https://media.formula1.com/image/upload/"
            "c_fill,w_720/q_auto/v1740000001/common/f1/2026/"
            "mclaren/oscpia01/2026mclarenoscpia01right.webp"
        ),
        portrait_variant="primary_icon",
        caption="Oscar Piastri — 2026 Formula 1 official driver portrait",
        preferred_for=("charts", "driver_card", "standings"),
    ),
    CuratedDriverPortrait(
        person_slug="max-verstappen",
        source_provider="formula1.com",
        source_page_url="https://www.formula1.com/en/drivers/max-verstappen",
        image_url=(
            "https://media.formula1.com/image/upload/"
            "c_fill,w_720/q_auto/v1740000001/common/f1/2026/"
            "redbullracing/maxver01/2026redbullracingmaxver01right.webp"
        ),
        portrait_variant="primary_icon",
        caption="Max Verstappen — 2026 Formula 1 official driver portrait",
        preferred_for=("charts", "driver_card", "standings"),
    ),
    CuratedDriverPortrait(
        person_slug="isack-hadjar",
        source_provider="formula1.com",
        source_page_url="https://www.formula1.com/en/drivers/isack-hadjar",
        image_url=(
            "https://media.formula1.com/image/upload/"
            "c_fill,w_720/q_auto/v1740000001/common/f1/2026/"
            "redbullracing/isahad01/2026redbullracingisahad01right.webp"
        ),
        portrait_variant="primary_icon",
        caption="Isack Hadjar — 2026 Formula 1 official driver portrait",
        preferred_for=("charts", "driver_card", "standings"),
    ),
    CuratedDriverPortrait(
        person_slug="george-russell",
        source_provider="formula1.com",
        source_page_url="https://www.formula1.com/en/drivers/george-russell",
        image_url=(
            "https://media.formula1.com/image/upload/"
            "c_fill,w_720/q_auto/v1740000001/common/f1/2026/"
            "mercedes/georus01/2026mercedesgeorus01right.webp"
        ),
        portrait_variant="primary_icon",
        caption="George Russell — 2026 Formula 1 official driver portrait",
        preferred_for=("charts", "driver_card", "standings"),
    ),
    CuratedDriverPortrait(
        person_slug="kimi-antonelli",
        source_provider="formula1.com",
        source_page_url="https://www.formula1.com/en/drivers/kimi-antonelli",
        image_url=(
            "https://media.formula1.com/image/upload/"
            "c_fill,w_720/q_auto/v1740000001/common/f1/2026/"
            "mercedes/andant01/2026mercedesandant01right.webp"
        ),
        portrait_variant="primary_icon",
        caption="Kimi Antonelli — 2026 Formula 1 official driver portrait",
        preferred_for=("charts", "driver_card", "standings"),
    ),
    CuratedDriverPortrait(
        person_slug="lewis-hamilton",
        source_provider="formula1.com",
        source_page_url="https://www.formula1.com/en/drivers/lewis-hamilton",
        image_url=(
            "https://media.formula1.com/image/upload/"
            "c_fill,w_720/q_auto/v1740000001/common/f1/2026/"
            "ferrari/lewham01/2026ferrarilewham01right.webp"
        ),
        portrait_variant="primary_icon",
        caption="Lewis Hamilton — 2026 Formula 1 official driver portrait",
        preferred_for=("charts", "driver_card", "standings"),
    ),
    CuratedDriverPortrait(
        person_slug="charles-leclerc",
        source_provider="formula1.com",
        source_page_url="https://www.formula1.com/en/drivers/charles-leclerc",
        image_url=(
            "https://media.formula1.com/image/upload/"
            "c_fill,w_720/q_auto/v1740000001/common/f1/2026/"
            "ferrari/chalec01/2026ferrarichalec01right.webp"
        ),
        portrait_variant="primary_icon",
        caption="Charles Leclerc — 2026 Formula 1 official driver portrait",
        preferred_for=("charts", "driver_card", "standings"),
    ),
    CuratedDriverPortrait(
        person_slug="max-verstappen",
        source_provider="redbullracing.com",
        source_page_url="https://www.redbullracing.com/int-en/team",
        image_url=(
            "https://www.redbullracing.com/_next/image?"
            "q=75&url=%2F_next%2Fstatic%2Fmedia%2Fmax-verstappen.ac2a5010.png&w=640"
        ),
        portrait_variant="studio_upper_body",
        caption="Max Verstappen — 2026 Oracle Red Bull Racing team portrait",
        preferred_for=("driver_card", "feature_graphic"),
    ),
    CuratedDriverPortrait(
        person_slug="isack-hadjar",
        source_provider="redbullracing.com",
        source_page_url="https://www.redbullracing.com/int-en/team",
        image_url=(
            "https://www.redbullracing.com/_next/image?"
            "q=75&url=%2F_next%2Fstatic%2Fmedia%2Fisack-hadjar.a13a3e30.png&w=640"
        ),
        portrait_variant="studio_upper_body",
        caption="Isack Hadjar — 2026 Oracle Red Bull Racing team portrait",
        preferred_for=("driver_card", "feature_graphic"),
    ),
    CuratedDriverPortrait(
        person_slug="george-russell",
        source_provider="formula1.com",
        source_page_url="https://www.formula1.com/en/drivers/george-russell",
        image_url=(
            "https://media.formula1.com/image/upload/"
            "t_16by9North/c_fit%2Cw_3200%2Ch_1800/q_auto/v1740000001/"
            "trackside-images/2026/F1_Grand_Prix_Of_Japan___Practice/2268554779.webp"
        ),
        portrait_variant="contextual_portrait",
        caption="George Russell — 2026 Formula 1 high-resolution portrait",
        preferred_for=("driver_card", "feature_graphic"),
    ),
    CuratedDriverPortrait(
        person_slug="kimi-antonelli",
        source_provider="formula1.com",
        source_page_url="https://www.formula1.com/en/drivers/kimi-antonelli",
        image_url=(
            "https://media.formula1.com/image/upload/"
            "t_16by9Centre/c_fit%2Cw_3200%2Ch_1800/q_auto/v1740000001/"
            "trackside-images/2026/F1_Grand_Prix_Of_Japan/2268884816.webp"
        ),
        portrait_variant="contextual_portrait",
        caption="Kimi Antonelli — 2026 Formula 1 high-resolution portrait",
        preferred_for=("driver_card", "feature_graphic"),
    ),
    CuratedDriverPortrait(
        person_slug="lewis-hamilton",
        source_provider="formula1.com",
        source_page_url="https://www.formula1.com/en/drivers/lewis-hamilton",
        image_url=(
            "https://media.formula1.com/image/upload/"
            "t_16by9Centre/c_fit%2Cw_3200%2Ch_1800/q_auto/v1740000001/"
            "trackside-images/2026/F1_Grand_Prix_Of_Japan___Practice/2268577899.webp"
        ),
        portrait_variant="contextual_portrait",
        caption="Lewis Hamilton — 2026 Formula 1 high-resolution portrait",
        preferred_for=("driver_card", "feature_graphic"),
    ),
    CuratedDriverPortrait(
        person_slug="charles-leclerc",
        source_provider="formula1.com",
        source_page_url="https://www.formula1.com/en/drivers/charles-leclerc",
        image_url=(
            "https://media.formula1.com/image/upload/"
            "t_16by9North/c_fit%2Cw_3200%2Ch_1800/q_auto/v1740000001/"
            "trackside-images/2026/F1_Grand_Prix_Of_Japan___Practice/2268572376.webp"
        ),
        portrait_variant="contextual_portrait",
        caption="Charles Leclerc — 2026 Formula 1 high-resolution portrait",
        preferred_for=("driver_card", "feature_graphic"),
    ),
    CuratedDriverPortrait(
        person_slug="lando-norris",
        source_provider="mclaren.com",
        source_page_url="https://www.mclaren.com/racing/team/lando-norris/",
        image_url=(
            "https://images.ctfassets.net/gy95mqeyjg28/"
            "2gtUGEfRaDDXILBqVSIj4Q/"
            "c57799cbb8b458aca1b953dc5d1703cc/"
            "launch_2026_lando_desktop.jpg?fm=webp&q=75&w=3840"
        ),
        portrait_variant="studio_full_body",
        caption="Lando Norris in 2026 McLaren overalls",
        preferred_for=("driver_card", "feature_graphic"),
    ),
    CuratedDriverPortrait(
        person_slug="oscar-piastri",
        source_provider="mclaren.com",
        source_page_url="https://www.mclaren.com/racing/team/oscar-piastri/",
        image_url=(
            "https://images.ctfassets.net/gy95mqeyjg28/"
            "5eFFdEkNfSJRI8fjAmk1IX/"
            "6463449c24e60400e609c14b95bdb37d/"
            "launch_2026_oscar_desktop.jpg?fm=webp&q=75&w=3840"
        ),
        portrait_variant="studio_full_body",
        caption="Oscar Piastri in 2026 McLaren overalls",
        preferred_for=("driver_card", "feature_graphic"),
    ),
)


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
    curated_portraits_persisted: int = 0
    curated_portrait_entity_links: int = 0
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


async def _persist_curated_portrait(
    session,
    *,
    seed: CuratedDriverPortrait,
    row: DriverPortraitRow,
    season: int,
) -> None:
    asset_id = await upsert_media_asset(
        session,
        MediaAssetInput(
            source_provider=seed.source_provider,
            discovered_via=seed.source_provider,
            original_url=seed.image_url,
            discovery_page_url=seed.source_page_url,
            caption=seed.caption,
            alt_text=seed.caption,
            content_role="driver_portrait",
            season=season,
            rights_evidence_url=seed.source_page_url,
            metadata={
                "media_kind": "curated_driver_portrait",
                "portrait_variant": seed.portrait_variant,
                "person_slug": row.person_slug,
                "driver_name": row.display_name,
                "team_name": row.team_name,
                "season": season,
                "preferred_for": list(seed.preferred_for),
                "curated": True,
            },
        ),
    )
    await link_media_asset_entity(
        session,
        media_asset_id=asset_id,
        entity_id=row.entity_id,
        relation_type="depicted",
        confidence=100,
        match_method="curated_driver_portrait_v1",
    )


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

            rows_by_slug = {row.person_slug: row for row in rows}
            for seed in CURATED_DRIVER_PORTRAITS:
                row = rows_by_slug.get(seed.person_slug)
                if row is None:
                    stats.failures += 1
                    continue
                try:
                    async with session.begin_nested():
                        await _persist_curated_portrait(
                            session,
                            seed=seed,
                            row=row,
                            season=season,
                        )
                except Exception:
                    stats.failures += 1
                    continue
                stats.curated_portraits_persisted += 1
                stats.curated_portrait_entity_links += 1

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
