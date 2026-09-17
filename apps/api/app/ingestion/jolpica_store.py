from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.jolpica import (
    JolpicaConstructorStanding,
    JolpicaDriverStanding,
    JolpicaRace,
)
from app.ingestion.jolpica_hashes import constructor_standings_hash, driver_standings_hash

PROVIDER = "jolpica"


def _race_provider_id(race: JolpicaRace) -> str:
    return f"{race.season}:{race.round}"


async def upsert_calendar(session: AsyncSession, races: list[JolpicaRace]) -> int:
    fetched_at = datetime.now(UTC)
    written = 0
    for race in races:
        result = await session.execute(
            text(
                """
                INSERT INTO races (
                    season, round, slug, official_name, circuit, country, start_at,
                    weekend_start_date, weekend_end_date, status, provider,
                    provider_race_id, circuit_provider_id, locality, latitude,
                    longitude, source_url, fetched_at
                ) VALUES (
                    :season, :round, :slug, :official_name, :circuit, :country,
                    :start_at, :race_date, :race_date, 'scheduled', :provider,
                    :provider_race_id, :circuit_provider_id, :locality, :latitude,
                    :longitude, :source_url, :fetched_at
                )
                ON CONFLICT (season, round) DO UPDATE SET
                    official_name = EXCLUDED.official_name,
                    circuit = EXCLUDED.circuit,
                    country = EXCLUDED.country,
                    start_at = EXCLUDED.start_at,
                    provider = EXCLUDED.provider,
                    provider_race_id = EXCLUDED.provider_race_id,
                    circuit_provider_id = EXCLUDED.circuit_provider_id,
                    locality = EXCLUDED.locality,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    source_url = EXCLUDED.source_url,
                    fetched_at = EXCLUDED.fetched_at
                RETURNING id
                """
            ),
            {
                "season": race.season,
                "round": race.round,
                "slug": f"{race.season}-round-{race.round}",
                "official_name": race.name,
                "circuit": race.circuit.name,
                "country": race.circuit.country,
                "start_at": race.start_at,
                "race_date": race.race_date,
                "provider": PROVIDER,
                "provider_race_id": _race_provider_id(race),
                "circuit_provider_id": race.circuit.provider_id,
                "locality": race.circuit.locality,
                "latitude": race.circuit.latitude,
                "longitude": race.circuit.longitude,
                "source_url": race.source_url,
                "fetched_at": fetched_at,
            },
        )
        if result.scalar_one_or_none() is not None:
            written += 1
    return written


async def _existing_snapshot(
    session: AsyncSession, table: str, season: int, after_round: int, content_hash: str
) -> bool:
    result = await session.execute(
        text(
            f"SELECT 1 FROM {table} "
            "WHERE provider = :provider AND season = :season "
            "AND after_round = :after_round AND content_hash = :content_hash LIMIT 1"
        ),
        {
            "provider": PROVIDER,
            "season": season,
            "after_round": after_round,
            "content_hash": content_hash,
        },
    )
    return result.scalar_one_or_none() is not None


async def store_driver_standings(
    session: AsyncSession,
    season: int,
    after_round: int,
    rows: list[JolpicaDriverStanding],
    source_url: str,
) -> bool:
    content_hash = driver_standings_hash(rows)
    if await _existing_snapshot(
        session, "driver_standings_snapshots", season, after_round, content_hash
    ):
        return False
    snapshot_id = (
        await session.execute(
            text(
                """
                INSERT INTO driver_standings_snapshots
                    (provider, season, after_round, source_url, content_hash)
                VALUES (:provider, :season, :after_round, :source_url, :content_hash)
                RETURNING id
                """
            ),
            {
                "provider": PROVIDER,
                "season": season,
                "after_round": after_round,
                "source_url": source_url,
                "content_hash": content_hash,
            },
        )
    ).scalar_one()
    for row in rows:
        await session.execute(
            text(
                """
                INSERT INTO driver_standing_rows
                    (snapshot_id, driver_provider_id, position, points, wins,
                     constructor_provider_ids)
                VALUES (:snapshot_id, :driver_id, :position, :points, :wins,
                        :constructor_ids)
                """
            ),
            {
                "snapshot_id": snapshot_id,
                "driver_id": row.driver_id,
                "position": row.position,
                "points": row.points,
                "wins": row.wins,
                "constructor_ids": list(row.constructor_ids),
            },
        )
    return True


async def store_constructor_standings(
    session: AsyncSession,
    season: int,
    after_round: int,
    rows: list[JolpicaConstructorStanding],
    source_url: str,
) -> bool:
    content_hash = constructor_standings_hash(rows)
    if await _existing_snapshot(
        session, "constructor_standings_snapshots", season, after_round, content_hash
    ):
        return False
    snapshot_id = (
        await session.execute(
            text(
                """
                INSERT INTO constructor_standings_snapshots
                    (provider, season, after_round, source_url, content_hash)
                VALUES (:provider, :season, :after_round, :source_url, :content_hash)
                RETURNING id
                """
            ),
            {
                "provider": PROVIDER,
                "season": season,
                "after_round": after_round,
                "source_url": source_url,
                "content_hash": content_hash,
            },
        )
    ).scalar_one()
    for row in rows:
        await session.execute(
            text(
                """
                INSERT INTO constructor_standing_rows
                    (snapshot_id, constructor_provider_id, position, points, wins)
                VALUES (:snapshot_id, :constructor_id, :position, :points, :wins)
                """
            ),
            {
                "snapshot_id": snapshot_id,
                "constructor_id": row.constructor_id,
                "position": row.position,
                "points": row.points,
                "wins": row.wins,
            },
        )
    return True


async def record_sync_run(
    session: AsyncSession,
    *,
    dataset: str,
    season: int,
    round_number: int | None,
    source_url: str,
    records_seen: int,
    records_written: int,
    metadata: dict[str, Any] | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO data_sync_runs (
                provider, dataset, season, round, status, source_url,
                completed_at, records_seen, records_written, metadata
            ) VALUES (
                :provider, :dataset, :season, :round, 'succeeded', :source_url,
                now(), :records_seen, :records_written, CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "provider": PROVIDER,
            "dataset": dataset,
            "season": season,
            "round": round_number,
            "source_url": source_url,
            "records_seen": records_seen,
            "records_written": records_written,
            "metadata": __import__("json").dumps(metadata or {}),
        },
    )
