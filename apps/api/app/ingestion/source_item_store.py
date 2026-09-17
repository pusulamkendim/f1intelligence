from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.entity_matcher import EntityAlias
from app.ingestion.source_item_entities import (
    SourceItemEntityClassification,
    SourceItemText,
    classify_source_item_entities,
)


@dataclass(frozen=True)
class SourceItemRecord:
    provider: str
    external_id: str
    source_type: str
    source_class: str
    title: str
    source_url: str | None = None
    standfirst: str | None = None
    summary: str | None = None
    body_excerpt: str | None = None
    author: str | None = None
    language: str | None = None
    published_at: datetime | None = None
    content_hash: str | None = None
    rights_policy: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TeamContextPerson:
    entity_id: UUID
    slug: str
    display_name: str
    role: str
    season: int


async def load_entity_aliases(session: AsyncSession) -> list[EntityAlias]:
    result = await session.execute(
        text(
            """
            SELECT
                e.id AS entity_id,
                e.entity_type,
                e.slug,
                e.display_name,
                ea.alias,
                ea.alias_type,
                ea.confidence,
                ea.valid_from_season,
                ea.valid_to_season
            FROM entity_aliases ea
            JOIN entities e ON e.id = ea.entity_id
            WHERE ea.enabled = true
            ORDER BY e.entity_type, e.display_name, length(ea.alias) DESC
            """
        )
    )
    return [EntityAlias(**dict(row)) for row in result.mappings().all()]


def build_team_context_aliases(
    people: list[TeamContextPerson],
) -> list[EntityAlias]:
    """Build team-scoped first-name aliases only when unambiguous inside that roster.

    These aliases are intentionally never stored globally. A first name such as Carlos,
    Lando, or Oscar is only usable while classifying content from the person's own
    first-party team source for the matching roster season.
    """
    first_names = [person.display_name.split()[0] for person in people if person.display_name.split()]
    counts = Counter(name.casefold() for name in first_names)
    aliases: list[EntityAlias] = []
    for person in people:
        parts = person.display_name.split()
        if not parts:
            continue
        first_name = parts[0]
        if len(first_name) < 3 or counts[first_name.casefold()] != 1:
            continue
        aliases.append(
            EntityAlias(
                entity_id=person.entity_id,
                entity_type="person",
                slug=person.slug,
                display_name=person.display_name,
                alias=first_name,
                alias_type="team_first_name",
                confidence=93,
                valid_from_season=person.season,
                valid_to_season=person.season,
            )
        )
    return aliases


async def load_team_context_aliases(
    session: AsyncSession,
    *,
    team_slug: str,
    season: int | None,
) -> list[EntityAlias]:
    result = await session.execute(
        text(
            """
            SELECT
                e.id AS entity_id,
                p.slug,
                p.display_name,
                tpr.role,
                tpr.season
            FROM teams t
            JOIN team_person_roles tpr ON tpr.team_id = t.id
            JOIN persons p ON p.id = tpr.person_id
            JOIN entities e ON e.id = p.entity_id
            WHERE t.slug = :team_slug
              AND tpr.season = COALESCE(
                    :season,
                    (SELECT max(latest.season)
                     FROM team_person_roles latest
                     WHERE latest.team_id = t.id)
              )
            ORDER BY p.display_name, tpr.role
            """
        ),
        {"team_slug": team_slug, "season": season},
    )
    people = [TeamContextPerson(**dict(row)) for row in result.mappings().all()]
    return build_team_context_aliases(people)


async def upsert_source_item(session: AsyncSession, item: SourceItemRecord) -> UUID:
    result = await session.execute(
        text(
            """
            INSERT INTO source_items (
                provider,
                external_id,
                source_type,
                source_class,
                source_url,
                title,
                standfirst,
                summary,
                body_excerpt,
                author,
                language,
                published_at,
                content_hash,
                rights_policy,
                raw_metadata
            ) VALUES (
                :provider,
                :external_id,
                :source_type,
                :source_class,
                :source_url,
                :title,
                :standfirst,
                :summary,
                :body_excerpt,
                :author,
                :language,
                :published_at,
                :content_hash,
                :rights_policy,
                CAST(:raw_metadata AS jsonb)
            )
            ON CONFLICT (provider, external_id) DO UPDATE SET
                source_type = EXCLUDED.source_type,
                source_class = EXCLUDED.source_class,
                source_url = EXCLUDED.source_url,
                title = EXCLUDED.title,
                standfirst = EXCLUDED.standfirst,
                summary = EXCLUDED.summary,
                body_excerpt = EXCLUDED.body_excerpt,
                author = EXCLUDED.author,
                language = EXCLUDED.language,
                published_at = EXCLUDED.published_at,
                fetched_at = now(),
                content_hash = EXCLUDED.content_hash,
                rights_policy = EXCLUDED.rights_policy,
                raw_metadata = EXCLUDED.raw_metadata,
                updated_at = now()
            RETURNING id
            """
        ),
        {
            "provider": item.provider,
            "external_id": item.external_id,
            "source_type": item.source_type,
            "source_class": item.source_class,
            "source_url": item.source_url,
            "title": item.title,
            "standfirst": item.standfirst,
            "summary": item.summary,
            "body_excerpt": item.body_excerpt,
            "author": item.author,
            "language": item.language,
            "published_at": item.published_at,
            "content_hash": item.content_hash,
            "rights_policy": item.rights_policy,
            "raw_metadata": json.dumps(item.raw_metadata),
        },
    )
    return result.scalar_one()


async def reconcile_source_item_entities(
    session: AsyncSession,
    source_item_id: UUID,
    classifications: tuple[SourceItemEntityClassification, ...],
) -> int:
    # Re-ingestion may change text or deterministic semantics. Remove every version
    # owned by our deterministic classifier; LLM/manual upgrades must survive refreshes.
    await session.execute(
        text(
            """
            DELETE FROM source_item_entities
            WHERE source_item_id = :source_item_id
              AND classification_method LIKE 'deterministic_v%'
            """
        ),
        {"source_item_id": source_item_id},
    )

    written = 0
    for classification in classifications:
        result = await session.execute(
            text(
                """
                INSERT INTO source_item_entities (
                    source_item_id,
                    entity_id,
                    relation_type,
                    confidence,
                    match_method,
                    matched_alias,
                    detected_in,
                    classification_method,
                    metadata
                ) VALUES (
                    :source_item_id,
                    :entity_id,
                    :relation_type,
                    :confidence,
                    :match_method,
                    :matched_alias,
                    :detected_in,
                    :classification_method,
                    '{}'::jsonb
                )
                ON CONFLICT (source_item_id, entity_id) DO NOTHING
                RETURNING entity_id
                """
            ),
            {
                "source_item_id": source_item_id,
                "entity_id": classification.entity_id,
                "relation_type": classification.relation_type,
                "confidence": classification.confidence,
                "match_method": classification.match_method,
                "matched_alias": classification.matched_alias,
                "detected_in": list(classification.detected_in),
                "classification_method": classification.classification_method,
            },
        )
        if result.scalar_one_or_none() is not None:
            written += 1
    return written


async def persist_source_item_with_entities(
    session: AsyncSession,
    item: SourceItemRecord,
    *,
    season: int | None = None,
    aliases: list[EntityAlias] | None = None,
) -> tuple[UUID, tuple[SourceItemEntityClassification, ...]]:
    source_item_id = await upsert_source_item(session, item)
    entity_aliases = aliases if aliases is not None else await load_entity_aliases(session)
    classifications = classify_source_item_entities(
        SourceItemText(
            title=item.title,
            standfirst=item.standfirst,
            summary=item.summary,
            body_excerpt=item.body_excerpt,
            season=season,
        ),
        entity_aliases,
    )
    await reconcile_source_item_entities(session, source_item_id, classifications)
    return source_item_id, classifications
