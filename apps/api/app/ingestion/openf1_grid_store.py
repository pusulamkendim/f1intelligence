from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from app.ingestion.openf1 import OPENF1_BASE_URL
from app.ingestion.openf1_grid import OpenF1StartingGridRow


async def starting_grid_loaded_session_keys(session, season: int) -> set[int]:
    result = await session.execute(
        text(
            """
            SELECT DISTINCT sg.provider_session_key
            FROM session_starting_grid sg
            JOIN race_sessions rs ON rs.id = sg.session_id
            JOIN races r ON r.id = rs.race_id
            WHERE r.season = :season AND sg.provider = 'openf1'
            """
        ),
        {"season": season},
    )
    return {int(row[0]) for row in result}


async def starting_grid_entity_maps(
    session, session_id: Any
) -> tuple[dict[int, Any | None], dict[int, Any | None]]:
    result = await session.execute(
        text(
            """
            SELECT driver_number, driver_entity_id, team_entity_id
            FROM session_entries
            WHERE session_id = :session_id AND provider = 'openf1'
            """
        ),
        {"session_id": session_id},
    )
    rows = result.mappings().all()
    drivers = {int(row["driver_number"]): row["driver_entity_id"] for row in rows}
    teams = {int(row["driver_number"]): row["team_entity_id"] for row in rows}
    return drivers, teams


async def upsert_starting_grid(
    session,
    *,
    session_id: Any,
    session_key: int,
    rows: list[OpenF1StartingGridRow],
    drivers: dict[int, Any | None],
    teams: dict[int, Any | None],
) -> int:
    source_url = f"{OPENF1_BASE_URL}/starting_grid?session_key={session_key}"
    fetched_at = datetime.now(UTC)
    for row in rows:
        await session.execute(
            text(
                """
                INSERT INTO session_starting_grid (
                    session_id, driver_entity_id, team_entity_id, provider,
                    provider_session_key, provider_driver_number, position,
                    qualifying_lap_duration_seconds, source_url, source_timestamp,
                    fetched_at, raw_payload
                ) VALUES (
                    :session_id, :driver_entity_id, :team_entity_id, 'openf1',
                    :session_key, :driver_number, :position, :lap_duration,
                    :source_url, NULL, :fetched_at, CAST(:raw_payload AS jsonb)
                )
                ON CONFLICT (provider, provider_session_key, provider_driver_number)
                DO UPDATE SET
                    session_id = EXCLUDED.session_id,
                    driver_entity_id = EXCLUDED.driver_entity_id,
                    team_entity_id = EXCLUDED.team_entity_id,
                    position = EXCLUDED.position,
                    qualifying_lap_duration_seconds = EXCLUDED.qualifying_lap_duration_seconds,
                    source_url = EXCLUDED.source_url,
                    fetched_at = EXCLUDED.fetched_at,
                    raw_payload = EXCLUDED.raw_payload
                """
            ),
            {
                "session_id": session_id,
                "driver_entity_id": drivers.get(row.driver_number),
                "team_entity_id": teams.get(row.driver_number),
                "session_key": session_key,
                "driver_number": row.driver_number,
                "position": row.position,
                "lap_duration": row.lap_duration_seconds,
                "source_url": source_url,
                "fetched_at": fetched_at,
                "raw_payload": json.dumps(row.raw_payload),
            },
        )
    return len(rows)
