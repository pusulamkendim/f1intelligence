from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from app.ingestion.openf1 import OPENF1_BASE_URL
from app.ingestion.openf1_overtakes import OpenF1Overtake


async def overtakes_loaded_session_keys(session, season: int) -> set[int]:
    result = await session.execute(
        text(
            """
            SELECT DISTINCT o.provider_session_key
            FROM session_overtakes o
            JOIN race_sessions rs ON rs.id = o.session_id
            JOIN races r ON r.id = rs.race_id
            WHERE r.season = :season AND o.provider = 'openf1'
            """
        ),
        {"season": season},
    )
    return {int(row[0]) for row in result}


async def upsert_overtakes(
    session,
    *,
    session_id: Any,
    session_key: int,
    rows: list[OpenF1Overtake],
    drivers: dict[int, Any | None],
) -> int:
    source_url = f"{OPENF1_BASE_URL}/overtakes?session_key={session_key}"
    fetched_at = datetime.now(UTC)
    for row in rows:
        await session.execute(
            text(
                """
                INSERT INTO session_overtakes (
                    session_id, overtaking_driver_entity_id, overtaken_driver_entity_id,
                    provider, provider_session_key, overtaking_driver_number,
                    overtaken_driver_number, position, observed_at, source_url,
                    source_timestamp, fetched_at, raw_payload
                ) VALUES (
                    :session_id, :overtaking_driver_entity_id, :overtaken_driver_entity_id,
                    'openf1', :session_key, :overtaking_driver_number,
                    :overtaken_driver_number, :position, :observed_at, :source_url,
                    :source_timestamp, :fetched_at, CAST(:raw_payload AS jsonb)
                )
                ON CONFLICT (
                    provider, provider_session_key, overtaking_driver_number,
                    overtaken_driver_number, observed_at
                ) DO UPDATE SET
                    session_id = EXCLUDED.session_id,
                    overtaking_driver_entity_id = EXCLUDED.overtaking_driver_entity_id,
                    overtaken_driver_entity_id = EXCLUDED.overtaken_driver_entity_id,
                    position = EXCLUDED.position,
                    source_url = EXCLUDED.source_url,
                    source_timestamp = EXCLUDED.source_timestamp,
                    fetched_at = EXCLUDED.fetched_at,
                    raw_payload = EXCLUDED.raw_payload
                """
            ),
            {
                "session_id": session_id,
                "overtaking_driver_entity_id": drivers.get(row.overtaking_driver_number),
                "overtaken_driver_entity_id": drivers.get(row.overtaken_driver_number),
                "session_key": session_key,
                "overtaking_driver_number": row.overtaking_driver_number,
                "overtaken_driver_number": row.overtaken_driver_number,
                "position": row.position,
                "observed_at": row.observed_at,
                "source_url": source_url,
                "source_timestamp": row.observed_at,
                "fetched_at": fetched_at,
                "raw_payload": json.dumps(row.raw_payload),
            },
        )
    return len(rows)
