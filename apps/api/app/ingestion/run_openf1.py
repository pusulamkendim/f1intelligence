from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ingestion.openf1 import OPENF1_BASE_URL, OpenF1Client, OpenF1Session
from app.ingestion.openf1_store import (
    load_season_races,
    loaded_session_result_keys,
    match_meetings_to_races,
    replace_session_entries,
    replace_session_results,
    upsert_meeting_links,
    upsert_sessions,
)


async def _audit(
    session,
    *,
    dataset: str,
    season: int,
    records_seen: int,
    records_written: int,
    metadata: dict[str, object] | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO data_sync_runs (
                provider, dataset, season, status, source_url, completed_at,
                records_seen, records_written, metadata
            ) VALUES (
                'openf1', :dataset, :season, 'succeeded', :source_url, now(),
                :records_seen, :records_written, CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "dataset": dataset,
            "season": season,
            "source_url": f"{OPENF1_BASE_URL}/{dataset}",
            "records_seen": records_seen,
            "records_written": records_written,
            "metadata": json.dumps(metadata or {}),
        },
    )


def _result_candidates(
    sessions: list[OpenF1Session],
    cached_keys: set[int],
    now: datetime | None = None,
) -> tuple[list[OpenF1Session], list[int]]:
    cutoff = (now or datetime.now(UTC)) - timedelta(minutes=30)
    eligible = [
        item
        for item in sessions
        if not item.is_cancelled and item.date_end is not None and item.date_end <= cutoff
    ]
    if not eligible:
        return [], []
    latest = max(eligible, key=lambda item: item.date_end or item.date_start).session_key
    to_fetch = [item for item in eligible if item.session_key not in cached_keys or item.session_key == latest]
    reused = [item.session_key for item in eligible if item.session_key in cached_keys]
    return to_fetch, reused


async def sync_openf1(season: int) -> dict[str, object]:
    settings = get_settings()
    headers = {"User-Agent": settings.source_user_agent, "Accept": "application/json"}
    timeout = httpx.Timeout(
        connect=settings.source_http_connect_timeout_seconds,
        read=settings.source_http_read_timeout_seconds,
        write=settings.source_http_read_timeout_seconds,
        pool=settings.source_http_connect_timeout_seconds,
    )
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as http_client:
        client = OpenF1Client(
            http_client,
            min_interval_seconds=settings.openf1_min_interval_seconds,
            retries=settings.source_http_retries,
            retry_backoff_seconds=settings.source_http_retry_backoff_seconds,
        )
        meetings = await client.meetings(season)
        provider_sessions = await client.sessions(season)

        async with SessionLocal() as db:
            async with db.begin():
                races = await load_season_races(db, season)
                matches = match_meetings_to_races(meetings, races)
                meeting_links = await upsert_meeting_links(db, meetings, matches)
                session_ids = await upsert_sessions(db, provider_sessions, matches)
                cached_keys = await loaded_session_result_keys(db, season)
                await _audit(
                    db,
                    dataset="meetings",
                    season=season,
                    records_seen=len(meetings),
                    records_written=meeting_links,
                    metadata={"matched_races": len(matches)},
                )
                await _audit(
                    db,
                    dataset="sessions",
                    season=season,
                    records_seen=len(provider_sessions),
                    records_written=len(session_ids),
                    metadata={"matched_sessions": len(session_ids)},
                )

        matched_sessions = [item for item in provider_sessions if item.session_key in session_ids]
        candidates, reused_keys = _result_candidates(matched_sessions, cached_keys)
        results_written = 0
        entries_written = 0
        unresolved_entries = 0
        fetched_session_keys: list[int] = []

        for item in sorted(candidates, key=lambda row: row.date_start):
            drivers = await client.drivers(item.session_key)
            results = await client.session_results(item.session_key)
            async with SessionLocal() as db:
                async with db.begin():
                    mappings, unresolved = await replace_session_entries(
                        db,
                        season=season,
                        session_id=session_ids[item.session_key],
                        drivers=drivers,
                    )
                    written = await replace_session_results(
                        db,
                        session_id=session_ids[item.session_key],
                        session_key=item.session_key,
                        rows=results,
                        entity_mappings=mappings,
                    )
                    await _audit(
                        db,
                        dataset="session_result",
                        season=season,
                        records_seen=len(results),
                        records_written=written,
                        metadata={
                            "session_key": item.session_key,
                            "session_code": item.session_code,
                            "drivers": len(drivers),
                            "unresolved_entries": unresolved,
                        },
                    )
            fetched_session_keys.append(item.session_key)
            entries_written += len(drivers)
            results_written += len(results)
            unresolved_entries += unresolved

    unmatched_meetings = sorted(
        meeting.meeting_key for meeting in meetings if meeting.meeting_key not in matches
    )
    return {
        "season": season,
        "meetings_seen": len(meetings),
        "meetings_matched": len(matches),
        "unmatched_meeting_keys": unmatched_meetings,
        "sessions_seen": len(provider_sessions),
        "sessions_matched": len(session_ids),
        "fetched_result_session_keys": fetched_session_keys,
        "cached_result_session_keys": sorted(reused_keys),
        "session_entries_written": entries_written,
        "session_results_written": results_written,
        "unresolved_session_entries": unresolved_entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync race-weekend sessions from OpenF1")
    parser.add_argument("--season", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(sync_openf1(args.season)), indent=2))


if __name__ == "__main__":
    main()
