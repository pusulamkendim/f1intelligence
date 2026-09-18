from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from app.ingestion.openf1 import OpenF1Client, parse_session_results, parse_sessions


def test_parse_sessions_normalizes_full_weekend_types() -> None:
    payload = [
        {
            "session_key": 1,
            "meeting_key": 10,
            "year": 2026,
            "session_name": "Practice 1",
            "session_type": "Practice",
            "date_start": "2026-09-18T09:00:00+00:00",
            "date_end": "2026-09-18T10:00:00+00:00",
        },
        {
            "session_key": 2,
            "meeting_key": 10,
            "year": 2026,
            "session_name": "Sprint Qualifying",
            "session_type": "Sprint Qualifying",
            "date_start": "2026-09-18T13:00:00+00:00",
            "date_end": "2026-09-18T13:45:00+00:00",
        },
        {
            "session_key": 3,
            "meeting_key": 10,
            "year": 2026,
            "session_name": "Sprint",
            "session_type": "Race",
            "date_start": "2026-09-19T10:00:00+00:00",
            "date_end": "2026-09-19T11:00:00+00:00",
        },
        {
            "session_key": 4,
            "meeting_key": 10,
            "year": 2026,
            "session_name": "Qualifying",
            "session_type": "Qualifying",
            "date_start": "2026-09-19T14:00:00+00:00",
            "date_end": "2026-09-19T15:00:00+00:00",
        },
        {
            "session_key": 5,
            "meeting_key": 10,
            "year": 2026,
            "session_name": "Race",
            "session_type": "Race",
            "date_start": "2026-09-20T12:00:00+00:00",
            "date_end": "2026-09-20T14:00:00+00:00",
        },
    ]

    assert [item.session_code for item in parse_sessions(payload)] == [
        "practice_1",
        "sprint_qualifying",
        "sprint",
        "qualifying",
        "race",
    ]


def test_parse_session_results_preserves_qualifying_phases_and_race_gap() -> None:
    qualifying = parse_session_results(
        [
            {
                "session_key": 1,
                "meeting_key": 10,
                "driver_number": 4,
                "position": 1,
                "duration": [80.1, 79.9, 79.5],
                "gap_to_leader": [0, 0, 0],
                "number_of_laps": 18,
            }
        ]
    )[0]
    assert qualifying.duration_seconds is None
    assert (qualifying.q1_seconds, qualifying.q2_seconds, qualifying.q3_seconds) == (
        80.1,
        79.9,
        79.5,
    )

    race = parse_session_results(
        [
            {
                "session_key": 2,
                "meeting_key": 10,
                "driver_number": 81,
                "position": 2,
                "duration": 5400.123,
                "gap_to_leader": "+1 LAP",
                "number_of_laps": 56,
            }
        ]
    )[0]
    assert race.duration_seconds == 5400.123
    assert race.gap_to_leader_text == "+1 LAP"


@pytest.mark.asyncio
async def test_client_retries_429_using_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, request=request)
        return httpx.Response(200, json=[], request=request)

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("app.ingestion.openf1.asyncio.sleep", no_sleep)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = OpenF1Client(
            http_client,
            base_url="https://openf1.test/v1",
            min_interval_seconds=0.1,
            retries=2,
        )
        assert await client.sessions(2026) == []

    assert calls == 2



@pytest.mark.asyncio
async def test_location_client_chunks_large_session_windows() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if len(calls) == 1:
            payload = [
                {
                    "session_key": 999,
                    "driver_number": 1,
                    "date": "2026-09-18T12:00:00Z",
                    "x": 100,
                    "y": 200,
                    "z": 10,
                }
            ]
        else:
            payload = [
                {
                    "session_key": 999,
                    "driver_number": 1,
                    "date": "2026-09-18T12:15:00Z",
                    "x": 300,
                    "y": 400,
                    "z": 20,
                }
            ]
        return httpx.Response(200, json=payload, request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as http_client:
        client = OpenF1Client(
            http_client,
            base_url="https://openf1.test/v1",
            min_interval_seconds=0,
        )
        rows = await client.locations(
            999,
            date_start=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
            date_end=datetime(2026, 9, 18, 12, 20, tzinfo=UTC),
            sample_interval_ms=1000,
            chunk_minutes=15,
        )

    assert len(calls) == 2
    assert "date%3E%3D=" in calls[0]
    assert "date%3C=" in calls[0]
    assert [(row.x, row.y) for row in rows] == [(100, 200), (300, 400)]
