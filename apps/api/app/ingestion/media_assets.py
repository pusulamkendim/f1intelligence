from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.media_source_registry import policy_for_provider
from app.ingestion.source_item_entities import SourceItemEntityClassification

EVENT_ROLES = {
    "podium",
    "winner",
    "race_start",
    "overtake",
    "incident",
    "pit_stop",
    "celebration",
}
RACE_ONLY_STORY_ROLES = EVENT_ROLES | {"race_hero"}

ROLE_KEYWORDS = {
    "podium": ("podium", "trophy", "champagne"),
    "winner": ("wins", "winner", "victory", "won"),
    "race_start": ("start", "turn one", "first lap"),
    "overtake": ("overtake", "passes", "battle", "fight"),
    "incident": ("crash", "collision", "contact", "spin", "incident"),
    "pit_stop": ("pit stop", "pitstop", "pit lane"),
    "strategy": ("strategy", "tyre", "tire", "undercut", "overcut"),
    "technical_detail": ("upgrade", "floor", "wing", "technical"),
    "celebration": ("celebrat", "champagne", "parc ferme"),
    "reaction": ("react", "reaction", "speaks", "says"),
}


@dataclass(frozen=True)
class MediaAssetInput:
    source_provider: str
    discovered_via: str
    original_url: str
    content_role: str = "generic"
    source_asset_id: str | None = None
    origin_provider: str | None = None
    origin_asset_id: str | None = None
    discovery_page_url: str | None = None
    caption: str | None = None
    alt_text: str | None = None
    photographer: str | None = None
    agency: str | None = None
    copyright_holder: str | None = None
    credit_line: str | None = None
    license_type: str | None = None
    license_url: str | None = None
    rights_evidence_url: str | None = None
    season: int | None = None
    race_id: UUID | None = None
    session_id: UUID | None = None
    lap_number: int | None = None
    captured_at: datetime | None = None
    published_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def infer_content_role(text_value: str | None) -> str:
    value = " ".join((text_value or "").casefold().split())
    if not value:
        return "generic"
    rules = (
        ("podium", ("podium", "trophy", "champagne")),
        ("winner", ("winner", "wins the", "victory", "parc ferme")),
        ("race_start", ("at the start", "race start", "turn one", "first corner")),
        ("incident", ("crash", "collision", "contact", "spins", "spin")),
        ("pit_stop", ("pit stop", "pitstop", "pit lane")),
        ("overtake", ("overtake", "passes", "battle for", "fight for")),
        ("technical_detail", ("front wing", "rear wing", "floor", "technical detail")),
        ("celebration", ("celebrates", "celebration")),
        ("garage", ("garage", "mechanics")),
        ("driver_action", ("driving", "on track")),
    )
    for role, tokens in rules:
        if any(token in value for token in tokens):
            return role
    return "generic"


async def upsert_media_asset(
    session: AsyncSession,
    asset: MediaAssetInput,
) -> UUID:
    policy = policy_for_provider(asset.discovered_via)
    result = await session.execute(
        text(
            """
            INSERT INTO media_assets (
                asset_type,
                content_role,
                source_role,
                source_provider,
                source_asset_id,
                origin_provider,
                origin_asset_id,
                discovered_via,
                discovery_page_url,
                original_url,
                caption,
                alt_text,
                photographer,
                agency,
                copyright_holder,
                credit_line,
                license_type,
                license_url,
                usage_scope,
                rights_status,
                storage_policy,
                rights_evidence_url,
                season,
                race_id,
                session_id,
                lap_number,
                captured_at,
                published_at,
                metadata
            ) VALUES (
                'photo',
                :content_role,
                :source_role,
                :source_provider,
                :source_asset_id,
                :origin_provider,
                :origin_asset_id,
                :discovered_via,
                :discovery_page_url,
                :original_url,
                :caption,
                :alt_text,
                :photographer,
                :agency,
                :copyright_holder,
                :credit_line,
                :license_type,
                :license_url,
                :usage_scope,
                :rights_status,
                :storage_policy,
                :rights_evidence_url,
                :season,
                :race_id,
                :session_id,
                :lap_number,
                :captured_at,
                :published_at,
                CAST(:metadata AS jsonb)
            )
            ON CONFLICT (source_provider, original_url) DO UPDATE SET
                content_role = EXCLUDED.content_role,
                source_asset_id = COALESCE(
                    EXCLUDED.source_asset_id,
                    media_assets.source_asset_id
                ),
                origin_provider = COALESCE(
                    EXCLUDED.origin_provider,
                    media_assets.origin_provider
                ),
                origin_asset_id = COALESCE(
                    EXCLUDED.origin_asset_id,
                    media_assets.origin_asset_id
                ),
                discovery_page_url = COALESCE(
                    EXCLUDED.discovery_page_url,
                    media_assets.discovery_page_url
                ),
                caption = COALESCE(EXCLUDED.caption, media_assets.caption),
                alt_text = COALESCE(EXCLUDED.alt_text, media_assets.alt_text),
                photographer = COALESCE(
                    EXCLUDED.photographer,
                    media_assets.photographer
                ),
                agency = COALESCE(EXCLUDED.agency, media_assets.agency),
                credit_line = COALESCE(
                    EXCLUDED.credit_line,
                    media_assets.credit_line
                ),
                rights_evidence_url = COALESCE(
                    EXCLUDED.rights_evidence_url,
                    media_assets.rights_evidence_url
                ),
                season = COALESCE(EXCLUDED.season, media_assets.season),
                race_id = COALESCE(EXCLUDED.race_id, media_assets.race_id),
                session_id = COALESCE(
                    EXCLUDED.session_id,
                    media_assets.session_id
                ),
                lap_number = COALESCE(
                    EXCLUDED.lap_number,
                    media_assets.lap_number
                ),
                captured_at = COALESCE(
                    EXCLUDED.captured_at,
                    media_assets.captured_at
                ),
                published_at = COALESCE(
                    EXCLUDED.published_at,
                    media_assets.published_at
                ),
                metadata = media_assets.metadata || EXCLUDED.metadata,
                updated_at = now()
            RETURNING id
            """
        ),
        {
            "content_role": asset.content_role,
            "source_role": policy.source_role,
            "source_provider": asset.source_provider,
            "source_asset_id": asset.source_asset_id,
            "origin_provider": asset.origin_provider,
            "origin_asset_id": asset.origin_asset_id,
            "discovered_via": asset.discovered_via,
            "discovery_page_url": asset.discovery_page_url,
            "original_url": asset.original_url,
            "caption": asset.caption,
            "alt_text": asset.alt_text,
            "photographer": asset.photographer,
            "agency": asset.agency,
            "copyright_holder": asset.copyright_holder,
            "credit_line": asset.credit_line,
            "license_type": asset.license_type,
            "license_url": asset.license_url,
            "usage_scope": policy.usage_scope,
            "rights_status": policy.rights_status,
            "storage_policy": policy.storage_policy,
            "rights_evidence_url": (
                asset.rights_evidence_url or policy.rights_evidence_url
            ),
            "season": asset.season,
            "race_id": asset.race_id,
            "session_id": asset.session_id,
            "lap_number": asset.lap_number,
            "captured_at": asset.captured_at,
            "published_at": asset.published_at,
            "metadata": json.dumps(asset.metadata),
        },
    )
    return result.scalar_one()


async def link_source_item_media(
    session: AsyncSession,
    *,
    source_item_id: UUID,
    media_asset_id: UUID,
    relation_type: str = "article_hero",
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO source_item_media_assets (
                source_item_id,
                media_asset_id,
                relation_type
            ) VALUES (
                :source_item_id,
                :media_asset_id,
                :relation_type
            )
            ON CONFLICT (source_item_id, media_asset_id) DO UPDATE SET
                relation_type = EXCLUDED.relation_type
            """
        ),
        {
            "source_item_id": source_item_id,
            "media_asset_id": media_asset_id,
            "relation_type": relation_type,
        },
    )


async def link_story_media_candidate(
    session: AsyncSession,
    *,
    story_id: UUID,
    media_asset_id: UUID,
    story_role: str,
    match_reason: str,
    confidence: int,
    metadata: dict[str, Any] | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO story_media_candidates (
                story_id,
                media_asset_id,
                story_role,
                match_reason,
                confidence,
                metadata
            ) VALUES (
                :story_id,
                :media_asset_id,
                :story_role,
                :match_reason,
                :confidence,
                CAST(:metadata AS jsonb)
            )
            ON CONFLICT (story_id, media_asset_id, story_role) DO UPDATE SET
                match_reason = EXCLUDED.match_reason,
                confidence = GREATEST(
                    story_media_candidates.confidence,
                    EXCLUDED.confidence
                ),
                metadata = story_media_candidates.metadata || EXCLUDED.metadata,
                updated_at = now()
            WHERE story_media_candidates.manual_override = false
            """
        ),
        {
            "story_id": story_id,
            "media_asset_id": media_asset_id,
            "story_role": story_role,
            "match_reason": match_reason,
            "confidence": max(0, min(confidence, 100)),
            "metadata": json.dumps(metadata or {}),
        },
    )


async def copy_source_entities_to_media(
    session: AsyncSession,
    *,
    source_item_id: UUID,
    media_asset_id: UUID,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO media_asset_entities (
                media_asset_id,
                entity_id,
                relation_type,
                confidence,
                match_method
            )
            SELECT
                :media_asset_id,
                entity_id,
                'depicted',
                confidence,
                'source_item_entity_copy_v1'
            FROM source_item_entities
            WHERE source_item_id = :source_item_id
              AND match_method <> 'source_context'
            ON CONFLICT (media_asset_id, entity_id) DO UPDATE SET
                confidence = GREATEST(
                    media_asset_entities.confidence,
                    EXCLUDED.confidence
                ),
                match_method = EXCLUDED.match_method
            """
        ),
        {
            "source_item_id": source_item_id,
            "media_asset_id": media_asset_id,
        },
    )


async def reconcile_media_entities(
    session: AsyncSession,
    *,
    media_asset_id: UUID,
    classifications: tuple[SourceItemEntityClassification, ...],
) -> None:
    for item in classifications:
        await session.execute(
            text(
                """
                INSERT INTO media_asset_entities (
                    media_asset_id,
                    entity_id,
                    relation_type,
                    confidence,
                    match_method
                ) VALUES (
                    :media_asset_id,
                    :entity_id,
                    'depicted',
                    :confidence,
                    :match_method
                )
                ON CONFLICT (media_asset_id, entity_id) DO UPDATE SET
                    confidence = GREATEST(
                        media_asset_entities.confidence,
                        EXCLUDED.confidence
                    ),
                    match_method = EXCLUDED.match_method
                """
            ),
            {
                "media_asset_id": media_asset_id,
                "entity_id": item.entity_id,
                "confidence": item.confidence,
                "match_method": "caption_entity_match_v1",
            },
        )


async def refresh_story_media_from_sources(
    session: AsyncSession,
    story_id: UUID,
) -> int:
    result = await session.execute(
        text(
            """
            SELECT
                si.id AS source_item_id,
                si.provider,
                si.source_url,
                si.title,
                si.published_at,
                si.raw_metadata->>'image_url' AS image_url,
                si.raw_metadata->>'image_source' AS image_source,
                ssi.relation_type
            FROM story_source_items ssi
            JOIN source_items si ON si.id = ssi.source_item_id
            WHERE ssi.story_id = :story_id
              AND NULLIF(si.raw_metadata->>'image_url', '') IS NOT NULL
            ORDER BY
                CASE WHEN ssi.relation_type = 'primary' THEN 0 ELSE 1 END,
                COALESCE(si.published_at, si.fetched_at) DESC
            """
        ),
        {"story_id": story_id},
    )

    linked = 0
    for row in result.mappings().all():
        image_url = str(row["image_url"])
        asset_id = await upsert_media_asset(
            session,
            MediaAssetInput(
                source_provider=str(row["provider"]),
                discovered_via=str(row["provider"]),
                original_url=image_url,
                content_role="article_hero",
                discovery_page_url=row["source_url"],
                caption=row["title"],
                published_at=row["published_at"],
                season=(
                    row["published_at"].year
                    if row["published_at"] is not None
                    else None
                ),
                metadata={
                    "image_source": row["image_source"],
                    "source_item_id": str(row["source_item_id"]),
                },
            ),
        )
        await link_source_item_media(
            session,
            source_item_id=row["source_item_id"],
            media_asset_id=asset_id,
        )
        await copy_source_entities_to_media(
            session,
            source_item_id=row["source_item_id"],
            media_asset_id=asset_id,
        )
        await link_story_media_candidate(
            session,
            story_id=story_id,
            media_asset_id=asset_id,
            story_role="hero",
            match_reason="source_article",
            confidence=90 if row["relation_type"] == "primary" else 80,
            metadata={"source_item_id": str(row["source_item_id"])},
        )
        linked += 1
    return linked


def _normalized_tokens(value: str | None) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", (value or "").casefold())
        if len(token) >= 3
    }


def _role_matches_title(role: str, title: str) -> bool:
    keywords = ROLE_KEYWORDS.get(role, ())
    normalized = " ".join(title.casefold().split())
    return any(keyword in normalized for keyword in keywords)


def _story_match_is_strong_enough(
    *,
    role: str,
    shared_entities: int,
    shared_races: int,
) -> bool:
    if shared_entities >= 2:
        return True
    return shared_races > 0 and role in RACE_ONLY_STORY_ROLES


async def match_media_asset_to_stories(
    session: AsyncSession,
    media_asset_id: UUID,
) -> int:
    await session.execute(
        text(
            """
            DELETE FROM story_media_candidates
            WHERE media_asset_id = :media_asset_id
              AND manual_override = false
              AND match_reason IN (
                  'exact_event',
                  'race_match',
                  'entity_match',
                  'fallback'
              )
            """
        ),
        {"media_asset_id": media_asset_id},
    )

    race_only_roles_sql = ", ".join(
        f"'{role}'" for role in sorted(RACE_ONLY_STORY_ROLES)
    )
    result = await session.execute(
        text(
            f"""
            SELECT
                s.id AS story_id,
                s.title,
                ma.content_role,
                COUNT(*)::int AS shared_entities,
                COUNT(*) FILTER (WHERE e.entity_type = 'race')::int
                    AS shared_races,
                COUNT(*) FILTER (WHERE e.entity_type = 'person')::int
                    AS shared_people,
                COUNT(*) FILTER (WHERE e.entity_type = 'team')::int
                    AS shared_teams
            FROM media_assets ma
            JOIN media_asset_entities mae
              ON mae.media_asset_id = ma.id
            JOIN story_entities se
              ON se.entity_id = mae.entity_id
            JOIN entities e ON e.id = mae.entity_id
            JOIN stories s ON s.id = se.story_id
            WHERE ma.id = :media_asset_id
              AND s.merged_into_story_id IS NULL
            GROUP BY s.id, s.title, ma.content_role
            HAVING
                COUNT(*) >= 2
                OR (
                    COUNT(*) FILTER (WHERE e.entity_type = 'race') > 0
                    AND ma.content_role IN ({race_only_roles_sql})
                )
            ORDER BY
                COUNT(*) FILTER (WHERE e.entity_type = 'race') DESC,
                COUNT(*) DESC,
                s.updated_at DESC
            LIMIT 30
            """
        ),
        {"media_asset_id": media_asset_id},
    )

    count = 0
    for row in result.mappings().all():
        shared = int(row["shared_entities"])
        race_match = int(row["shared_races"]) > 0
        person_match = int(row["shared_people"]) > 0
        team_match = int(row["shared_teams"]) > 0
        role = str(row["content_role"])
        if not _story_match_is_strong_enough(
            role=role,
            shared_entities=shared,
            shared_races=int(row["shared_races"]),
        ):
            continue

        score = 45 + min(shared, 3) * 10
        if race_match:
            score += 20
        if person_match:
            score += 10
        if team_match:
            score += 5
        if _role_matches_title(role, str(row["title"])):
            score += 10

        if race_match and person_match and role in EVENT_ROLES:
            reason = "exact_event"
        elif race_match:
            reason = "race_match"
        elif person_match or team_match:
            reason = "entity_match"
        else:
            reason = "fallback"

        story_role = "hero" if role in RACE_ONLY_STORY_ROLES else "supporting"
        await link_story_media_candidate(
            session,
            story_id=row["story_id"],
            media_asset_id=media_asset_id,
            story_role=story_role,
            match_reason=reason,
            confidence=min(score, 95),
            metadata={
                "shared_entities": shared,
                "shared_race": race_match,
                "shared_person": person_match,
                "shared_team": team_match,
            },
        )
        count += 1
    return count
