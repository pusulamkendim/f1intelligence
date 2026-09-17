from __future__ import annotations

import json
import re
import unicodedata
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.jolpica import JolpicaRace

PROVIDER = "jolpica"


def _race_provider_id(race: JolpicaRace) -> str:
    # Jolpica identifies calendar rows by season + current ordinal round.
    # This is useful provenance, but it is not a stable race identity when the
    # calendar is amended and an event is inserted or removed.
    return f"{race.season}:{race.round}"


def _slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def _canonical_race_slug(race: JolpicaRace) -> str:
    return f"{race.season}-{_slugify(race.name)}"


def _calendar_alias_candidates(race: JolpicaRace) -> list[str]:
    candidates = [race.name, race.circuit.name, race.circuit.locality]
    seen: set[str] = set()
    unique: list[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        normalized = candidate.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


async def _existing_entity_by_circuit(
    session: AsyncSession, race: JolpicaRace
) -> tuple[Any, str] | None:
    result = await session.execute(
        text(
            """
            SELECT e.id, e.slug
            FROM races r
            JOIN entities e ON e.id = r.entity_id
            WHERE r.season = :season
              AND r.circuit_provider_id = :circuit_provider_id
              AND e.entity_type = 'race'
            ORDER BY r.updated_at DESC
            LIMIT 2
            """
        ),
        {
            "season": race.season,
            "circuit_provider_id": race.circuit.provider_id,
        },
    )
    rows = list(result)
    if len(rows) > 1:
        raise ValueError(
            "ambiguous canonical race identity for circuit "
            f"{race.circuit.provider_id!r} in season {race.season}"
        )
    if not rows:
        return None
    return rows[0].id, rows[0].slug


async def _existing_entity_by_alias(
    session: AsyncSession, race: JolpicaRace
) -> tuple[Any, str] | None:
    candidates = _calendar_alias_candidates(race)
    display_name = f"{race.season} {race.name}".lower()
    result = await session.execute(
        text(
            """
            SELECT
                e.id,
                e.slug,
                MAX(
                    CASE
                        WHEN lower(e.display_name) = :display_name THEN 1000
                        WHEN ea.alias_type = 'race_name' THEN 500 + ea.confidence
                        WHEN ea.alias_type = 'canonical' THEN 400 + ea.confidence
                        WHEN ea.alias_type = 'venue' THEN 300 + ea.confidence
                        ELSE ea.confidence
                    END
                ) AS match_score
            FROM entities e
            LEFT JOIN entity_aliases ea ON ea.entity_id = e.id AND ea.enabled = true
            WHERE e.entity_type = 'race'
              AND (e.active_from_season IS NULL OR e.active_from_season <= :season)
              AND (e.active_to_season IS NULL OR e.active_to_season >= :season)
              AND (
                    lower(e.display_name) = :display_name
                    OR lower(ea.alias) = ANY(CAST(:candidates AS text[]))
              )
            GROUP BY e.id, e.slug
            ORDER BY match_score DESC, e.slug
            LIMIT 2
            """
        ),
        {
            "season": race.season,
            "display_name": display_name,
            "candidates": candidates,
        },
    )
    rows = list(result)
    if not rows:
        return None
    if len(rows) > 1 and rows[0].match_score == rows[1].match_score:
        raise ValueError(
            f"ambiguous canonical race aliases for {race.name!r} in season {race.season}"
        )
    return rows[0].id, rows[0].slug


async def _create_canonical_race_entity(
    session: AsyncSession, race: JolpicaRace
) -> tuple[Any, str]:
    slug = _canonical_race_slug(race)
    display_name = f"{race.season} {race.name}"
    entity = await session.execute(
        text(
            """
            INSERT INTO entities (
                entity_type, slug, display_name, active_from_season,
                active_to_season, metadata
            ) VALUES (
                'race', :slug, :display_name, :season, :season,
                CAST(:metadata AS jsonb)
            )
            ON CONFLICT (entity_type, slug) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                active_from_season = EXCLUDED.active_from_season,
                active_to_season = EXCLUDED.active_to_season,
                metadata = entities.metadata || EXCLUDED.metadata,
                updated_at = now()
            RETURNING id, slug
            """
        ),
        {
            "slug": slug,
            "display_name": display_name,
            "season": race.season,
            "metadata": json.dumps(
                {
                    "source": PROVIDER,
                    "auto_created_from_calendar": True,
                }
            ),
        },
    )
    row = entity.one()

    aliases = [
        (display_name, "canonical", 100),
        (race.name, "race_name", 98),
        (race.circuit.name, "venue", 90),
    ]
    if race.circuit.locality:
        aliases.append((race.circuit.locality, "venue", 82))

    for alias, alias_type, confidence in aliases:
        await session.execute(
            text(
                """
                INSERT INTO entity_aliases (
                    entity_id, alias, alias_type, confidence,
                    valid_from_season, valid_to_season
                ) VALUES (
                    :entity_id, :alias, :alias_type, :confidence, :season, :season
                )
                ON CONFLICT (entity_id, alias) DO UPDATE SET
                    alias_type = EXCLUDED.alias_type,
                    confidence = EXCLUDED.confidence,
                    valid_from_season = EXCLUDED.valid_from_season,
                    valid_to_season = EXCLUDED.valid_to_season,
                    enabled = true,
                    updated_at = now()
                """
            ),
            {
                "entity_id": row.id,
                "alias": alias,
                "alias_type": alias_type,
                "confidence": confidence,
                "season": race.season,
            },
        )
    return row.id, row.slug


async def _resolve_canonical_race_entity(
    session: AsyncSession, race: JolpicaRace
) -> tuple[Any, str]:
    by_circuit = await _existing_entity_by_circuit(session, race)
    if by_circuit is not None:
        return by_circuit

    by_alias = await _existing_entity_by_alias(session, race)
    if by_alias is not None:
        return by_alias

    return await _create_canonical_race_entity(session, race)


async def upsert_calendar(session: AsyncSession, races: list[JolpicaRace]) -> int:
    if not races:
        return 0

    resolved: list[tuple[JolpicaRace, Any, str]] = []
    for race in races:
        entity_id, slug = await _resolve_canonical_race_entity(session, race)
        resolved.append((race, entity_id, slug))

    fetched_at = datetime.now(UTC)
    written = 0
    seasons = sorted({race.season for race in races})

    # Round is mutable calendar position, not identity. Releasing round numbers
    # before reconciliation prevents a newly inserted event from forcing all
    # later races onto the wrong canonical entity because of UNIQUE(season, round).
    for season in seasons:
        await session.execute(
            text("UPDATE races SET round = NULL WHERE season = :season"),
            {"season": season},
        )
        await session.execute(
            text(
                """
                UPDATE races
                SET provider_race_id = NULL
                WHERE season = :season AND provider = :provider
                """
            ),
            {"season": season, "provider": PROVIDER},
        )

    for race, entity_id, slug in resolved:
        values = {
            "season": race.season,
            "round": race.round,
            "slug": slug,
            "official_name": race.name,
            "circuit": race.circuit.name,
            "country": race.circuit.country,
            "start_at": race.start_at,
            "race_date": race.race_date,
            "entity_id": entity_id,
            "provider": PROVIDER,
            "provider_race_id": _race_provider_id(race),
            "circuit_provider_id": race.circuit.provider_id,
            "locality": race.circuit.locality,
            "latitude": race.circuit.latitude,
            "longitude": race.circuit.longitude,
            "source_url": race.source_url,
            "fetched_at": fetched_at,
        }

        existing = await session.execute(
            text(
                """
                UPDATE races SET
                    round = :round,
                    slug = :slug,
                    official_name = :official_name,
                    circuit = :circuit,
                    country = :country,
                    start_at = :start_at,
                    weekend_start_date = :race_date,
                    weekend_end_date = :race_date,
                    entity_id = :entity_id,
                    provider = :provider,
                    provider_race_id = :provider_race_id,
                    circuit_provider_id = :circuit_provider_id,
                    locality = :locality,
                    latitude = :latitude,
                    longitude = :longitude,
                    source_url = :source_url,
                    fetched_at = :fetched_at,
                    updated_at = now()
                WHERE season = :season AND entity_id = :entity_id
                RETURNING id
                """
            ),
            values,
        )
        if existing.scalar_one_or_none() is None:
            inserted = await session.execute(
                text(
                    """
                    INSERT INTO races (
                        season, round, slug, official_name, circuit, country,
                        start_at, weekend_start_date, weekend_end_date, status,
                        entity_id, provider, provider_race_id, circuit_provider_id,
                        locality, latitude, longitude, source_url, fetched_at
                    ) VALUES (
                        :season, :round, :slug, :official_name, :circuit, :country,
                        :start_at, :race_date, :race_date, 'scheduled', :entity_id,
                        :provider, :provider_race_id, :circuit_provider_id, :locality,
                        :latitude, :longitude, :source_url, :fetched_at
                    )
                    ON CONFLICT (season, slug) DO UPDATE SET
                        round = EXCLUDED.round,
                        official_name = EXCLUDED.official_name,
                        circuit = EXCLUDED.circuit,
                        country = EXCLUDED.country,
                        start_at = EXCLUDED.start_at,
                        weekend_start_date = EXCLUDED.weekend_start_date,
                        weekend_end_date = EXCLUDED.weekend_end_date,
                        entity_id = EXCLUDED.entity_id,
                        provider = EXCLUDED.provider,
                        provider_race_id = EXCLUDED.provider_race_id,
                        circuit_provider_id = EXCLUDED.circuit_provider_id,
                        locality = EXCLUDED.locality,
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude,
                        source_url = EXCLUDED.source_url,
                        fetched_at = EXCLUDED.fetched_at,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                values,
            )
            inserted.scalar_one()
        written += 1

    return written
