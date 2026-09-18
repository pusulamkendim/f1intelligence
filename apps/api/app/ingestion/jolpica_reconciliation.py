from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.jolpica import (
    JolpicaConstructorIdentity,
    JolpicaDriverIdentity,
    JolpicaDriverStanding,
)

PROVIDER = "jolpica"


class AmbiguousEntityMatch(ValueError):
    pass


@dataclass(frozen=True)
class CanonicalCandidate:
    entity_id: UUID
    slug: str
    display_name: str
    birth_date: Any | None = None


@dataclass(frozen=True)
class ProviderMapping:
    entity_id: UUID
    valid_from_season: int | None
    valid_to_season: int | None


@dataclass(frozen=True)
class ReconciliationReport:
    drivers: int
    constructors: int
    auto_created: int
    validity_extensions: int
    exact_identity_matches: int
    roster_links: int
    review_required: tuple[str, ...]

    @property
    def blocked(self) -> bool:
        return bool(self.review_required)


def _normalize_identity(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", "", ascii_value.casefold())


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")
    return slug or "historical-entity"


def _mapping_method(mapping: ProviderMapping, season: int) -> str:
    lower_ok = (
        mapping.valid_from_season is None
        or mapping.valid_from_season <= season
    )
    upper_ok = (
        mapping.valid_to_season is None
        or mapping.valid_to_season >= season
    )
    return (
        "exact_provider_id"
        if lower_ok and upper_ok
        else "provider_validity_extension"
    )


def _driver_identity_match(
    identity: JolpicaDriverIdentity,
    candidates: list[CanonicalCandidate],
) -> CanonicalCandidate | None:
    full_name = f"{identity.given_name} {identity.family_name}"
    normalized = _normalize_identity(full_name)
    matches = [
        candidate
        for candidate in candidates
        if _normalize_identity(candidate.display_name) == normalized
    ]
    if not matches:
        return None
    if len(matches) > 1:
        raise AmbiguousEntityMatch(
            f"ambiguous driver identity {identity.driver_id}: "
            + ", ".join(sorted(candidate.slug for candidate in matches))
        )

    candidate = matches[0]
    if (
        identity.date_of_birth is not None
        and candidate.birth_date is not None
        and identity.date_of_birth != candidate.birth_date
    ):
        raise AmbiguousEntityMatch(
            f"driver identity conflict {identity.driver_id}: "
            f"{candidate.slug} has birth date {candidate.birth_date}"
        )
    return candidate


def _constructor_identity_match(
    identity: JolpicaConstructorIdentity,
    candidates: list[CanonicalCandidate],
) -> CanonicalCandidate | None:
    normalized = _normalize_identity(identity.name)
    matches = [
        candidate
        for candidate in candidates
        if _normalize_identity(candidate.display_name) == normalized
    ]
    if not matches:
        return None
    if len(matches) > 1:
        raise AmbiguousEntityMatch(
            f"ambiguous constructor identity {identity.constructor_id}: "
            + ", ".join(sorted(candidate.slug for candidate in matches))
        )
    return matches[0]


def _season_roster_pairs(
    standings: list[JolpicaDriverStanding],
) -> set[tuple[str, str]]:
    return {
        (row.driver_id, constructor_id)
        for row in standings
        for constructor_id in row.constructor_ids
    }


async def _provider_mapping(
    session: AsyncSession,
    *,
    entity_type: str,
    provider_id: str,
) -> ProviderMapping | None:
    result = await session.execute(
        text(
            """
            SELECT entity_id, valid_from_season, valid_to_season
            FROM entity_provider_ids
            WHERE provider = :provider
              AND provider_entity_type = :entity_type
              AND provider_id = :provider_id
            LIMIT 1
            """
        ),
        {
            "provider": PROVIDER,
            "entity_type": entity_type,
            "provider_id": provider_id,
        },
    )
    row = result.mappings().first()
    if row is None:
        return None
    return ProviderMapping(
        entity_id=row["entity_id"],
        valid_from_season=row["valid_from_season"],
        valid_to_season=row["valid_to_season"],
    )


async def _canonical_candidates(
    session: AsyncSession,
    *,
    entity_type: str,
) -> list[CanonicalCandidate]:
    if entity_type == "driver":
        result = await session.execute(
            text(
                """
                SELECT
                    e.id AS entity_id,
                    e.slug,
                    e.display_name,
                    p.birth_date
                FROM entities e
                JOIN persons p ON p.entity_id = e.id
                WHERE e.entity_type = 'person'
                ORDER BY e.slug
                """
            )
        )
    else:
        result = await session.execute(
            text(
                """
                SELECT
                    e.id AS entity_id,
                    e.slug,
                    e.display_name,
                    NULL::date AS birth_date
                FROM entities e
                WHERE e.entity_type = 'team'
                ORDER BY e.slug
                """
            )
        )
    return [CanonicalCandidate(**dict(row)) for row in result.mappings().all()]


async def _audit(
    session: AsyncSession,
    *,
    entity_type: str,
    provider_id: str,
    season: int,
    resolved_entity_id: UUID | None,
    method: str,
    confidence: int,
    review_required: bool,
    source_url: str | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO entity_reconciliation_audit (
                provider,
                provider_entity_type,
                provider_id,
                season,
                resolved_entity_id,
                resolution_method,
                confidence,
                review_required,
                source_url,
                metadata
            ) VALUES (
                :provider,
                :entity_type,
                :provider_id,
                :season,
                :resolved_entity_id,
                :method,
                :confidence,
                :review_required,
                :source_url,
                CAST(:metadata AS jsonb)
            )
            ON CONFLICT (
                provider,
                provider_entity_type,
                provider_id,
                season
            ) DO UPDATE SET
                resolved_entity_id = EXCLUDED.resolved_entity_id,
                resolution_method = EXCLUDED.resolution_method,
                confidence = EXCLUDED.confidence,
                review_required = EXCLUDED.review_required,
                source_url = EXCLUDED.source_url,
                metadata = EXCLUDED.metadata,
                updated_at = now()
            """
        ),
        {
            "provider": PROVIDER,
            "entity_type": entity_type,
            "provider_id": provider_id,
            "season": season,
            "resolved_entity_id": resolved_entity_id,
            "method": method,
            "confidence": confidence,
            "review_required": review_required,
            "source_url": source_url,
            "metadata": json.dumps(metadata or {}),
        },
    )


async def _extend_validity(
    session: AsyncSession,
    *,
    entity_id: UUID,
    entity_type: str,
    provider_id: str,
    season: int,
) -> None:
    await session.execute(
        text(
            """
            UPDATE entity_provider_ids
            SET
                valid_from_season = CASE
                    WHEN valid_from_season IS NULL THEN NULL
                    ELSE LEAST(valid_from_season, :season)
                END,
                valid_to_season = CASE
                    WHEN valid_to_season IS NULL THEN NULL
                    ELSE GREATEST(valid_to_season, :season)
                END,
                updated_at = now()
            WHERE provider = :provider
              AND provider_entity_type = :entity_type
              AND provider_id = :provider_id
            """
        ),
        {
            "provider": PROVIDER,
            "entity_type": entity_type,
            "provider_id": provider_id,
            "season": season,
        },
    )
    await session.execute(
        text(
            """
            UPDATE entities
            SET
                active_from_season = CASE
                    WHEN active_from_season IS NULL THEN :season
                    ELSE LEAST(active_from_season, :season)
                END,
                active_to_season = CASE
                    WHEN active_to_season IS NULL THEN NULL
                    ELSE GREATEST(active_to_season, :season)
                END,
                updated_at = now()
            WHERE id = :entity_id
            """
        ),
        {"entity_id": entity_id, "season": season},
    )


async def _insert_provider_mapping(
    session: AsyncSession,
    *,
    entity_id: UUID,
    entity_type: str,
    provider_id: str,
    season: int,
    source_url: str | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO entity_provider_ids (
                entity_id,
                provider,
                provider_entity_type,
                provider_id,
                valid_from_season,
                valid_to_season,
                source_url
            ) VALUES (
                :entity_id,
                :provider,
                :entity_type,
                :provider_id,
                :season,
                :season,
                :source_url
            )
            ON CONFLICT (
                provider,
                provider_entity_type,
                provider_id
            ) DO UPDATE SET
                entity_id = EXCLUDED.entity_id,
                valid_from_season = CASE
                    WHEN entity_provider_ids.valid_from_season IS NULL
                        THEN NULL
                    ELSE LEAST(
                        entity_provider_ids.valid_from_season,
                        EXCLUDED.valid_from_season
                    )
                END,
                valid_to_season = CASE
                    WHEN entity_provider_ids.valid_to_season IS NULL
                        THEN NULL
                    ELSE GREATEST(
                        entity_provider_ids.valid_to_season,
                        EXCLUDED.valid_to_season
                    )
                END,
                source_url = COALESCE(
                    EXCLUDED.source_url,
                    entity_provider_ids.source_url
                ),
                updated_at = now()
            """
        ),
        {
            "entity_id": entity_id,
            "provider": PROVIDER,
            "entity_type": entity_type,
            "provider_id": provider_id,
            "season": season,
            "source_url": source_url,
        },
    )


async def _unique_slug(
    session: AsyncSession,
    *,
    entity_type: str,
    preferred: str,
    provider_id: str,
) -> str:
    for candidate in (
        preferred,
        f"{preferred}-{_slugify(provider_id)}",
    ):
        result = await session.execute(
            text(
                """
                SELECT 1
                FROM entities
                WHERE entity_type = :entity_type
                  AND slug = :slug
                LIMIT 1
                """
            ),
            {"entity_type": entity_type, "slug": candidate},
        )
        if result.scalar_one_or_none() is None:
            return candidate
    raise ValueError(
        f"unable to allocate canonical slug for {entity_type} {provider_id}"
    )


async def _create_driver(
    session: AsyncSession,
    identity: JolpicaDriverIdentity,
    season: int,
) -> tuple[UUID, str]:
    display_name = f"{identity.given_name} {identity.family_name}"
    slug = await _unique_slug(
        session,
        entity_type="person",
        preferred=_slugify(display_name),
        provider_id=identity.driver_id,
    )
    entity_id = (
        await session.execute(
            text(
                """
                INSERT INTO entities (
                    entity_type,
                    slug,
                    display_name,
                    active_from_season,
                    active_to_season,
                    metadata
                ) VALUES (
                    'person',
                    :slug,
                    :display_name,
                    :season,
                    :season,
                    CAST(:metadata AS jsonb)
                )
                RETURNING id
                """
            ),
            {
                "slug": slug,
                "display_name": display_name,
                "season": season,
                "metadata": json.dumps(
                    {
                        "kind": "driver",
                        "participation": "historical_auto",
                        "source_provider": PROVIDER,
                        "nationality": identity.nationality,
                    }
                ),
            },
        )
    ).scalar_one()
    await session.execute(
        text(
            """
            INSERT INTO persons (
                entity_id,
                slug,
                display_name,
                birth_date
            ) VALUES (
                :entity_id,
                :slug,
                :display_name,
                :birth_date
            )
            """
        ),
        {
            "entity_id": entity_id,
            "slug": slug,
            "display_name": display_name,
            "birth_date": identity.date_of_birth,
        },
    )
    aliases = [
        (display_name, "canonical", 100),
        (identity.family_name, "surname", 92),
    ]
    if identity.code:
        aliases.append((identity.code, "driver_code", 86))
    for alias, alias_type, confidence in aliases:
        await session.execute(
            text(
                """
                INSERT INTO entity_aliases (
                    entity_id,
                    alias,
                    alias_type,
                    confidence,
                    valid_from_season,
                    valid_to_season
                ) VALUES (
                    :entity_id,
                    :alias,
                    :alias_type,
                    :confidence,
                    :season,
                    :season
                )
                ON CONFLICT (entity_id, alias) DO UPDATE SET
                    enabled = true,
                    confidence = GREATEST(
                        entity_aliases.confidence,
                        EXCLUDED.confidence
                    ),
                    valid_from_season = LEAST(
                        COALESCE(
                            entity_aliases.valid_from_season,
                            EXCLUDED.valid_from_season
                        ),
                        EXCLUDED.valid_from_season
                    ),
                    valid_to_season = GREATEST(
                        COALESCE(
                            entity_aliases.valid_to_season,
                            EXCLUDED.valid_to_season
                        ),
                        EXCLUDED.valid_to_season
                    ),
                    updated_at = now()
                """
            ),
            {
                "entity_id": entity_id,
                "alias": alias,
                "alias_type": alias_type,
                "confidence": confidence,
                "season": season,
            },
        )
    return entity_id, slug


async def _create_constructor(
    session: AsyncSession,
    identity: JolpicaConstructorIdentity,
    season: int,
) -> tuple[UUID, str]:
    slug = await _unique_slug(
        session,
        entity_type="team",
        preferred=_slugify(identity.name),
        provider_id=identity.constructor_id,
    )
    entity_id = (
        await session.execute(
            text(
                """
                INSERT INTO entities (
                    entity_type,
                    slug,
                    display_name,
                    active_from_season,
                    active_to_season,
                    metadata
                ) VALUES (
                    'team',
                    :slug,
                    :display_name,
                    :season,
                    :season,
                    CAST(:metadata AS jsonb)
                )
                RETURNING id
                """
            ),
            {
                "slug": slug,
                "display_name": identity.name,
                "season": season,
                "metadata": json.dumps(
                    {
                        "kind": "constructor",
                        "participation": "historical_auto",
                        "source_provider": PROVIDER,
                        "nationality": identity.nationality,
                    }
                ),
            },
        )
    ).scalar_one()
    await session.execute(
        text(
            """
            INSERT INTO teams (
                slug,
                name,
                active_season,
                entity_id
            ) VALUES (
                :slug,
                :name,
                :season,
                :entity_id
            )
            ON CONFLICT (slug) DO UPDATE SET
                name = EXCLUDED.name,
                entity_id = EXCLUDED.entity_id,
                updated_at = now()
            """
        ),
        {
            "slug": slug,
            "name": identity.name,
            "season": season,
            "entity_id": entity_id,
        },
    )
    await session.execute(
        text(
            """
            INSERT INTO entity_aliases (
                entity_id,
                alias,
                alias_type,
                confidence,
                valid_from_season,
                valid_to_season
            ) VALUES (
                :entity_id,
                :alias,
                'canonical',
                100,
                :season,
                :season
            )
            ON CONFLICT (entity_id, alias) DO UPDATE SET
                enabled = true,
                confidence = 100,
                updated_at = now()
            """
        ),
        {
            "entity_id": entity_id,
            "alias": identity.name,
            "season": season,
        },
    )
    return entity_id, slug


async def _enrich_driver(
    session: AsyncSession,
    *,
    entity_id: UUID,
    identity: JolpicaDriverIdentity,
    season: int,
) -> None:
    await session.execute(
        text(
            """
            UPDATE persons
            SET
                birth_date = COALESCE(
                    birth_date,
                    :birth_date
                ),
                updated_at = now()
            WHERE entity_id = :entity_id
            """
        ),
        {
            "entity_id": entity_id,
            "birth_date": identity.date_of_birth,
        },
    )
    await session.execute(
        text(
            """
            UPDATE entities
            SET
                active_from_season = CASE
                    WHEN active_from_season IS NULL THEN :season
                    ELSE LEAST(active_from_season, :season)
                END,
                active_to_season = CASE
                    WHEN active_to_season IS NULL THEN NULL
                    ELSE GREATEST(active_to_season, :season)
                END,
                metadata = metadata || CAST(:metadata AS jsonb),
                updated_at = now()
            WHERE id = :entity_id
            """
        ),
        {
            "entity_id": entity_id,
            "season": season,
            "metadata": json.dumps(
                {
                    "kind": "driver",
                    "nationality": identity.nationality,
                }
            ),
        },
    )


async def upsert_driver_team_participation(
    session: AsyncSession,
    *,
    driver_entity_id: UUID,
    team_entity_id: UUID,
    season: int,
    source_url: str | None,
) -> bool:
    result = await session.execute(
        text(
            """
            INSERT INTO team_person_roles (
                team_id,
                person_id,
                role,
                season,
                source_url
            )
            SELECT
                t.id,
                p.id,
                'driver',
                :season,
                :source_url
            FROM teams t
            JOIN persons p ON p.entity_id = :driver_entity_id
            WHERE t.entity_id = :team_entity_id
            ON CONFLICT (team_id, person_id, role, season) DO UPDATE SET
                source_url = COALESCE(
                    EXCLUDED.source_url,
                    team_person_roles.source_url
                ),
                updated_at = now()
            RETURNING id
            """
        ),
        {
            "driver_entity_id": driver_entity_id,
            "team_entity_id": team_entity_id,
            "season": season,
            "source_url": source_url,
        },
    )
    return result.scalar_one_or_none() is not None


async def reconcile_jolpica_season_entities(
    session: AsyncSession,
    *,
    season: int,
    drivers: list[JolpicaDriverIdentity],
    constructors: list[JolpicaConstructorIdentity],
    standings: list[JolpicaDriverStanding],
) -> ReconciliationReport:
    driver_candidates = await _canonical_candidates(
        session,
        entity_type="driver",
    )
    constructor_candidates = await _canonical_candidates(
        session,
        entity_type="constructor",
    )

    driver_map: dict[str, UUID] = {}
    constructor_map: dict[str, UUID] = {}
    review_required: list[str] = []
    auto_created = 0
    validity_extensions = 0
    exact_identity_matches = 0

    for identity in constructors:
        mapping = await _provider_mapping(
            session,
            entity_type="constructor",
            provider_id=identity.constructor_id,
        )
        if mapping is not None:
            method = _mapping_method(mapping, season)
            if method == "provider_validity_extension":
                await _extend_validity(
                    session,
                    entity_id=mapping.entity_id,
                    entity_type="constructor",
                    provider_id=identity.constructor_id,
                    season=season,
                )
                validity_extensions += 1
            constructor_map[identity.constructor_id] = mapping.entity_id
            await _audit(
                session,
                entity_type="constructor",
                provider_id=identity.constructor_id,
                season=season,
                resolved_entity_id=mapping.entity_id,
                method=method,
                confidence=100,
                review_required=False,
                source_url=identity.source_url,
            )
            continue

        try:
            candidate = _constructor_identity_match(
                identity,
                constructor_candidates,
            )
        except AmbiguousEntityMatch as exc:
            review_required.append(
                f"constructor:{identity.constructor_id}"
            )
            await _audit(
                session,
                entity_type="constructor",
                provider_id=identity.constructor_id,
                season=season,
                resolved_entity_id=None,
                method="ambiguous",
                confidence=0,
                review_required=True,
                source_url=identity.source_url,
                metadata={"reason": str(exc)},
            )
            continue

        if candidate is None:
            entity_id, slug = await _create_constructor(
                session,
                identity,
                season,
            )
            auto_created += 1
            constructor_candidates.append(
                CanonicalCandidate(
                    entity_id=entity_id,
                    slug=slug,
                    display_name=identity.name,
                )
            )
            method = "auto_created"
            confidence = 95
        else:
            entity_id = candidate.entity_id
            method = "exact_identity"
            confidence = 98
            exact_identity_matches += 1
            await session.execute(
                text(
                    """
                    UPDATE entities
                    SET
                        active_from_season = CASE
                            WHEN active_from_season IS NULL THEN :season
                            ELSE LEAST(active_from_season, :season)
                        END,
                        active_to_season = CASE
                            WHEN active_to_season IS NULL THEN NULL
                            ELSE GREATEST(active_to_season, :season)
                        END,
                        updated_at = now()
                    WHERE id = :entity_id
                    """
                ),
                {"entity_id": entity_id, "season": season},
            )

        await _insert_provider_mapping(
            session,
            entity_id=entity_id,
            entity_type="constructor",
            provider_id=identity.constructor_id,
            season=season,
            source_url=identity.source_url,
        )
        constructor_map[identity.constructor_id] = entity_id
        await _audit(
            session,
            entity_type="constructor",
            provider_id=identity.constructor_id,
            season=season,
            resolved_entity_id=entity_id,
            method=method,
            confidence=confidence,
            review_required=False,
            source_url=identity.source_url,
        )

    for identity in drivers:
        mapping = await _provider_mapping(
            session,
            entity_type="driver",
            provider_id=identity.driver_id,
        )
        if mapping is not None:
            method = _mapping_method(mapping, season)
            if method == "provider_validity_extension":
                await _extend_validity(
                    session,
                    entity_id=mapping.entity_id,
                    entity_type="driver",
                    provider_id=identity.driver_id,
                    season=season,
                )
                validity_extensions += 1
            await _enrich_driver(
                session,
                entity_id=mapping.entity_id,
                identity=identity,
                season=season,
            )
            driver_map[identity.driver_id] = mapping.entity_id
            await _audit(
                session,
                entity_type="driver",
                provider_id=identity.driver_id,
                season=season,
                resolved_entity_id=mapping.entity_id,
                method=method,
                confidence=100,
                review_required=False,
                source_url=identity.source_url,
            )
            continue

        try:
            candidate = _driver_identity_match(
                identity,
                driver_candidates,
            )
        except AmbiguousEntityMatch as exc:
            review_required.append(f"driver:{identity.driver_id}")
            await _audit(
                session,
                entity_type="driver",
                provider_id=identity.driver_id,
                season=season,
                resolved_entity_id=None,
                method="ambiguous",
                confidence=0,
                review_required=True,
                source_url=identity.source_url,
                metadata={"reason": str(exc)},
            )
            continue

        if candidate is None:
            entity_id, slug = await _create_driver(
                session,
                identity,
                season,
            )
            auto_created += 1
            driver_candidates.append(
                CanonicalCandidate(
                    entity_id=entity_id,
                    slug=slug,
                    display_name=(
                        f"{identity.given_name} {identity.family_name}"
                    ),
                    birth_date=identity.date_of_birth,
                )
            )
            method = "auto_created"
            confidence = 98
        else:
            entity_id = candidate.entity_id
            exact_identity_matches += 1
            method = "exact_identity"
            confidence = 99
            await _enrich_driver(
                session,
                entity_id=entity_id,
                identity=identity,
                season=season,
            )

        await _insert_provider_mapping(
            session,
            entity_id=entity_id,
            entity_type="driver",
            provider_id=identity.driver_id,
            season=season,
            source_url=identity.source_url,
        )
        driver_map[identity.driver_id] = entity_id
        await _audit(
            session,
            entity_type="driver",
            provider_id=identity.driver_id,
            season=season,
            resolved_entity_id=entity_id,
            method=method,
            confidence=confidence,
            review_required=False,
            source_url=identity.source_url,
        )

    roster_links = 0
    for driver_id, constructor_id in _season_roster_pairs(standings):
        driver_entity_id = driver_map.get(driver_id)
        team_entity_id = constructor_map.get(constructor_id)
        if driver_entity_id is None or team_entity_id is None:
            continue
        if await upsert_driver_team_participation(
            session,
            driver_entity_id=driver_entity_id,
            team_entity_id=team_entity_id,
            season=season,
            source_url=(
                f"https://api.jolpi.ca/ergast/f1/{season}/"
                "driverstandings.json"
            ),
        ):
            roster_links += 1

    return ReconciliationReport(
        drivers=len(driver_map),
        constructors=len(constructor_map),
        auto_created=auto_created,
        validity_extensions=validity_extensions,
        exact_identity_matches=exact_identity_matches,
        roster_links=roster_links,
        review_required=tuple(sorted(review_required)),
    )
