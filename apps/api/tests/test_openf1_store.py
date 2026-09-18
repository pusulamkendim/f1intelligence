from datetime import UTC, datetime
from uuid import uuid4

from app.ingestion.openf1 import OpenF1Meeting
from app.ingestion.openf1_store import (
    match_meetings_to_races,
    qualifying_segment_definitions,
)


def _meeting(key: int, date_end: datetime) -> OpenF1Meeting:
    return OpenF1Meeting(
        meeting_key=key,
        year=2026,
        meeting_name="Example Grand Prix",
        meeting_official_name=None,
        circuit_key=None,
        circuit_short_name=None,
        country_name=None,
        location=None,
        date_start=date_end,
        date_end=date_end,
        gmt_offset=None,
        is_cancelled=False,
    )


def test_meeting_matching_uses_weekend_date_and_does_not_double_assign() -> None:
    race_one = uuid4()
    race_two = uuid4()
    races = [
        {
            "id": race_one,
            "round": 1,
            "official_name": "One",
            "country": "A",
            "circuit": "A",
            "start_at": datetime(2026, 3, 8, 14, tzinfo=UTC),
        },
        {
            "id": race_two,
            "round": 2,
            "official_name": "Two",
            "country": "B",
            "circuit": "B",
            "start_at": datetime(2026, 3, 15, 14, tzinfo=UTC),
        },
    ]
    meetings = [
        _meeting(100, datetime(2026, 3, 8, 16, tzinfo=UTC)),
        _meeting(200, datetime(2026, 3, 15, 16, tzinfo=UTC)),
    ]

    assert match_meetings_to_races(meetings, races) == {100: race_one, 200: race_two}


def test_meeting_outside_weekend_tolerance_is_not_matched() -> None:
    race_id = uuid4()
    races = [
        {
            "id": race_id,
            "round": 1,
            "official_name": "One",
            "country": "A",
            "circuit": "A",
            "start_at": datetime(2026, 3, 8, 14, tzinfo=UTC),
        }
    ]

    assert match_meetings_to_races(
        [_meeting(100, datetime(2026, 3, 12, 14, tzinfo=UTC))], races
    ) == {}


def test_qualifying_segments_are_children_of_one_qualifying_session() -> None:
    assert qualifying_segment_definitions("qualifying") == (
        ("q1", "Q1", 1),
        ("q2", "Q2", 2),
        ("q3", "Q3", 3),
    )
    assert qualifying_segment_definitions("race") == ()
