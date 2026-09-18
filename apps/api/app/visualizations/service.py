from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.visualizations import VisualizationResponse
from app.visualizations.series import lap_time_series, position_series, stint_series

Chart = Literal["positions", "lap-times", "stints", "sectors", "speeds", "intervals", "pit-stops", "weather", "overtakes", "starting-grid"]


class VisualizationNotFoundError(ValueError):
    pass


async def _session(session: AsyncSession, race_key: str, session_code: str) -> dict[str, Any]:
    result = await session.execute(text("""
        SELECT rs.id, rs.session_name, rs.source_url, rs.fetched_at, r.official_name
        FROM race_sessions rs JOIN races r ON r.id=rs.race_id
        WHERE (r.slug=:race_key OR r.id::text=:race_key) AND rs.session_code=:session_code
        LIMIT 1
    """), {"race_key": race_key, "session_code": session_code})
    row = result.mappings().first()
    if not row:
        raise VisualizationNotFoundError(f"race/session not found: {race_key}/{session_code}")
    return dict(row)


async def _driver_rows(session: AsyncSession, session_id: Any, table: str, columns: str) -> list[dict[str, Any]]:
    if table not in {"session_laps", "session_stints"}:
        raise ValueError("unsupported visualization table")
    result = await session.execute(text(f"""
        SELECT {columns}, e.slug AS driver_key, e.display_name AS driver_label,
               te.slug AS team_key, COALESCE(te.display_name, se.team_name) AS team_label,
               se.team_colour AS team_color
        FROM {table} d
        JOIN session_entries se ON se.session_id=d.session_id AND se.driver_number=d.provider_driver_number
        LEFT JOIN entities e ON e.id=COALESCE(d.driver_entity_id, se.driver_entity_id)
        LEFT JOIN entities te ON te.id=se.team_entity_id
        WHERE d.session_id=:session_id AND e.id IS NOT NULL
    """), {"session_id": session_id})
    return [dict(row) for row in result.mappings().all()]


async def _position_rows(session: AsyncSession, session_id: Any) -> list[dict[str, Any]]:
    result = await session.execute(text("""
        WITH lap_boundaries AS (
          SELECT provider_driver_number, lap_number, started_at,
                 lead(started_at) OVER (PARTITION BY provider_driver_number ORDER BY lap_number) AS next_lap_at
          FROM session_laps WHERE session_id=:session_id AND started_at IS NOT NULL
        )
        SELECT lb.lap_number, p.position, e.slug AS driver_key, e.display_name AS driver_label,
               te.slug AS team_key, COALESCE(te.display_name, se.team_name) AS team_label, se.team_colour AS team_color
        FROM lap_boundaries lb
        JOIN session_entries se ON se.session_id=:session_id AND se.driver_number=lb.provider_driver_number
        LEFT JOIN entities e ON e.id=se.driver_entity_id LEFT JOIN entities te ON te.id=se.team_entity_id
        JOIN LATERAL (
          SELECT position FROM session_positions p
          WHERE p.session_id=:session_id AND p.provider_driver_number=lb.provider_driver_number
            AND p.observed_at >= lb.started_at AND (lb.next_lap_at IS NULL OR p.observed_at < lb.next_lap_at)
          ORDER BY p.observed_at DESC LIMIT 1
        ) p ON true WHERE e.id IS NOT NULL ORDER BY lb.lap_number, e.slug
    """), {"session_id": session_id})
    return [dict(row) for row in result.mappings().all()]


async def _annotations(session: AsyncSession, session_id: Any) -> list[dict[str, Any]]:
    result = await session.execute(text("""
        SELECT id::text, category, COALESCE(message, flag, category) AS label, lap_number, observed_at, flag, scope
        FROM session_race_control_events WHERE session_id=:session_id ORDER BY observed_at, id
    """), {"session_id": session_id})
    return [{"id": row["id"], "type": row["category"], "label": row["label"], "lap": row["lap_number"],
             "occurred_at": row["observed_at"].isoformat() if row["observed_at"] else None,
             "metadata": {"flag": row["flag"], "scope": row["scope"]}} for row in result.mappings().all()]


async def race_visualization(session: AsyncSession, race_key: str, session_code: str, chart: Chart) -> VisualizationResponse:
    context = await _session(session, race_key, session_code)
    if chart == "positions":
        series = position_series(await _position_rows(session, context["id"]))
        x_axis, y_axis = "lap", "position"
    elif chart == "lap-times":
        rows = await _driver_rows(session, context["id"], "session_laps", "d.lap_number, d.lap_duration_seconds")
        series = lap_time_series(rows); x_axis, y_axis = "lap", "seconds"
    else:
        rows = await _driver_rows(session, context["id"], "session_stints", "d.stint_number, d.lap_start, d.lap_end, d.compound, d.tyre_age_at_start")
        series = stint_series(rows); x_axis, y_axis = "lap", "stint"
    return VisualizationResponse(
        key=f"{race_key}:{session_code}:{chart}", chart_type="timeline" if chart == "stints" else "line",
        title=f'{context["official_name"]} — {context["session_name"]} — {chart}', x_axis=x_axis, y_axis=y_axis,
        series=series, annotations=await _annotations(session, context["id"]),
        provenance=[{"provider": "openf1", "source_url": context["source_url"],
                     "fetched_at": context["fetched_at"].isoformat() if context["fetched_at"] else None,
                     "datasets": [chart, "race_control"]}],
    )


async def _extra_series(session: AsyncSession, session_id: Any, chart: Chart) -> tuple[list[dict[str, Any]], str, str]:
    if chart in {"sectors", "speeds"}:
        cols = "d.lap_number, d.sector_1_duration_seconds, d.sector_2_duration_seconds, d.sector_3_duration_seconds, d.i1_speed_kph, d.i2_speed_kph, d.st_speed_kph"
        rows = await _driver_rows(session, session_id, "session_laps", cols)
        fields = (("sector_1_duration_seconds", "S1"), ("sector_2_duration_seconds", "S2"), ("sector_3_duration_seconds", "S3")) if chart == "sectors" else (("i1_speed_kph", "I1"), ("i2_speed_kph", "I2"), ("st_speed_kph", "Speed trap"))
        unit = "seconds" if chart == "sectors" else "kph"
        return [{"key": field, "label": label, "unit": unit, "points": [{"lap": int(r["lap_number"]), "value": float(r[field])} for r in rows if r.get(field) is not None]} for field, label in fields], "lap", unit
    table_map = {"intervals": ("session_intervals", "d.observed_at, d.gap_to_leader_seconds, d.interval_seconds"), "pit-stops": ("session_pit_stops", "d.lap_number, d.stop_duration_seconds, d.lane_duration_seconds")}
    if chart in table_map:
        table, cols = table_map[chart]
        rows = await _driver_rows(session, session_id, table, cols)
        fields = (("gap_to_leader_seconds", "Gap to leader"), ("interval_seconds", "Interval")) if chart == "intervals" else (("stop_duration_seconds", "Stop"), ("lane_duration_seconds", "Pit lane"))
        x = "observed_at" if chart == "intervals" else "lap_number"
        return [{"key": field, "label": label, "unit": "seconds", "points": [{"x": r[x].isoformat() if hasattr(r[x], "isoformat") else r[x], "value": float(r[field])} for r in rows if r.get(field) is not None]} for field, label in fields], "timestamp" if chart == "intervals" else "lap", "seconds"
    if chart == "weather":
        result = await session.execute(text("SELECT observed_at,air_temperature_c,track_temperature_c,humidity_percent,pressure_mbar,wind_speed_mps,rainfall FROM session_weather WHERE session_id=:session_id ORDER BY observed_at"), {"session_id": session_id})
        rows = [dict(r) for r in result.mappings().all()]
        fields = (("air_temperature_c","Air temperature","celsius"),("track_temperature_c","Track temperature","celsius"),("humidity_percent","Humidity","percent"),("pressure_mbar","Pressure","mbar"),("wind_speed_mps","Wind speed","mps"),("rainfall","Rainfall","boolean"))
        return [{"key": k,"label": label,"unit": unit,"points": [{"timestamp": r["observed_at"].isoformat(),"value": r[k]} for r in rows if r[k] is not None]} for k,label,unit in fields], "timestamp", "mixed"
    if chart == "overtakes":
        result = await session.execute(text("SELECT o.observed_at,o.position,a.display_name AS overtaker,b.display_name AS overtaken FROM session_overtakes o LEFT JOIN entities a ON a.id=o.overtaking_driver_entity_id LEFT JOIN entities b ON b.id=o.overtaken_driver_entity_id WHERE o.session_id=:session_id ORDER BY o.observed_at"), {"session_id": session_id})
        points = [{"timestamp": r["observed_at"].isoformat(),"position": r["position"],"overtaker": r["overtaker"],"overtaken": r["overtaken"]} for r in result.mappings().all()]
        return [{"key":"overtakes","label":"Overtakes","unit":"event","points":points}], "timestamp", "event"
    result = await session.execute(text("SELECT g.position,e.display_name AS driver,te.display_name AS team,g.qualifying_lap_duration_seconds FROM session_starting_grid g LEFT JOIN entities e ON e.id=g.driver_entity_id LEFT JOIN entities te ON te.id=g.team_entity_id WHERE g.session_id=:session_id ORDER BY g.position"), {"session_id": session_id})
    points = [{"position": r["position"],"driver": r["driver"],"team": r["team"],"qualifying_seconds": r["qualifying_lap_duration_seconds"]} for r in result.mappings().all()]
    return [{"key":"starting-grid","label":"Starting grid","unit":"position","points":points}], "position", "position"
