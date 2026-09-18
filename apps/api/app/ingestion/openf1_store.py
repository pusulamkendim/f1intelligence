from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.openf1 import OpenF1Driver, OpenF1Meeting, OpenF1Session, OpenF1SessionResult

PROVIDER = "openf1"
QUALIFYING_SEGMENTS = (("q1", "Q1", 1), ("q2", "Q2", 2), ("q3", "Q3", 3))


def qualifying_segment_definitions(session_code: str) -> tuple[tuple[str, str, int], ...]:
    return QUALIFYING_SEGMENTS if session_code == "qualifying" else ()


async def _upsert_session_segments(
    session: AsyncSession,
    *,
    session_id: Any,
    item: OpenF1Session,
) -> None:
    for segment_code, segment_name, sequence in qualifying_segment_definitions(
        item.session_code
    ):
        await session.execute(
            text(
                """
                INSERT INTO session_segments (
                    session_id,
                    segment_code,
                    segment_name,
                    segment_type,
                    sequence,
                    provider,
                    provider_segment_id,
                    source_url,
                    fetched_at,
                    raw_metadata
                ) VALUES (
                    :session_id,
                    :segment_code,
                    :segment_name,
                    'qualifying_phase',
                    :sequence,
                    :provider,
                    NULL,
                    :source_url,
                    :fetched_at,
                    CAST(:raw_metadata AS jsonb)
                )
                ON CONFLICT (session_id, segment_code) DO UPDATE SET
                    segment_name = EXCLUDED.segment_name,
                    segment_type = EXCLUDED.segment_type,
                    sequence = EXCLUDED.sequence,
                    provider = EXCLUDED.provider,
                    source_url = EXCLUDED.source_url,
                    fetched_at = EXCLUDED.fetched_at,
                    raw_metadata = EXCLUDED.raw_metadata
                """
            ),
            {
                "session_id": session_id,
                "segment_code": segment_code,
                "segment_name": segment_name,
                "sequence": sequence,
                "provider": PROVIDER,
                "source_url": (
                    f"https://api.openf1.org/v1/sessions?session_key={item.session_key}"
                ),
                "fetched_at": datetime.now(UTC),
                "raw_metadata": __import__("json").dumps(
                    {
                        "derived_from": "openf1_session",
                        "provider_session_id": str(item.session_key),
                    }
                ),
            },
        )


async def load_season_races(session: AsyncSession, season: int) -> list[dict[str, Any]]:
    result = await session.execute(text("""
        SELECT id, round, official_name, country, circuit, start_at
        FROM races WHERE season = :season AND start_at IS NOT NULL ORDER BY round
    """), {"season": season})
    return [dict(row) for row in result.mappings().all()]


def match_meetings_to_races(meetings: list[OpenF1Meeting], races: list[dict[str, Any]]) -> dict[int, Any]:
    matches: dict[int, Any] = {}
    used_races: set[Any] = set()
    for meeting in sorted(meetings, key=lambda item: item.date_end):
        candidates = []
        for race in races:
            if race["id"] in used_races or race["start_at"] is None:
                continue
            delta = abs((race["start_at"] - meeting.date_end).total_seconds())
            if delta <= 36 * 3600:
                candidates.append((delta, race["id"]))
        if candidates:
            _, race_id = min(candidates, key=lambda item: item[0])
            matches[meeting.meeting_key] = race_id
            used_races.add(race_id)
    return matches


async def upsert_meeting_links(session: AsyncSession, meetings: list[OpenF1Meeting], race_matches: dict[int, Any]) -> int:
    written = 0
    for meeting in meetings:
        race_id = race_matches.get(meeting.meeting_key)
        if race_id is None:
            continue
        await session.execute(text("""
            INSERT INTO race_provider_ids (race_id, provider, provider_id, provider_entity_type, source_url, fetched_at, raw_metadata)
            VALUES (:race_id, :provider, :provider_id, 'meeting', :source_url, now(), CAST(:raw_metadata AS jsonb))
            ON CONFLICT (provider, provider_entity_type, provider_id) DO UPDATE SET
                race_id = EXCLUDED.race_id, source_url = EXCLUDED.source_url,
                fetched_at = EXCLUDED.fetched_at, raw_metadata = EXCLUDED.raw_metadata
        """), {"race_id": race_id, "provider": PROVIDER, "provider_id": str(meeting.meeting_key),
               "source_url": f"https://api.openf1.org/v1/meetings?meeting_key={meeting.meeting_key}",
               "raw_metadata": __import__("json").dumps({"meeting_name": meeting.meeting_name, "meeting_official_name": meeting.meeting_official_name, "circuit_key": meeting.circuit_key, "location": meeting.location})})
        written += 1
    return written


async def upsert_sessions(session: AsyncSession, sessions: list[OpenF1Session], race_matches: dict[int, Any]) -> dict[int, Any]:
    by_meeting: dict[int, list[OpenF1Session]] = {}
    for item in sessions:
        if item.meeting_key in race_matches:
            by_meeting.setdefault(item.meeting_key, []).append(item)
    session_ids: dict[int, Any] = {}
    for meeting_key, meeting_sessions in by_meeting.items():
        for sequence, item in enumerate(sorted(meeting_sessions, key=lambda row: row.date_start), start=1):
            result = await session.execute(text("""
                INSERT INTO race_sessions (race_id, provider, provider_session_id, provider_meeting_id, session_code, session_name, session_type, sequence, starts_at, ends_at, gmt_offset, is_cancelled, source_url, fetched_at, raw_metadata)
                VALUES (:race_id, :provider, :provider_session_id, :provider_meeting_id, :session_code, :session_name, :session_type, :sequence, :starts_at, :ends_at, :gmt_offset, :is_cancelled, :source_url, :fetched_at, CAST(:raw_metadata AS jsonb))
                ON CONFLICT (provider, provider_session_id) DO UPDATE SET
                    race_id = EXCLUDED.race_id, provider_meeting_id = EXCLUDED.provider_meeting_id,
                    session_code = EXCLUDED.session_code, session_name = EXCLUDED.session_name,
                    session_type = EXCLUDED.session_type, sequence = EXCLUDED.sequence,
                    starts_at = EXCLUDED.starts_at, ends_at = EXCLUDED.ends_at,
                    gmt_offset = EXCLUDED.gmt_offset, is_cancelled = EXCLUDED.is_cancelled,
                    source_url = EXCLUDED.source_url, fetched_at = EXCLUDED.fetched_at,
                    raw_metadata = EXCLUDED.raw_metadata RETURNING id
            """), {"race_id": race_matches[meeting_key], "provider": PROVIDER,
                     "provider_session_id": str(item.session_key), "provider_meeting_id": str(item.meeting_key),
                     "session_code": item.session_code, "session_name": item.session_name, "session_type": item.session_type,
                     "sequence": sequence, "starts_at": item.date_start, "ends_at": item.date_end,
                     "gmt_offset": item.gmt_offset, "is_cancelled": item.is_cancelled,
                     "source_url": f"https://api.openf1.org/v1/sessions?session_key={item.session_key}",
                     "fetched_at": datetime.now(UTC),
                     "raw_metadata": __import__("json").dumps({"circuit_key": item.circuit_key, "circuit_short_name": item.circuit_short_name, "country_name": item.country_name, "location": item.location})})
            session_id = result.scalar_one()
            session_ids[item.session_key] = session_id
            await _upsert_session_segments(
                session,
                session_id=session_id,
                item=item,
            )
    return session_ids


async def _resolve_driver_entity(session: AsyncSession, season: int, driver: OpenF1Driver) -> tuple[Any | None, Any | None]:
    """Resolve person and team independently; a session-local car number is never person identity."""
    driver_entity_id = None
    if driver.full_name:
        result = await session.execute(text("""
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
        """), {"full_name": driver.full_name, "season": season})
        driver_entity_id = result.scalar_one_or_none()

    team_entity_id = None
    if driver.team_name:
        result = await session.execute(text("""
            SELECT ea.entity_id
            FROM entity_aliases ea
            JOIN entities e ON e.id = ea.entity_id
            WHERE e.entity_type = 'team' AND lower(ea.alias) = lower(:team_name) AND ea.enabled = true
            ORDER BY ea.confidence DESC LIMIT 1
        """), {"team_name": driver.team_name})
        team_entity_id = result.scalar_one_or_none()
    return driver_entity_id, team_entity_id


async def replace_session_entries(session: AsyncSession, *, season: int, session_id: Any, drivers: list[OpenF1Driver]) -> tuple[dict[int, tuple[Any | None, Any | None]], int]:
    await session.execute(text("DELETE FROM session_entries WHERE session_id = :session_id"), {"session_id": session_id})
    mappings: dict[int, tuple[Any | None, Any | None]] = {}
    unresolved = 0
    for driver in drivers:
        driver_entity_id, team_entity_id = await _resolve_driver_entity(session, season, driver)
        if driver_entity_id is None or team_entity_id is None:
            unresolved += 1
        mappings[driver.driver_number] = (driver_entity_id, team_entity_id)
        await session.execute(text("""
            INSERT INTO session_entries (session_id, provider, driver_provider_id, driver_number, driver_entity_id, team_entity_id, broadcast_name, first_name, last_name, full_name, name_acronym, team_name, team_colour, headshot_reference_url, source_url, raw_metadata)
            VALUES (:session_id, :provider, :driver_provider_id, :driver_number, :driver_entity_id, :team_entity_id, :broadcast_name, :first_name, :last_name, :full_name, :name_acronym, :team_name, :team_colour, :headshot_reference_url, :source_url, '{}'::jsonb)
        """), {"session_id": session_id, "provider": PROVIDER, "driver_provider_id": str(driver.driver_number),
                 "driver_number": driver.driver_number, "driver_entity_id": driver_entity_id, "team_entity_id": team_entity_id,
                 "broadcast_name": driver.broadcast_name, "first_name": driver.first_name, "last_name": driver.last_name,
                 "full_name": driver.full_name, "name_acronym": driver.name_acronym, "team_name": driver.team_name,
                 "team_colour": driver.team_colour, "headshot_reference_url": driver.headshot_url,
                 "source_url": f"https://api.openf1.org/v1/drivers?session_key={driver.session_key}"})
    return mappings, unresolved


async def replace_session_results(session: AsyncSession, *, session_id: Any, session_key: int, rows: list[OpenF1SessionResult], entity_mappings: dict[int, tuple[Any | None, Any | None]]) -> int:
    await session.execute(text("DELETE FROM session_results WHERE session_id = :session_id"), {"session_id": session_id})
    for row in rows:
        driver_entity_id, team_entity_id = entity_mappings.get(row.driver_number, (None, None))
        await session.execute(text("""
            INSERT INTO session_results (session_id, provider, provider_result_id, driver_provider_id, driver_number, driver_entity_id, team_entity_id, position, dnf, dns, dsq, number_of_laps, duration_seconds, q1_seconds, q2_seconds, q3_seconds, gap_to_leader_seconds, gap_to_leader_text, q1_gap_seconds, q2_gap_seconds, q3_gap_seconds, source_url)
            VALUES (:session_id, :provider, :provider_result_id, :driver_provider_id, :driver_number, :driver_entity_id, :team_entity_id, :position, :dnf, :dns, :dsq, :number_of_laps, :duration_seconds, :q1_seconds, :q2_seconds, :q3_seconds, :gap_to_leader_seconds, :gap_to_leader_text, :q1_gap_seconds, :q2_gap_seconds, :q3_gap_seconds, :source_url)
        """), {"session_id": session_id, "provider": PROVIDER, "provider_result_id": f"{session_key}:{row.driver_number}",
                 "driver_provider_id": str(row.driver_number), "driver_number": row.driver_number,
                 "driver_entity_id": driver_entity_id, "team_entity_id": team_entity_id, "position": row.position,
                 "dnf": row.dnf, "dns": row.dns, "dsq": row.dsq, "number_of_laps": row.number_of_laps,
                 "duration_seconds": row.duration_seconds, "q1_seconds": row.q1_seconds, "q2_seconds": row.q2_seconds,
                 "q3_seconds": row.q3_seconds, "gap_to_leader_seconds": row.gap_to_leader_seconds,
                 "gap_to_leader_text": row.gap_to_leader_text, "q1_gap_seconds": row.q1_gap_seconds,
                 "q2_gap_seconds": row.q2_gap_seconds, "q3_gap_seconds": row.q3_gap_seconds,
                 "source_url": f"https://api.openf1.org/v1/session_result?session_key={session_key}"})
    return len(rows)


async def loaded_session_result_keys(session: AsyncSession, season: int) -> set[int]:
    result = await session.execute(text("""
        SELECT DISTINCT rs.provider_session_id FROM race_sessions rs
        JOIN races r ON r.id = rs.race_id JOIN session_results sr ON sr.session_id = rs.id
        WHERE r.season = :season AND rs.provider = :provider
    """), {"season": season, "provider": PROVIDER})
    return {int(value) for value in result.scalars().all()}
