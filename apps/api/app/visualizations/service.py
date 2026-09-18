from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.visualizations import VisualizationResponse
from app.visualizations.series import (
    interval_series,
    lap_time_series,
    normalize_team_color,
    pit_stop_series,
    position_series,
    sector_series,
    segment_series,
    speed_series,
    stint_series,
    tyre_semantic_token,
)

Chart = Literal[
    "positions",
    "lap-times",
    "stints",
    "sectors",
    "speeds",
    "intervals",
    "pit-stops",
    "weather",
    "overtakes",
    "starting-grid",
    "segments",
    "timing-tower",
    "session-result",
]

CLASSIC_F1_TOKENS = {
    "timing-purple": "#B14CFF",
    "timing-green": "#39E75F",
    "timing-yellow": "#FFD60A",
    "tyre-soft": "#FF3B30",
    "tyre-medium": "#FFD60A",
    "tyre-hard": "#F2F2F2",
    "tyre-intermediate": "#34C759",
    "tyre-wet": "#0A84FF",
    "flag-red": "#FF3B30",
    "flag-yellow": "#FFD60A",
    "flag-green": "#34C759",
    "flag-blue": "#0A84FF",
    "flag-chequered": "#F2F2F2",
    "safety-car": "#FFD60A",
    "virtual-safety-car": "#FFD60A",
    "drs": "#39E75F",
    "pit-lane": "#8E8E93",
    "segment-unavailable": "#4A4A4A",
    "segment-unknown": "#6E6E73",
}

CLASSIC_COLUMNS: dict[str, list[dict[str, Any]]] = {
    "sector-timing": [
        {"key": "driver_acronym", "label": "DRIVER", "align": "left"},
        {"key": "lap", "label": "LAP", "formatter": "integer"},
        {"key": "s1_seconds", "label": "S1", "formatter": "lap-time", "status_key": "s1_status"},
        {"key": "s2_seconds", "label": "S2", "formatter": "lap-time", "status_key": "s2_status"},
        {"key": "s3_seconds", "label": "S3", "formatter": "lap-time", "status_key": "s3_status"},
    ],
    "speed-comparison": [
        {"key": "driver_acronym", "label": "DRIVER", "align": "left"},
        {"key": "lap", "label": "LAP", "formatter": "integer"},
        {"key": "i1_kph", "label": "I1", "formatter": "speed"},
        {"key": "i2_kph", "label": "I2", "formatter": "speed"},
        {"key": "speed_trap_kph", "label": "ST", "formatter": "speed"},
    ],
    "stint-strategy": [
        {"key": "driver_acronym", "label": "DRIVER", "align": "left"},
        {"key": "compound", "label": "TYRE", "align": "center"},
        {"key": "lap_start", "label": "FROM", "formatter": "integer"},
        {"key": "lap_end", "label": "TO", "formatter": "integer"},
        {"key": "tyre_age_at_start", "label": "AGE", "formatter": "integer"},
    ],
    "pit-stop": [
        {"key": "driver_acronym", "label": "DRIVER", "align": "left"},
        {"key": "lap", "label": "LAP", "formatter": "integer"},
        {"key": "stop_seconds", "label": "STOP", "formatter": "delta"},
        {"key": "pit_lane_seconds", "label": "PIT LANE", "formatter": "delta"},
    ],
    "starting-grid": [
        {"key": "position", "label": "POS", "formatter": "position"},
        {"key": "driver_acronym", "label": "DRIVER", "align": "left"},
        {"key": "team", "label": "TEAM", "align": "left"},
        {"key": "qualifying_seconds", "label": "TIME", "formatter": "lap-time"},
    ],
    "race-classification": [
        {"key": "position", "label": "POS", "formatter": "position"},
        {"key": "driver_acronym", "label": "DRIVER", "align": "left"},
        {"key": "team_label", "label": "TEAM", "align": "left"},
        {"key": "grid_position", "label": "GRID", "formatter": "position"},
        {"key": "finish_time", "label": "TIME / GAP", "align": "right"},
        {"key": "points", "label": "PTS", "formatter": "raw"},
    ],
    "qualifying-classification": [
        {"key": "position", "label": "POS", "formatter": "position"},
        {"key": "driver_acronym", "label": "DRIVER", "align": "left"},
        {"key": "team_label", "label": "TEAM", "align": "left"},
        {"key": "q1", "label": "Q1", "formatter": "lap-time"},
        {"key": "q2", "label": "Q2", "formatter": "lap-time"},
        {"key": "q3", "label": "Q3", "formatter": "lap-time"},
    ],
    "championship-standings": [
        {"key": "position", "label": "POS", "formatter": "position"},
        {"key": "driver_acronym", "label": "DRIVER", "align": "left"},
        {"key": "team_label", "label": "TEAM", "align": "left"},
        {"key": "points", "label": "PTS", "formatter": "raw"},
        {"key": "wins", "label": "WINS", "formatter": "integer"},
    ],
    "driver-season-results": [
        {"key": "round", "label": "RD", "formatter": "integer"},
        {"key": "race_label", "label": "GRAND PRIX", "align": "left"},
        {"key": "qualifying_position", "label": "QUALI", "formatter": "position"},
        {"key": "grid_position", "label": "GRID", "formatter": "position"},
        {"key": "finish_position", "label": "RACE", "formatter": "position"},
        {"key": "points", "label": "PTS", "formatter": "raw"},
    ],
    "mini-sector-timing": [
        {"key": "driver_acronym", "label": "DRIVER", "align": "left"},
        {"key": "lap", "label": "LAP", "formatter": "integer"},
        {"key": "sector_1", "label": "S1", "formatter": "segments"},
        {"key": "sector_2", "label": "S2", "formatter": "segments"},
        {"key": "sector_3", "label": "S3", "formatter": "segments"},
    ],
    "timing-tower": [
        {"key": "position", "label": "POS", "formatter": "position"},
        {"key": "driver_acronym", "label": "DRIVER", "align": "left"},
        {"key": "gap", "label": "GAP", "formatter": "delta"},
        {"key": "interval", "label": "INT", "formatter": "delta"},
        {"key": "last_lap_seconds", "label": "LAST LAP", "formatter": "lap-time"},
        {"key": "compound", "label": "TYRE", "align": "center"},
        {"key": "tyre_age", "label": "AGE", "formatter": "integer"},
    ],
    "session-classification": [
        {"key": "position", "label": "POS", "formatter": "position"},
        {"key": "driver_acronym", "label": "DRIVER", "align": "left"},
        {"key": "gap", "label": "GAP", "align": "right"},
        {"key": "duration_seconds", "label": "TIME", "formatter": "lap-time"},
        {"key": "number_of_laps", "label": "LAPS", "formatter": "integer"},
        {"key": "status", "label": "STATUS", "align": "left"},
    ],
}


class VisualizationNotFoundError(ValueError):
    pass


async def _session(session: AsyncSession, race_key: str, session_code: str) -> dict[str, Any]:
    result = await session.execute(
        text(
            """
            SELECT rs.id, rs.session_name, rs.source_url, rs.fetched_at,
                   r.official_name
            FROM race_sessions rs
            JOIN races r ON r.id = rs.race_id
            WHERE (r.slug = :race_key OR r.id::text = :race_key)
              AND rs.session_code = :session_code
            LIMIT 1
            """
        ),
        {"race_key": race_key, "session_code": session_code},
    )
    row = result.mappings().first()
    if not row:
        raise VisualizationNotFoundError(
            f"race/session not found: {race_key}/{session_code}"
        )
    return dict(row)


async def _driver_rows(
    session: AsyncSession,
    session_id: Any,
    table: str,
    columns: str,
) -> list[dict[str, Any]]:
    allowed = {
        "session_laps",
        "session_stints",
        "session_intervals",
        "session_pit_stops",
    }
    if table not in allowed:
        raise ValueError("unsupported visualization table")
    result = await session.execute(
        text(
            f"""
            SELECT {columns},
                   e.slug AS driver_key,
                   e.display_name AS driver_label,
                   se.driver_number,
                   se.name_acronym AS driver_acronym,
                   te.slug AS team_key,
                   COALESCE(te.display_name, se.team_name) AS team_label,
                   se.team_colour AS team_color
            FROM {table} d
            JOIN session_entries se
              ON se.session_id = d.session_id
             AND se.driver_number = d.provider_driver_number
            LEFT JOIN entities e
              ON e.id = COALESCE(d.driver_entity_id, se.driver_entity_id)
            LEFT JOIN entities te ON te.id = se.team_entity_id
            WHERE d.session_id = :session_id
              AND e.id IS NOT NULL
            """
        ),
        {"session_id": session_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def _position_rows(
    session: AsyncSession,
    session_id: Any,
) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            """
            WITH lap_boundaries AS (
                SELECT provider_driver_number, lap_number, started_at,
                       lead(started_at) OVER (
                           PARTITION BY provider_driver_number
                           ORDER BY lap_number
                       ) AS next_lap_at
                FROM session_laps
                WHERE session_id = :session_id
                  AND started_at IS NOT NULL
            )
            SELECT lb.lap_number,
                   p.position,
                   e.slug AS driver_key,
                   e.display_name AS driver_label,
                   se.driver_number,
                   se.name_acronym AS driver_acronym,
                   te.slug AS team_key,
                   COALESCE(te.display_name, se.team_name) AS team_label,
                   se.team_colour AS team_color
            FROM lap_boundaries lb
            JOIN session_entries se
              ON se.session_id = :session_id
             AND se.driver_number = lb.provider_driver_number
            LEFT JOIN entities e ON e.id = se.driver_entity_id
            LEFT JOIN entities te ON te.id = se.team_entity_id
            JOIN LATERAL (
                SELECT position
                FROM session_positions p
                WHERE p.session_id = :session_id
                  AND p.provider_driver_number = lb.provider_driver_number
                  AND p.observed_at >= lb.started_at
                  AND (
                      lb.next_lap_at IS NULL
                      OR p.observed_at < lb.next_lap_at
                  )
                ORDER BY p.observed_at DESC
                LIMIT 1
            ) p ON true
            WHERE e.id IS NOT NULL
            ORDER BY lb.lap_number, e.slug
            """
        ),
        {"session_id": session_id},
    )
    return [dict(row) for row in result.mappings().all()]


def _annotation_token(row: Any) -> str | None:
    flag = (row.get("flag") or "").upper()
    category = (row.get("category") or "").upper()
    message = (row.get("label") or "").upper()
    combined = f"{category} {message}"

    if "CHEQUERED" in flag or "CHECKERED" in flag:
        return "flag-chequered"
    if flag == "RED":
        return "flag-red"
    if "YELLOW" in flag:
        return "flag-yellow"
    if "GREEN" in flag:
        return "flag-green"
    if "BLUE" in flag:
        return "flag-blue"
    if "VIRTUAL SAFETY CAR" in combined or "VSC" in combined:
        return "virtual-safety-car"
    if "SAFETY CAR" in combined:
        return "safety-car"
    if "DRS" in combined:
        return "drs"
    return None


async def _annotations(
    session: AsyncSession,
    session_id: Any,
) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            """
            SELECT id::text,
                   category,
                   COALESCE(message, flag, category) AS label,
                   lap_number,
                   observed_at,
                   flag,
                   scope,
                   sector
            FROM session_race_control_events
            WHERE session_id = :session_id
            ORDER BY observed_at, id
            """
        ),
        {"session_id": session_id},
    )
    rows = result.mappings().all()
    return [
        {
            "id": row["id"],
            "type": row["category"] or "race_control",
            "label": row["label"],
            "lap": row["lap_number"],
            "occurred_at": row["observed_at"].isoformat()
            if row["observed_at"]
            else None,
            "semantic_token": _annotation_token(row),
            "metadata": {
                "flag": row["flag"],
                "scope": row["scope"],
                "sector": row["sector"],
            },
        }
        for row in rows
    ]


def _axis(
    key: str,
    label: str,
    *,
    unit: str | None = None,
    direction: str = "normal",
    formatter: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "unit": unit,
        "direction": direction,
        "formatter": formatter,
        "min": min_value,
        "max": max_value,
    }


def _presentation(
    preset: str,
    *,
    show_legend: bool = True,
    show_annotations: bool = True,
) -> dict[str, Any]:
    return {
        "preset": preset,
        "dense": True,
        "dark_preferred": True,
        "driver_label_mode": "acronym",
        "show_legend": show_legend,
        "show_annotations": show_annotations,
        "columns": CLASSIC_COLUMNS.get(preset, []),
        "semantic_tokens": CLASSIC_F1_TOKENS,
    }


async def _weather_series(
    session: AsyncSession,
    session_id: Any,
) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            """
            SELECT observed_at,
                   air_temperature_c,
                   track_temperature_c,
                   humidity_percent,
                   pressure_mbar,
                   wind_speed_mps,
                   wind_direction_degrees,
                   rainfall
            FROM session_weather
            WHERE session_id = :session_id
            ORDER BY observed_at
            """
        ),
        {"session_id": session_id},
    )
    rows = [dict(row) for row in result.mappings().all()]
    fields = (
        ("air_temperature_c", "Air temperature", "celsius"),
        ("track_temperature_c", "Track temperature", "celsius"),
        ("humidity_percent", "Humidity", "percent"),
        ("pressure_mbar", "Pressure", "mbar"),
        ("wind_speed_mps", "Wind speed", "mps"),
        ("rainfall", "Rainfall", "boolean"),
    )
    return [
        {
            "key": key,
            "label": label,
            "unit": unit,
            "points": [
                {
                    "timestamp": row["observed_at"].isoformat(),
                    "value": row[key],
                    "wind_direction_degrees": row["wind_direction_degrees"],
                }
                for row in rows
                if row[key] is not None
            ],
        }
        for key, label, unit in fields
    ]


async def _overtake_series(
    session: AsyncSession,
    session_id: Any,
) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            """
            SELECT o.observed_at,
                   o.position,
                   a.slug AS overtaker_key,
                   a.display_name AS overtaker,
                   b.slug AS overtaken_key,
                   b.display_name AS overtaken,
                   se.name_acronym AS overtaker_acronym,
                   se.driver_number AS overtaker_number,
                   se.team_colour AS overtaker_team_color
            FROM session_overtakes o
            LEFT JOIN entities a ON a.id = o.overtaking_driver_entity_id
            LEFT JOIN entities b ON b.id = o.overtaken_driver_entity_id
            LEFT JOIN session_entries se
              ON se.session_id = o.session_id
             AND se.driver_number = o.overtaking_driver_number
            WHERE o.session_id = :session_id
            ORDER BY o.observed_at
            """
        ),
        {"session_id": session_id},
    )
    points = [
        {
            "timestamp": row["observed_at"].isoformat(),
            "position": row["position"],
            "overtaker_key": row["overtaker_key"],
            "overtaker": row["overtaker"],
            "overtaker_acronym": row["overtaker_acronym"],
            "overtaker_number": row["overtaker_number"],
            "overtaker_color": normalize_team_color(row["overtaker_team_color"]),
            "overtaken_key": row["overtaken_key"],
            "overtaken": row["overtaken"],
        }
        for row in result.mappings().all()
    ]
    return [
        {
            "key": "overtakes",
            "label": "Overtakes",
            "unit": "event",
            "points": points,
        }
    ]


async def _starting_grid_series(
    session: AsyncSession,
    session_id: Any,
) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            """
            SELECT g.position,
                   e.slug AS driver_key,
                   e.display_name AS driver,
                   se.name_acronym AS driver_acronym,
                   se.driver_number,
                   te.slug AS team_key,
                   COALESCE(te.display_name, se.team_name) AS team,
                   se.team_colour AS team_color,
                   g.qualifying_lap_duration_seconds
            FROM session_starting_grid g
            LEFT JOIN entities e ON e.id = g.driver_entity_id
            LEFT JOIN entities te ON te.id = g.team_entity_id
            LEFT JOIN session_entries se
              ON se.session_id = g.session_id
             AND se.driver_number = g.provider_driver_number
            WHERE g.session_id = :session_id
            ORDER BY g.position
            """
        ),
        {"session_id": session_id},
    )
    points = [
        {
            "position": row["position"],
            "driver_key": row["driver_key"],
            "driver": row["driver"],
            "driver_acronym": row["driver_acronym"],
            "driver_number": row["driver_number"],
            "team_key": row["team_key"],
            "team": row["team"],
            "color": normalize_team_color(row["team_color"]),
            "qualifying_seconds": row["qualifying_lap_duration_seconds"],
        }
        for row in result.mappings().all()
    ]
    return [
        {
            "key": "starting-grid",
            "label": "Starting grid",
            "unit": "position",
            "points": points,
        }
    ]


async def race_visualization(
    session: AsyncSession,
    race_key: str,
    session_code: str,
    chart: Chart,
) -> VisualizationResponse:
    context = await _session(session, race_key, session_code)
    session_id = context["id"]

    if chart == "positions":
        series = position_series(await _position_rows(session, session_id))
        max_position = max(
            (
                point["position"]
                for item in series
                for point in item["points"]
            ),
            default=None,
        )
        chart_type = "line"
        x_axis = _axis("lap", "Lap", unit="lap", formatter="integer")
        y_axis = _axis(
            "position",
            "Position",
            unit="position",
            direction="reversed",
            formatter="position",
            min_value=1,
            max_value=float(max_position) if max_position else None,
        )
        presentation = _presentation("position-trace")
    elif chart == "lap-times":
        rows = await _driver_rows(
            session,
            session_id,
            "session_laps",
            "d.lap_number, d.lap_duration_seconds, d.is_pit_out_lap",
        )
        series = lap_time_series(rows)
        chart_type = "line"
        x_axis = _axis("lap", "Lap", unit="lap", formatter="integer")
        y_axis = _axis(
            "seconds",
            "Lap time",
            unit="seconds",
            formatter="lap-time",
        )
        presentation = _presentation("lap-times")
    elif chart == "stints":
        rows = await _driver_rows(
            session,
            session_id,
            "session_stints",
            "d.stint_number, d.lap_start, d.lap_end, d.compound, "
            "d.tyre_age_at_start",
        )
        series = stint_series(rows)
        chart_type = "timeline"
        x_axis = _axis("lap", "Lap", unit="lap", formatter="integer")
        y_axis = _axis("driver", "Driver")
        presentation = _presentation("stint-strategy")
    elif chart == "sectors":
        rows = await _driver_rows(
            session,
            session_id,
            "session_laps",
            "d.lap_number, d.sector_1_duration_seconds, "
            "d.sector_2_duration_seconds, d.sector_3_duration_seconds",
        )
        series = sector_series(rows)
        chart_type = "timing_table"
        x_axis = _axis("lap", "Lap", unit="lap", formatter="integer")
        y_axis = _axis(
            "sector_seconds",
            "Sector time",
            unit="seconds",
            formatter="lap-time",
        )
        presentation = _presentation("sector-timing")
    elif chart == "speeds":
        rows = await _driver_rows(
            session,
            session_id,
            "session_laps",
            "d.lap_number, d.i1_speed_kph, d.i2_speed_kph, d.st_speed_kph",
        )
        series = speed_series(rows)
        chart_type = "timing_table"
        x_axis = _axis("lap", "Lap", unit="lap", formatter="integer")
        y_axis = _axis("speed", "Speed", unit="kph", formatter="speed")
        presentation = _presentation("speed-comparison")
    elif chart == "intervals":
        rows = await _driver_rows(
            session,
            session_id,
            "session_intervals",
            "d.observed_at, d.gap_to_leader_seconds, d.interval_seconds, "
            "d.gap_to_leader_text, d.interval_text",
        )
        series = interval_series(rows)
        chart_type = "line"
        x_axis = _axis("timestamp", "Session time", formatter="timestamp")
        y_axis = _axis(
            "seconds",
            "Gap / interval",
            unit="seconds",
            formatter="delta",
        )
        presentation = _presentation("gap-interval")
    elif chart == "pit-stops":
        rows = await _driver_rows(
            session,
            session_id,
            "session_pit_stops",
            "d.lap_number, d.observed_at, d.stop_duration_seconds, "
            "d.lane_duration_seconds",
        )
        series = pit_stop_series(rows)
        chart_type = "bar"
        x_axis = _axis("lap", "Lap", unit="lap", formatter="integer")
        y_axis = _axis(
            "seconds",
            "Pit time",
            unit="seconds",
            formatter="delta",
        )
        presentation = _presentation("pit-stop")
    elif chart == "weather":
        series = await _weather_series(session, session_id)
        chart_type = "multi_panel"
        x_axis = _axis("timestamp", "Session time", formatter="timestamp")
        y_axis = _axis("value", "Weather", formatter="auto")
        presentation = _presentation("weather", show_legend=True)
    elif chart == "overtakes":
        series = await _overtake_series(session, session_id)
        chart_type = "event_stream"
        x_axis = _axis("timestamp", "Session time", formatter="timestamp")
        y_axis = _axis(
            "position",
            "Position",
            unit="position",
            direction="reversed",
            formatter="position",
        )
        presentation = _presentation(
            "overtakes",
            show_legend=False,
        )
    else:
        series = await _starting_grid_series(session, session_id)
        chart_type = "timing_table"
        x_axis = _axis(
            "position",
            "Grid",
            unit="position",
            formatter="position",
        )
        y_axis = _axis("driver", "Driver")
        presentation = _presentation(
            "starting-grid",
            show_annotations=False,
        )

    annotations = (
        await _annotations(session, session_id)
        if presentation["show_annotations"]
        else []
    )
    return VisualizationResponse(
        key=f"{race_key}:{session_code}:{chart}",
        chart_type=chart_type,
        title=f'{context["official_name"]} — {context["session_name"]} — {chart}',
        x_axis=x_axis,
        y_axis=y_axis,
        presentation=presentation,
        series=series,
        annotations=annotations,
        provenance=[
            {
                "provider": "openf1",
                "source_url": context["source_url"],
                "fetched_at": context["fetched_at"].isoformat()
                if context["fetched_at"]
                else None,
                "datasets": [chart, "race_control"],
            }
        ],
    )
