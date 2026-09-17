from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.openf1_telemetry import OpenF1Lap, OpenF1Position, OpenF1Stint

PROVIDER = "openf1"


async def telemetry_loaded_session_keys(session: AsyncSession, season: int) -> set[int]:
    result = await session.execute(text("""
        SELECT DISTINCT rs.provider_session_id
        FROM race_sessions rs
        JOIN races r ON r.id = rs.race_id
        WHERE r.season = :season AND rs.provider = :provider
          AND (EXISTS (SELECT 1 FROM session_laps l WHERE l.session_id = rs.id)
            OR EXISTS (SELECT 1 FROM session_stints s WHERE s.session_id = rs.id)
            OR EXISTS (SELECT 1 FROM session_positions p WHERE p.session_id = rs.id))
    """), {"season": season, "provider": PROVIDER})
    return {int(value) for value in result.scalars().all()}


async def driver_entity_map(session: AsyncSession, session_id: Any) -> dict[int, Any | None]:
    result = await session.execute(text("""
        SELECT driver_number, driver_entity_id FROM session_entries WHERE session_id = :session_id
    """), {"session_id": session_id})
    return {int(row["driver_number"]): row["driver_entity_id"] for row in result.mappings().all()}


async def upsert_laps(session: AsyncSession, *, session_id: Any, session_key: int, rows: list[OpenF1Lap], drivers: dict[int, Any | None]) -> int:
    fetched_at = datetime.now(UTC)
    for row in rows:
        await session.execute(text("""
            INSERT INTO session_laps (session_id, driver_id, provider, provider_session_key, provider_driver_number, lap_number, lap_duration_seconds, is_pit_out_lap, started_at, source_url, source_timestamp, fetched_at, raw_payload)
            VALUES (:session_id, :driver_id, :provider, :session_key, :driver_number, :lap_number, :duration, :pit_out, :started_at, :source_url, :source_timestamp, :fetched_at, CAST(:raw_payload AS jsonb))
            ON CONFLICT (provider, provider_session_key, provider_driver_number, lap_number) DO UPDATE SET driver_id=EXCLUDED.driver_id, lap_duration_seconds=EXCLUDED.lap_duration_seconds, is_pit_out_lap=EXCLUDED.is_pit_out_lap, started_at=EXCLUDED.started_at, source_timestamp=EXCLUDED.source_timestamp, fetched_at=EXCLUDED.fetched_at, raw_payload=EXCLUDED.raw_payload
        """), {"session_id": session_id, "driver_id": drivers.get(row.driver_number), "provider": PROVIDER, "session_key": session_key, "driver_number": row.driver_number, "lap_number": row.lap_number, "duration": row.lap_duration_seconds, "pit_out": row.is_pit_out_lap, "started_at": row.started_at, "source_url": f"https://api.openf1.org/v1/laps?session_key={session_key}", "source_timestamp": row.started_at, "fetched_at": fetched_at, "raw_payload": json.dumps(row.raw_payload)})
    return len(rows)


async def upsert_stints(session: AsyncSession, *, session_id: Any, session_key: int, rows: list[OpenF1Stint], drivers: dict[int, Any | None]) -> int:
    fetched_at = datetime.now(UTC)
    for row in rows:
        await session.execute(text("""
            INSERT INTO session_stints (session_id, driver_id, provider, provider_session_key, provider_driver_number, stint_number, lap_start, lap_end, compound, tyre_age_at_start, source_url, fetched_at, raw_payload)
            VALUES (:session_id, :driver_id, :provider, :session_key, :driver_number, :stint_number, :lap_start, :lap_end, :compound, :tyre_age, :source_url, :fetched_at, CAST(:raw_payload AS jsonb))
            ON CONFLICT (provider, provider_session_key, provider_driver_number, stint_number) DO UPDATE SET driver_id=EXCLUDED.driver_id, lap_start=EXCLUDED.lap_start, lap_end=EXCLUDED.lap_end, compound=EXCLUDED.compound, tyre_age_at_start=EXCLUDED.tyre_age_at_start, fetched_at=EXCLUDED.fetched_at, raw_payload=EXCLUDED.raw_payload
        """), {"session_id": session_id, "driver_id": drivers.get(row.driver_number), "provider": PROVIDER, "session_key": session_key, "driver_number": row.driver_number, "stint_number": row.stint_number, "lap_start": row.lap_start, "lap_end": row.lap_end, "compound": row.compound, "tyre_age": row.tyre_age_at_start, "source_url": f"https://api.openf1.org/v1/stints?session_key={session_key}", "fetched_at": fetched_at, "raw_payload": json.dumps(row.raw_payload)})
    return len(rows)


async def upsert_positions(session: AsyncSession, *, session_id: Any, session_key: int, rows: list[OpenF1Position], drivers: dict[int, Any | None]) -> int:
    fetched_at = datetime.now(UTC)
    for row in rows:
        await session.execute(text("""
            INSERT INTO session_positions (session_id, driver_id, provider, provider_session_key, provider_driver_number, observed_at, position, source_url, source_timestamp, fetched_at, raw_payload)
            VALUES (:session_id, :driver_id, :provider, :session_key, :driver_number, :observed_at, :position, :source_url, :observed_at, :fetched_at, CAST(:raw_payload AS jsonb))
            ON CONFLICT (provider, provider_session_key, provider_driver_number, observed_at) DO UPDATE SET driver_id=EXCLUDED.driver_id, position=EXCLUDED.position, fetched_at=EXCLUDED.fetched_at, raw_payload=EXCLUDED.raw_payload
        """), {"session_id": session_id, "driver_id": drivers.get(row.driver_number), "provider": PROVIDER, "session_key": session_key, "driver_number": row.driver_number, "observed_at": row.observed_at, "position": row.position, "source_url": f"https://api.openf1.org/v1/position?session_key={session_key}", "fetched_at": fetched_at, "raw_payload": json.dumps(row.raw_payload)})
    return len(rows)
