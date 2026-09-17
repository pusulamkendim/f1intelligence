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
from app.ingestion.openf1_canonicalize import reconcile_unresolved_session_drivers
from app.ingestion.openf1_context import parse_intervals, parse_pit_stops, parse_race_control, parse_weather
from app.ingestion.openf1_context_store import context_loaded_session_keys, upsert_intervals, upsert_pit_stops, upsert_race_control, upsert_weather
from app.ingestion.openf1_grid import parse_starting_grid
from app.ingestion.openf1_grid_store import starting_grid_entity_maps, starting_grid_loaded_session_keys, upsert_starting_grid
from app.ingestion.openf1_store import load_season_races, loaded_session_result_keys, match_meetings_to_races, replace_session_entries, replace_session_results, upsert_meeting_links, upsert_sessions
from app.ingestion.openf1_telemetry_store import driver_entity_map, telemetry_loaded_session_keys, upsert_laps, upsert_positions, upsert_stints


async def _audit(session, *, dataset: str, season: int, records_seen: int, records_written: int, metadata: dict[str, object] | None = None) -> None:
    await session.execute(text("""INSERT INTO data_sync_runs (provider,dataset,season,status,source_url,completed_at,records_seen,records_written,metadata) VALUES ('openf1',:dataset,:season,'succeeded',:source_url,now(),:records_seen,:records_written,CAST(:metadata AS jsonb))"""), {"dataset": dataset, "season": season, "source_url": f"{OPENF1_BASE_URL}/{dataset}", "records_seen": records_seen, "records_written": records_written, "metadata": json.dumps(metadata or {})})


def _completed_sessions(sessions: list[OpenF1Session], now: datetime | None = None) -> list[OpenF1Session]:
    cutoff = (now or datetime.now(UTC)) - timedelta(minutes=30)
    return [item for item in sessions if not item.is_cancelled and item.date_end is not None and item.date_end <= cutoff]


def _result_candidates(sessions: list[OpenF1Session], cached_keys: set[int], now: datetime | None = None) -> tuple[list[OpenF1Session], list[int]]:
    eligible = _completed_sessions(sessions, now)
    if not eligible:
        return [], []
    latest = max(eligible, key=lambda item: item.date_end or item.date_start).session_key
    return [item for item in eligible if item.session_key not in cached_keys or item.session_key == latest], [item.session_key for item in eligible if item.session_key in cached_keys]


def _bounded_candidates(sessions: list[OpenF1Session], cached_keys: set[int], *, limit: int = 2, now: datetime | None = None) -> list[OpenF1Session]:
    eligible = sorted(_completed_sessions(sessions, now), key=lambda item: item.date_end or item.date_start)
    if not eligible or limit <= 0:
        return []
    latest = eligible[-1]
    uncached = [item for item in eligible if item.session_key not in cached_keys and item.session_key != latest.session_key]
    selected = uncached[: max(0, limit - 1)]
    if latest.session_key not in {item.session_key for item in selected}:
        selected.append(latest)
    return selected[:limit]


def _telemetry_candidates(sessions: list[OpenF1Session], cached_keys: set[int], *, limit: int = 2, now: datetime | None = None) -> list[OpenF1Session]:
    return _bounded_candidates(sessions, cached_keys, limit=limit, now=now)


def _grid_sessions(sessions: list[OpenF1Session]) -> list[OpenF1Session]:
    return [item for item in sessions if item.session_code in {"race", "sprint"}]


async def sync_openf1(season: int, *, telemetry_limit: int = 2) -> dict[str, object]:
    settings = get_settings()
    headers = {"User-Agent": settings.source_user_agent, "Accept": "application/json"}
    timeout = httpx.Timeout(connect=settings.source_http_connect_timeout_seconds, read=settings.source_http_read_timeout_seconds, write=settings.source_http_read_timeout_seconds, pool=settings.source_http_connect_timeout_seconds)
    canonicalized_driver_names = 0
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as http_client:
        client = OpenF1Client(http_client, min_interval_seconds=settings.openf1_min_interval_seconds, retries=settings.source_http_retries, retry_backoff_seconds=settings.source_http_retry_backoff_seconds)
        meetings = await client.meetings(season)
        provider_sessions = await client.sessions(season)
        async with SessionLocal() as db:
            async with db.begin():
                races = await load_season_races(db, season)
                matches = match_meetings_to_races(meetings, races)
                meeting_links = await upsert_meeting_links(db, meetings, matches)
                session_ids = await upsert_sessions(db, provider_sessions, matches)
                canonicalized_driver_names += await reconcile_unresolved_session_drivers(db, season)
                cached_keys = await loaded_session_result_keys(db, season)
                telemetry_cached = await telemetry_loaded_session_keys(db, season)
                context_cached = await context_loaded_session_keys(db, season)
                grid_cached = await starting_grid_loaded_session_keys(db, season)
                await _audit(db, dataset="meetings", season=season, records_seen=len(meetings), records_written=meeting_links, metadata={"matched_races": len(matches)})
                await _audit(db, dataset="sessions", season=season, records_seen=len(provider_sessions), records_written=len(session_ids), metadata={"matched_sessions": len(session_ids), "canonicalized_driver_names": canonicalized_driver_names})
        matched_sessions = [item for item in provider_sessions if item.session_key in session_ids]
        candidates, reused_keys = _result_candidates(matched_sessions, cached_keys)
        results_written = entries_written = unresolved_entries = 0
        fetched_session_keys: list[int] = []
        for item in sorted(candidates, key=lambda row: row.date_start):
            drivers = await client.drivers(item.session_key)
            results = await client.session_results(item.session_key)
            async with SessionLocal() as db:
                async with db.begin():
                    mappings, unresolved = await replace_session_entries(db, season=season, session_id=session_ids[item.session_key], drivers=drivers)
                    if unresolved:
                        canonicalized_driver_names += await reconcile_unresolved_session_drivers(db, season)
                        mappings, unresolved = await replace_session_entries(db, season=season, session_id=session_ids[item.session_key], drivers=drivers)
                    written = await replace_session_results(db, session_id=session_ids[item.session_key], session_key=item.session_key, rows=results, entity_mappings=mappings)
                    await _audit(db, dataset="session_result", season=season, records_seen=len(results), records_written=written, metadata={"session_key": item.session_key, "session_code": item.session_code, "drivers": len(drivers), "unresolved_entries": unresolved})
            fetched_session_keys.append(item.session_key)
            entries_written += len(drivers)
            results_written += len(results)
            unresolved_entries += unresolved

        grid_summary: list[dict[str, int]] = []
        for item in _bounded_candidates(_grid_sessions(matched_sessions), grid_cached, limit=telemetry_limit):
            grid = parse_starting_grid(await client._get("starting_grid", session_key=item.session_key))
            if not grid:
                continue
            drivers = await client.drivers(item.session_key)
            async with SessionLocal() as db:
                async with db.begin():
                    mappings, unresolved = await replace_session_entries(db, season=season, session_id=session_ids[item.session_key], drivers=drivers)
                    if unresolved:
                        canonicalized_driver_names += await reconcile_unresolved_session_drivers(db, season)
                        await replace_session_entries(db, season=season, session_id=session_ids[item.session_key], drivers=drivers)
                    driver_map, team_map = await starting_grid_entity_maps(db, session_ids[item.session_key])
                    count = await upsert_starting_grid(db, session_id=session_ids[item.session_key], session_key=item.session_key, rows=grid, drivers=driver_map, teams=team_map)
                    await _audit(db, dataset="starting_grid", season=season, records_seen=len(grid), records_written=count, metadata={"session_key": item.session_key, "session_code": item.session_code})
            grid_summary.append({"session_key": item.session_key, "rows": len(grid)})

        telemetry_summary: list[dict[str, int]] = []
        for item in _telemetry_candidates(matched_sessions, telemetry_cached, limit=telemetry_limit):
            laps = await client.laps(item.session_key)
            stints = await client.stints(item.session_key)
            positions = await client.positions(item.session_key)
            async with SessionLocal() as db:
                async with db.begin():
                    driver_map = await driver_entity_map(db, session_ids[item.session_key])
                    lap_count = await upsert_laps(db, session_id=session_ids[item.session_key], session_key=item.session_key, rows=laps, drivers=driver_map)
                    stint_count = await upsert_stints(db, session_id=session_ids[item.session_key], session_key=item.session_key, rows=stints, drivers=driver_map)
                    position_count = await upsert_positions(db, session_id=session_ids[item.session_key], session_key=item.session_key, rows=positions, drivers=driver_map)
                    await _audit(db, dataset="telemetry", season=season, records_seen=len(laps) + len(stints) + len(positions), records_written=lap_count + stint_count + position_count, metadata={"session_key": item.session_key, "session_code": item.session_code, "laps": lap_count, "stints": stint_count, "positions": position_count})
            telemetry_summary.append({"session_key": item.session_key, "laps": len(laps), "stints": len(stints), "positions": len(positions)})

        context_summary: list[dict[str, int]] = []
        for item in _bounded_candidates(matched_sessions, context_cached, limit=telemetry_limit):
            race_control = parse_race_control(await client._get("race_control", session_key=item.session_key))
            intervals = parse_intervals(await client._get("intervals", session_key=item.session_key))
            pits = parse_pit_stops(await client._get("pit", session_key=item.session_key))
            weather = parse_weather(await client._get("weather", session_key=item.session_key))
            async with SessionLocal() as db:
                async with db.begin():
                    driver_map = await driver_entity_map(db, session_ids[item.session_key])
                    rc = await upsert_race_control(db, session_id=session_ids[item.session_key], session_key=item.session_key, rows=race_control, drivers=driver_map)
                    iv = await upsert_intervals(db, session_id=session_ids[item.session_key], session_key=item.session_key, rows=intervals, drivers=driver_map)
                    pt = await upsert_pit_stops(db, session_id=session_ids[item.session_key], session_key=item.session_key, rows=pits, drivers=driver_map)
                    wt = await upsert_weather(db, session_id=session_ids[item.session_key], session_key=item.session_key, rows=weather)
                    await _audit(db, dataset="race_context", season=season, records_seen=len(race_control) + len(intervals) + len(pits) + len(weather), records_written=rc + iv + pt + wt, metadata={"session_key": item.session_key, "session_code": item.session_code, "race_control": rc, "intervals": iv, "pit_stops": pt, "weather": wt})
            context_summary.append({"session_key": item.session_key, "race_control": len(race_control), "intervals": len(intervals), "pit_stops": len(pits), "weather": len(weather)})
    return {"season": season, "meetings_seen": len(meetings), "meetings_matched": len(matches), "sessions_seen": len(provider_sessions), "sessions_matched": len(session_ids), "fetched_result_session_keys": fetched_session_keys, "cached_result_session_keys": sorted(reused_keys), "session_entries_written": entries_written, "session_results_written": results_written, "unresolved_session_entries": unresolved_entries, "canonicalized_driver_names": canonicalized_driver_names, "starting_grid_sessions": grid_summary, "telemetry_sessions": telemetry_summary, "race_context_sessions": context_summary}


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync race-weekend sessions from OpenF1")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--telemetry-limit", type=int, default=2, help="Maximum completed sessions to fetch telemetry, grid and race context for per run")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(sync_openf1(args.season, telemetry_limit=args.telemetry_limit)), indent=2))


if __name__ == "__main__":
    main()
