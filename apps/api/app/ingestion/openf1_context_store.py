from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.openf1_context import OpenF1Interval, OpenF1PitStop, OpenF1RaceControlEvent, OpenF1Weather

PROVIDER = "openf1"


async def context_loaded_session_keys(session: AsyncSession, season: int) -> set[int]:
    result = await session.execute(text("""
        SELECT DISTINCT rs.provider_session_id FROM race_sessions rs JOIN races r ON r.id=rs.race_id
        WHERE r.season=:season AND rs.provider=:provider AND (
          EXISTS (SELECT 1 FROM session_race_control_events x WHERE x.session_id=rs.id) OR
          EXISTS (SELECT 1 FROM session_intervals x WHERE x.session_id=rs.id) OR
          EXISTS (SELECT 1 FROM session_pit_stops x WHERE x.session_id=rs.id) OR
          EXISTS (SELECT 1 FROM session_weather x WHERE x.session_id=rs.id))
    """), {"season": season, "provider": PROVIDER})
    return {int(value) for value in result.scalars().all()}


async def upsert_race_control(session: AsyncSession, *, session_id: Any, session_key: int, rows: list[OpenF1RaceControlEvent], drivers: dict[int, Any | None]) -> int:
    fetched_at = datetime.now(UTC)
    for row in rows:
        await session.execute(text("""
          INSERT INTO session_race_control_events (session_id,driver_entity_id,provider,provider_session_key,provider_driver_number,observed_at,category,flag,scope,message,lap_number,sector,source_url,source_timestamp,fetched_at,raw_payload)
          VALUES (:session_id,:driver_entity_id,:provider,:session_key,:driver_number,:observed_at,:category,:flag,:scope,:message,:lap_number,:sector,:source_url,:observed_at,:fetched_at,CAST(:raw AS jsonb))
          ON CONFLICT (provider,provider_session_key,observed_at,message) DO UPDATE SET driver_entity_id=EXCLUDED.driver_entity_id,category=EXCLUDED.category,flag=EXCLUDED.flag,scope=EXCLUDED.scope,lap_number=EXCLUDED.lap_number,sector=EXCLUDED.sector,fetched_at=EXCLUDED.fetched_at,raw_payload=EXCLUDED.raw_payload
        """), {"session_id":session_id,"driver_entity_id":drivers.get(row.driver_number) if row.driver_number is not None else None,"provider":PROVIDER,"session_key":session_key,"driver_number":row.driver_number,"observed_at":row.observed_at,"category":row.category,"flag":row.flag,"scope":row.scope,"message":row.message,"lap_number":row.lap_number,"sector":row.sector,"source_url":f"https://api.openf1.org/v1/race_control?session_key={session_key}","fetched_at":fetched_at,"raw":json.dumps(row.raw_payload)})
    return len(rows)


async def upsert_intervals(session: AsyncSession, *, session_id: Any, session_key: int, rows: list[OpenF1Interval], drivers: dict[int, Any | None]) -> int:
    fetched_at=datetime.now(UTC)
    for row in rows:
        await session.execute(text("""INSERT INTO session_intervals (session_id,driver_entity_id,provider,provider_session_key,provider_driver_number,observed_at,interval_seconds,interval_text,gap_to_leader_seconds,gap_to_leader_text,source_url,source_timestamp,fetched_at,raw_payload) VALUES (:session_id,:driver_entity_id,:provider,:session_key,:driver_number,:observed_at,:interval_seconds,:interval_text,:gap_seconds,:gap_text,:source_url,:observed_at,:fetched_at,CAST(:raw AS jsonb)) ON CONFLICT (provider,provider_session_key,provider_driver_number,observed_at) DO UPDATE SET driver_entity_id=EXCLUDED.driver_entity_id,interval_seconds=EXCLUDED.interval_seconds,interval_text=EXCLUDED.interval_text,gap_to_leader_seconds=EXCLUDED.gap_to_leader_seconds,gap_to_leader_text=EXCLUDED.gap_to_leader_text,fetched_at=EXCLUDED.fetched_at,raw_payload=EXCLUDED.raw_payload"""), {"session_id":session_id,"driver_entity_id":drivers.get(row.driver_number),"provider":PROVIDER,"session_key":session_key,"driver_number":row.driver_number,"observed_at":row.observed_at,"interval_seconds":row.interval_seconds,"interval_text":row.interval_text,"gap_seconds":row.gap_to_leader_seconds,"gap_text":row.gap_to_leader_text,"source_url":f"https://api.openf1.org/v1/intervals?session_key={session_key}","fetched_at":fetched_at,"raw":json.dumps(row.raw_payload)})
    return len(rows)


async def upsert_pit_stops(session: AsyncSession, *, session_id: Any, session_key: int, rows: list[OpenF1PitStop], drivers: dict[int, Any | None]) -> int:
    fetched_at=datetime.now(UTC)
    for row in rows:
        await session.execute(text("""INSERT INTO session_pit_stops (session_id,driver_entity_id,provider,provider_session_key,provider_driver_number,lap_number,observed_at,lane_duration_seconds,stop_duration_seconds,source_url,source_timestamp,fetched_at,raw_payload) VALUES (:session_id,:driver_entity_id,:provider,:session_key,:driver_number,:lap_number,:observed_at,:lane_duration,:stop_duration,:source_url,:observed_at,:fetched_at,CAST(:raw AS jsonb)) ON CONFLICT (provider,provider_session_key,provider_driver_number,lap_number) DO UPDATE SET driver_entity_id=EXCLUDED.driver_entity_id,observed_at=EXCLUDED.observed_at,lane_duration_seconds=EXCLUDED.lane_duration_seconds,stop_duration_seconds=EXCLUDED.stop_duration_seconds,fetched_at=EXCLUDED.fetched_at,raw_payload=EXCLUDED.raw_payload"""), {"session_id":session_id,"driver_entity_id":drivers.get(row.driver_number),"provider":PROVIDER,"session_key":session_key,"driver_number":row.driver_number,"lap_number":row.lap_number,"observed_at":row.observed_at,"lane_duration":row.lane_duration_seconds,"stop_duration":row.stop_duration_seconds,"source_url":f"https://api.openf1.org/v1/pit?session_key={session_key}","fetched_at":fetched_at,"raw":json.dumps(row.raw_payload)})
    return len(rows)


async def upsert_weather(session: AsyncSession, *, session_id: Any, session_key: int, rows: list[OpenF1Weather]) -> int:
    fetched_at=datetime.now(UTC)
    for row in rows:
        await session.execute(text("""INSERT INTO session_weather (session_id,provider,provider_session_key,observed_at,air_temperature_c,track_temperature_c,humidity_percent,pressure_mbar,rainfall,wind_direction_degrees,wind_speed_mps,source_url,source_timestamp,fetched_at,raw_payload) VALUES (:session_id,:provider,:session_key,:observed_at,:air,:track,:humidity,:pressure,:rainfall,:wind_direction,:wind_speed,:source_url,:observed_at,:fetched_at,CAST(:raw AS jsonb)) ON CONFLICT (provider,provider_session_key,observed_at) DO UPDATE SET air_temperature_c=EXCLUDED.air_temperature_c,track_temperature_c=EXCLUDED.track_temperature_c,humidity_percent=EXCLUDED.humidity_percent,pressure_mbar=EXCLUDED.pressure_mbar,rainfall=EXCLUDED.rainfall,wind_direction_degrees=EXCLUDED.wind_direction_degrees,wind_speed_mps=EXCLUDED.wind_speed_mps,fetched_at=EXCLUDED.fetched_at,raw_payload=EXCLUDED.raw_payload"""), {"session_id":session_id,"provider":PROVIDER,"session_key":session_key,"observed_at":row.observed_at,"air":row.air_temperature_c,"track":row.track_temperature_c,"humidity":row.humidity_percent,"pressure":row.pressure_mbar,"rainfall":row.rainfall,"wind_direction":row.wind_direction_degrees,"wind_speed":row.wind_speed_mps,"source_url":f"https://api.openf1.org/v1/weather?session_key={session_key}","fetched_at":fetched_at,"raw":json.dumps(row.raw_payload)})
    return len(rows)
