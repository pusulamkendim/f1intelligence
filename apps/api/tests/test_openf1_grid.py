from app.ingestion.openf1_grid import parse_starting_grid


def test_parse_starting_grid_preserves_provider_identity_and_lap_duration() -> None:
    rows = parse_starting_grid(
        [
            {
                "position": 1,
                "driver_number": 1,
                "lap_duration": 76.732,
                "meeting_key": 1143,
                "session_key": 7783,
            },
            {
                "position": 2,
                "driver_number": 63,
                "lap_duration": None,
                "meeting_key": 1143,
                "session_key": 7783,
            },
        ]
    )

    assert len(rows) == 2
    assert rows[0].session_key == 7783
    assert rows[0].meeting_key == 1143
    assert rows[0].driver_number == 1
    assert rows[0].position == 1
    assert rows[0].lap_duration_seconds == 76.732
    assert rows[0].raw_payload["position"] == 1
    assert rows[1].lap_duration_seconds is None


def test_parse_starting_grid_skips_rows_without_driver_or_position() -> None:
    rows = parse_starting_grid(
        [
            {"session_key": 1, "meeting_key": 2, "position": 1},
            {"session_key": 1, "meeting_key": 2, "driver_number": 44},
        ]
    )

    assert rows == []
