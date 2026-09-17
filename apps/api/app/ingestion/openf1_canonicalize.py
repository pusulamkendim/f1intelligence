from __future__ import annotations

import re
import unicodedata

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

PROVIDER = "openf1"


def _slugify_driver_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


async def _find_driver_entity(session: AsyncSession, *, full_name: str, season: int):
    result = await session.execute(
        text(
            """
            SELECT e.id
            FROM entities e
            LEFT JOIN entity_aliases ea ON ea.entity_id = e.id AND ea.enabled = true
            WHERE e.entity_type = 'person'
              AND (lower(e.display_name) = lower(:full_name) OR lower(ea.alias) = lower(:full_name))
              AND (e.active_from_season IS NULL OR e.active_from_season <= :season)
              AND (e.active_to_season IS NULL OR e.active_to_season >= :season)
            ORDER BY CASE WHEN lower(e.display_name) = lower(:full_name) THEN 0 ELSE 1 END,
                     ea.confidence DESC NULLS LAST
            LIMIT 1
            """
        ),
        {"full_name": full_name, "season": season},
    )
    return result.scalar_one_or_none()


async def _create_session_driver_entity(
    session: AsyncSession,
    *,
    full_name: str,
    last_name: str | None,
    name_acronym: str | None,
    season: int,
):
    slug = _slugify_driver_name(full_name)
    if not slug:
        return None

    result = await session.execute(
        text(
            """
            INSERT INTO entities (
                entity_type, slug, display_name, active_from_season, active_to_season, metadata
            ) VALUES (
                'person', :slug, :full_name, :season, :season,
                '{"kind":"driver","discovered_via":"openf1_session"}'::jsonb
            )
            ON CONFLICT (entity_type, slug) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                active_from_season = LEAST(COALESCE(entities.active_from_season, EXCLUDED.active_from_season), EXCLUDED.active_from_season),
                active_to_season = GREATEST(COALESCE(entities.active_to_season, EXCLUDED.active_to_season), EXCLUDED.active_to_season),
                metadata = entities.metadata || EXCLUDED.metadata,
                updated_at = now()
            RETURNING id
            """
        ),
        {"slug": slug, "full_name": full_name, "season": season},
    )
    entity_id = result.scalar_one()

    await session.execute(
        text(
            """
            INSERT INTO persons (entity_id, slug, display_name)
            VALUES (:entity_id, :slug, :full_name)
            ON CONFLICT (slug) DO UPDATE SET
                entity_id = EXCLUDED.entity_id,
                display_name = EXCLUDED.display_name,
                updated_at = now()
            """
        ),
        {"entity_id": entity_id, "slug": slug, "full_name": full_name},
    )

    aliases = [(full_name, "canonical", 100)]
    if last_name:
        aliases.append((last_name, "surname", 92))
    if name_acronym:
        aliases.append((name_acronym, "driver_code", 86))
    for alias, alias_type, confidence in aliases:
        await session.execute(
            text(
                """
                INSERT INTO entity_aliases (
                    entity_id, alias, alias_type, confidence, valid_from_season, valid_to_season
                ) VALUES (
                    :entity_id, :alias, :alias_type, :confidence, :season, :season
                )
                ON CONFLICT (entity_id, alias) DO UPDATE SET
                    alias_type = EXCLUDED.alias_type,
                    confidence = GREATEST(entity_aliases.confidence, EXCLUDED.confidence),
                    valid_from_season = LEAST(COALESCE(entity_aliases.valid_from_season, EXCLUDED.valid_from_season), EXCLUDED.valid_from_season),
                    valid_to_season = GREATEST(COALESCE(entity_aliases.valid_to_season, EXCLUDED.valid_to_season), EXCLUDED.valid_to_season),
                    enabled = true,
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
    return entity_id


async def reconcile_unresolved_session_drivers(session: AsyncSession, season: int) -> int:
    """Canonicalize OpenF1-only session participants and repair existing structured rows.

    OpenF1 exposes a driver number per session, not a stable person identifier, so identity is
    deliberately based on an exact canonical/alias full-name match. We do not persist the
    session-local car number as an entity_provider_id.
    """
    result = await session.execute(
        text(
            """
            SELECT se.full_name, max(se.last_name) AS last_name, max(se.name_acronym) AS name_acronym
            FROM session_entries se
            JOIN race_sessions rs ON rs.id = se.session_id
            JOIN races r ON r.id = rs.race_id
            WHERE r.season = :season
              AND se.provider = :provider
              AND se.driver_entity_id IS NULL
              AND se.full_name IS NOT NULL
              AND btrim(se.full_name) <> ''
            GROUP BY se.full_name
            ORDER BY se.full_name
            """
        ),
        {"season": season, "provider": PROVIDER},
    )
    unresolved = [dict(row) for row in result.mappings().all()]
    resolved_names = 0

    for row in unresolved:
        full_name = row["full_name"].strip()
        entity_id = await _find_driver_entity(session, full_name=full_name, season=season)
        if entity_id is None:
            entity_id = await _create_session_driver_entity(
                session,
                full_name=full_name,
                last_name=row["last_name"],
                name_acronym=row["name_acronym"],
                season=season,
            )
        if entity_id is None:
            continue

        await session.execute(
            text(
                """
                UPDATE session_entries se
                SET driver_entity_id = :entity_id
                FROM race_sessions rs, races r
                WHERE se.session_id = rs.id
                  AND rs.race_id = r.id
                  AND r.season = :season
                  AND se.provider = :provider
                  AND se.driver_entity_id IS NULL
                  AND lower(se.full_name) = lower(:full_name)
                """
            ),
            {"entity_id": entity_id, "season": season, "provider": PROVIDER, "full_name": full_name},
        )
        resolved_names += 1

    # Propagate canonical driver links to rows already persisted before reconciliation.
    for table in ("session_results", "session_laps", "session_stints", "session_positions"):
        await session.execute(
            text(
                f"""
                UPDATE {table} target
                SET driver_entity_id = se.driver_entity_id
                FROM session_entries se, race_sessions rs, races r
                WHERE target.session_id = se.session_id
                  AND target.provider = :provider
                  AND target.driver_entity_id IS NULL
                  AND target.provider_driver_number = se.driver_number
                  AND se.session_id = rs.id
                  AND rs.race_id = r.id
                  AND r.season = :season
                  AND se.driver_entity_id IS NOT NULL
                """
            ),
            {"provider": PROVIDER, "season": season},
        )

    return resolved_names
