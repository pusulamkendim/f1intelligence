from datetime import UTC, datetime

from app.ingestion.openf1_overtakes import parse_overtakes


def test_parse_overtakes_preserves_provider_event_identity() -> None:
    rows = parse_overtakes(
        [
            {
                "date": "2024-11-03T15:50:07.565000+00:00",
                "meeting_key": 1249,
                "overtaken_driver_number": 4,
                "overtaking_driver_number": 63,
                "position": 1,
                "session_key": 9636,
            }
        ]
    )

    assert len(rows) == 1
    assert rows[0].session_key == 9636
    assert rows[0].meeting_key == 1249
    assert rows[0].overtaking_driver_number == 63
    assert rows[0].overtaken_driver_number == 4
    assert rows[0].position == 1
    assert rows[0].observed_at == datetime(2024, 11, 3, 15, 50, 7, 565000, tzinfo=UTC)
    assert rows[0].raw_payload["position"] == 1


def test_parse_overtakes_skips_incomplete_rows() -> None:
    rows = parse_overtakes(
        [
            {
                "meeting_key": 1249,
                "overtaken_driver_number": 4,
                "overtaking_driver_number": 63,
                "position": 1,
                "session_key": 9636,
            },
            {
                "date": "2024-11-03T15:50:07+00:00",
                "meeting_key": 1249,
                "overtaking_driver_number": 63,
                "position": 1,
                "session_key": 9636,
            },
        ]
    )

    assert rows == []
