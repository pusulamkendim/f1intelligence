from app.ingestion.openf1_context import parse_intervals, parse_pit_stops, parse_race_control, parse_weather


def test_parse_race_control_preserves_flag_context() -> None:
    rows = parse_race_control([{"session_key": 99, "date": "2026-09-13T13:10:00Z", "category": "Flag", "flag": "DOUBLE YELLOW", "scope": "Sector", "sector": 8, "lap_number": 12, "message": "DOUBLE YELLOW IN TRACK SECTOR 8"}])
    assert rows[0].flag == "DOUBLE YELLOW"
    assert rows[0].driver_number is None
    assert rows[0].observed_at.tzinfo is not None


def test_parse_intervals_preserves_lapped_text() -> None:
    rows = parse_intervals([{"session_key": 99, "driver_number": 4, "date": "2026-09-13T13:20:00Z", "interval": 1.234, "gap_to_leader": "+1 LAP"}])
    assert rows[0].interval_seconds == 1.234
    assert rows[0].gap_to_leader_seconds is None
    assert rows[0].gap_to_leader_text == "+1 LAP"


def test_parse_pit_uses_lane_duration_not_deprecated_pit_duration() -> None:
    rows = parse_pit_stops([{"session_key": 99, "driver_number": 81, "lap_number": 27, "date": "2026-09-13T13:40:00Z", "lane_duration": 21.9, "pit_duration": 99.0, "stop_duration": 2.2}])
    assert rows[0].lane_duration_seconds == 21.9
    assert rows[0].stop_duration_seconds == 2.2


def test_parse_weather_keeps_track_conditions() -> None:
    rows = parse_weather([{"session_key": 99, "date": "2026-09-13T13:00:00Z", "air_temperature": 24.1, "track_temperature": 38.2, "humidity": 54, "pressure": 1012.4, "rainfall": 0, "wind_direction": 180, "wind_speed": 3.5}])
    assert rows[0].track_temperature_c == 38.2
    assert rows[0].rainfall is False
