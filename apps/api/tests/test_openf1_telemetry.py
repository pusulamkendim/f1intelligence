from app.ingestion.openf1_telemetry import parse_laps, parse_locations, parse_positions, parse_stints


def test_parse_laps_preserves_provider_identity_and_richer_context() -> None:
    rows = parse_laps([{"session_key": 999, "driver_number": 4, "lap_number": 12, "lap_duration": 81.234, "is_pit_out_lap": False, "date_start": "2026-09-13T12:10:00Z", "duration_sector_1": 25.1, "duration_sector_2": 30.2, "duration_sector_3": 25.934, "i1_speed": 301, "i2_speed": 287, "st_speed": 322, "segments_sector_1": [2049, 2051]}])
    assert rows[0].session_key == 999
    assert rows[0].lap_number == 12
    assert rows[0].sector_2_duration_seconds == 30.2
    assert rows[0].st_speed_kph == 322
    assert rows[0].segments_sector_1 == [2049, 2051]
    assert rows[0].raw_payload["lap_duration"] == 81.234


def test_parse_stints_keeps_tyre_context() -> None:
    rows = parse_stints([{"session_key": 999, "driver_number": 81, "stint_number": 2, "lap_start": 19, "lap_end": 37, "compound": "HARD", "tyre_age_at_start": 3}])
    assert rows[0].compound == "HARD"
    assert rows[0].tyre_age_at_start == 3


def test_parse_positions_requires_timestamp_and_position() -> None:
    rows = parse_positions([{"session_key": 999, "driver_number": 1, "date": "2026-09-13T12:30:01Z", "position": 2}, {"session_key": 999, "driver_number": 4, "position": 3}])
    assert len(rows) == 1
    assert rows[0].position == 2
    assert rows[0].observed_at.tzinfo is not None



def test_parse_locations_downsamples_each_driver_independently() -> None:
    rows = parse_locations(
        [
            {
                "session_key": 999,
                "driver_number": 1,
                "date": "2026-09-13T12:30:00.000Z",
                "x": 100,
                "y": 200,
                "z": 10,
            },
            {
                "session_key": 999,
                "driver_number": 1,
                "date": "2026-09-13T12:30:00.300Z",
                "x": 110,
                "y": 210,
                "z": 11,
            },
            {
                "session_key": 999,
                "driver_number": 4,
                "date": "2026-09-13T12:30:00.400Z",
                "x": 500,
                "y": 600,
                "z": 20,
            },
            {
                "session_key": 999,
                "driver_number": 1,
                "date": "2026-09-13T12:30:01.100Z",
                "x": 130,
                "y": 230,
                "z": 13,
            },
        ],
        sample_interval_ms=1000,
    )

    assert [(row.driver_number, row.x, row.y) for row in rows] == [
        (1, 100, 200),
        (1, 130, 230),
        (4, 500, 600),
    ]
    assert rows[0].observed_at.tzinfo is not None
