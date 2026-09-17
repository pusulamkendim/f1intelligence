from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.jolpica import (
    JolpicaConstructorStanding,
    JolpicaDriverStanding,
    JolpicaQualifyingResult,
    JolpicaRace,
    JolpicaRaceResult,
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


async def _race_id(session: AsyncSession, season: int, round_number: int) -> Any:
    result = await session.execute(
        text("SELECT id FROM races WHERE season = :season AND round = :round"),
        {"season": season, "round": round_number},
    )
    return result.scalar_one()


async def upsert_race_results(
    session: AsyncSession,
    season: int,
    round_number: int,
    rows: list[JolpicaRaceResult],
    source_url: str,
) -> int:
    race_id = await _race_id(session, season, round_number)
    fetched_at = datetime.now(UTC)
    for row in rows:
        provider_result_id = f"{season}:{round_number}:{row.driver_id}"
        await session.execute(
            text(
                """
                INSERT INTO race_results (
                    race_id, provider, provider_result_id, driver_provider_id,
                    constructor_provider_id, car_number, grid_position, finish_position,
                    position_text, points, laps, status, finish_time, fastest_lap_rank,
                    fastest_lap_number, fastest_lap_time, source_url, fetched_at
                ) VALUES (
                    :race_id, :provider, :provider_result_id, :driver_id, :constructor_id,
                    :car_number, :grid_position, :finish_position, :position_text, :points,
                    :laps, :status, :finish_time, :fastest_lap_rank, :fastest_lap_number,
                    :fastest_lap_time, :source_url, :fetched_at
                )
                ON CONFLICT (provider, provider_result_id) DO UPDATE SET
                    race_id = EXCLUDED.race_id,
                    constructor_provider_id = EXCLUDED.constructor_provider_id,
                    car_number = EXCLUDED.car_number,
                    grid_position = EXCLUDED.grid_position,
                    finish_position = EXCLUDED.finish_position,
                    position_text = EXCLUDED.position_text,
                    points = EXCLUDED.points,
                    laps = EXCLUDED.laps,
                    status = EXCLUDED.status,
                    finish_time = EXCLUDED.finish_time,
                    fastest_lap_rank = EXCLUDED.fastest_lap_rank,
                    fastest_lap_number = EXCLUDED.fastest_lap_number,
                    fastest_lap_time = EXCLUDED.fastest_lap_time,
                    source_url = EXCLUDED.source_url,
                    fetched_at = EXCLUDED.fetched_at
                """
            ),
            {
                "race_id": race_id,
                "provider": PROVIDER,
                "provider_result_id": provider_result_id,
                "driver_id": row.driver_id,
                "constructor_id": row.constructor_id,
                "car_number": row.car_number,
                "grid_position": row.grid_position,
                "finish_position": row.position,
                "position_text": row.position_text,
                "points": row.points,
                "laps": row.laps,
                "status": row.status,
                "finish_time": row.finish_time,
                "fastest_lap_rank": row.fastest_lap_rank,
                "fastest_lap_number": row.fastest_lap_number,
                "fastest_lap_time": row.fastest_lap_time,
                "source_url": source_url,
                "fetched_at": fetched_at,
            },
        )
    if rows:
        await session.execute(
            text("UPDATE races SET status = 'completed', updated_at = now() WHERE id = :race_id"),
            {"race_id": race_id},
        )
    return len(rows)


async def upsert_qualifying_results(
    session: AsyncSession,
    season: int,
    round_number: int,
    rows: list[JolpicaQualifyingResult],
    source_url: str,
) -> int:
    race_id = await _race_id(session, season, round_number)
    fetched_at = datetime.now(UTC)
    for row in rows:
        provider_result_id = f"{season}:{round_number}:{row.driver_id}"
        await session.execute(
            text(
                """
                INSERT INTO qualifying_results (
                    race_id, provider, provider_result_id, driver_provider_id,
                    constructor_provider_id, car_number, position, q1, q2, q3,
                    source_url, fetched_at
                ) VALUES (
                    :race_id, :provider, :provider_result_id, :driver_id, :constructor_id,
                    :car_number, :position, :q1, :q2, :q3, :source_url, :fetched_at
                )
                ON CONFLICT (provider, provider_result_id) DO UPDATE SET
                    race_id = EXCLUDED.race_id,
                    constructor_provider_id = EXCLUDED.constructor_provider_id,
                    car_number = EXCLUDED.car_number,
                    position = EXCLUDED.position,
                    q1 = EXCLUDED.q1,
                    q2 = EXCLUDED.q2,
                    q3 = EXCLUDED.q3,
                    source_url = EXCLUDED.source_url,
                    fetched_at = EXCLUDED.fetched_at
                """
            ),
            {
                "race_id": race_id,
                "provider": PROVIDER,
                "provider_result_id": provider_result_id,
                "driver_id": row.driver_id,
                "constructor_id": row.constructor_id,
                "car_number": row.car_number,
                "position": row.position,
                "q1": row.q1,
                "q2": row.q2,
                "q3": row.q3,
                "source_url": source_url,
                "fetched_at": fetched_at,
            },
        )
    return len(rows)


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
