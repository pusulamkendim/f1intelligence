from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


class FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows

    def first(self) -> dict[str, Any] | None:
        return self.rows[0] if self.rows else None

    def all(self) -> list[dict[str, Any]]:
        return self.rows


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows

    def mappings(self) -> FakeMappings:
        return FakeMappings(self.rows)


class FakeSession:
    def __init__(self, responses: list[list[dict[str, Any]]]):
        self.responses = responses
        self.index = 0

    async def execute(self, *_args: Any, **_kwargs: Any) -> FakeResult:
        rows = self.responses[self.index]
        self.index += 1
        return FakeResult(rows)


def override_with(fake_session: FakeSession):
    async def override_db() -> AsyncIterator[FakeSession]:
        yield fake_session

    return override_db


def test_driver_context_exposes_roster_session_relations_timeline_and_related() -> None:
    entity_id = uuid4()
    person_id = uuid4()
    red_bull_id = uuid4()
    racing_bulls_id = uuid4()
    story_id = uuid4()
    fetched_at = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    fake_session = FakeSession(
        [
            [
                {
                    "entity_id": entity_id,
                    "slug": "yuki-tsunoda",
                    "display_name": "Yuki Tsunoda",
                    "entity_metadata": {"kind": "driver"},
                    "person_id": person_id,
                    "nationality_code": "JPN",
                }
            ],
            [
                {
                    "relation_type": "roster_driver_for",
                    "target_id": red_bull_id,
                    "target_key": "red-bull-racing",
                    "target_label": "Red Bull Racing",
                    "season": 2026,
                    "source_url": "https://example.test/roster",
                    "session_count": None,
                    "first_session_at": None,
                    "last_session_at": None,
                },
                {
                    "relation_type": "participated_for",
                    "target_id": racing_bulls_id,
                    "target_key": "racing-bulls",
                    "target_label": "Racing Bulls",
                    "season": 2026,
                    "source_url": None,
                    "session_count": 15,
                    "first_session_at": fetched_at,
                    "last_session_at": fetched_at,
                },
            ],
            [
                {
                    "race_results": 3,
                    "qualifying_results": 3,
                    "session_results": 15,
                    "laps": 0,
                    "stints": 0,
                    "positions": 0,
                    "intervals": 0,
                    "pit_stops": 0,
                    "starting_grid": 0,
                    "overtakes": 0,
                    "standings": 1,
                    "stories": 1,
                    "documents": 0,
                    "evidence": 0,
                }
            ],
            [
                {
                    "provider": "jolpica",
                    "source_url": "https://example.test/standings",
                    "fetched_at": fetched_at,
                    "metadata": {
                        "provider_entity_type": "driver",
                        "provider_id": "tsunoda",
                    },
                }
            ],
            [
                {
                    "event_id": str(story_id),
                    "event_type": "story",
                    "occurred_at": fetched_at,
                    "label": "Tsunoda returns to Racing Bulls",
                    "target_type": "story",
                    "target_id": str(story_id),
                    "target_key": "tsunoda-racing-bulls-return",
                    "target_label": "Tsunoda returns to Racing Bulls",
                    "target_subtype": "developing",
                    "provider": None,
                    "source_url": None,
                    "fetched_at": fetched_at,
                    "metadata": {
                        "relation_type": "directly_involved",
                        "relation_confidence": 100,
                    },
                }
            ],
        ]
    )
    app.dependency_overrides[get_db] = override_with(fake_session)
    try:
        response = TestClient(app).get("/api/v1/context/driver/yuki-tsunoda")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract_version"] == "1"
    assert payload["target"]["type"] == "driver"
    assert payload["target"]["key"] == "yuki-tsunoda"
    assert [relation["type"] for relation in payload["relations"]] == [
        "roster_driver_for",
        "participated_for",
    ]
    assert payload["relations"][1]["target"]["key"] == "racing-bulls"
    assert payload["relations"][1]["metadata"]["session_count"] == 15
    assert {facet["type"] for facet in payload["facets"]} == {
        "race_results",
        "qualifying_results",
        "session_results",
        "standings",
        "stories",
    }
    assert payload["provenance"][0]["metadata"]["provider_id"] == "tsunoda"
    assert payload["timeline"][0]["type"] == "story"
    assert payload["timeline"][0]["source"] == "stories"
    assert payload["timeline"][0]["target"]["key"] == "tsunoda-racing-bulls-return"
    assert [item["key"] for item in payload["related"]] == [
        "red-bull-racing",
        "racing-bulls",
        "tsunoda-racing-bulls-return",
    ]


def test_session_context_links_race_season_and_participants() -> None:
    session_id = uuid4()
    race_id = uuid4()
    race_entity_id = uuid4()
    driver_id = uuid4()
    team_id = uuid4()
    starts_at = datetime(2026, 9, 13, 13, 0, tzinfo=UTC)
    fetched_at = datetime(2026, 9, 13, 16, 0, tzinfo=UTC)
    fake_session = FakeSession(
        [
            [
                {
                    "session_id": session_id,
                    "session_code": "race",
                    "session_name": "Race",
                    "session_type": "Race",
                    "starts_at": starts_at,
                    "ends_at": None,
                    "provider": "openf1",
                    "source_url": "https://example.test/session",
                    "fetched_at": fetched_at,
                    "race_id": race_id,
                    "season": 2026,
                    "race_slug": "2026-madrid-grand-prix",
                    "race_entity_id": race_entity_id,
                    "race_label": "2026 Madrid Grand Prix",
                    "context_key": "2026-madrid-grand-prix-race",
                }
            ],
            [
                {
                    "entity_id": race_entity_id,
                    "slug": "2026-madrid-grand-prix",
                    "display_name": "2026 Madrid Grand Prix",
                }
            ],
            [
                {
                    "driver_id": driver_id,
                    "driver_key": "yuki-tsunoda",
                    "driver_label": "Yuki Tsunoda",
                    "team_id": team_id,
                    "team_key": "racing-bulls",
                    "team_label": "Racing Bulls",
                    "driver_number": 22,
                }
            ],
            [
                {
                    "entries": 22,
                    "results": 22,
                    "laps": 1100,
                    "stints": 44,
                    "positions": 200,
                    "intervals": 0,
                    "pit_stops": 0,
                    "starting_grid": 0,
                    "overtakes": 0,
                    "race_control": 0,
                    "weather": 0,
                    "evidence": 0,
                }
            ],
            [
                {
                    "provider": "openf1",
                    "source_url": "https://example.test/session",
                    "fetched_at": fetched_at,
                    "metadata": {
                        "provider_session_id": "9999",
                        "provider_meeting_id": "8888",
                    },
                }
            ],
            [],
        ]
    )
    app.dependency_overrides[get_db] = override_with(fake_session)
    try:
        response = TestClient(app).get(
            "/api/v1/context/session/2026-madrid-grand-prix-race"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["target"]["subtype"] == "race"
    assert payload["relations"][0]["type"] == "part_of_race"
    assert payload["relations"][1]["type"] == "part_of_season"
    participant = payload["relations"][2]
    assert participant["type"] == "has_participant"
    assert participant["target"]["key"] == "yuki-tsunoda"
    assert participant["metadata"]["team"]["key"] == "racing-bulls"
    assert {facet["type"] for facet in payload["facets"]} == {
        "entries",
        "results",
        "laps",
        "stints",
        "positions",
    }
    assert [item["key"] for item in payload["related"]] == [
        "2026-madrid-grand-prix",
        "2026",
        "yuki-tsunoda",
    ]


def test_season_context_is_virtual_and_lists_canonical_races() -> None:
    race_entity_id = uuid4()
    fake_session = FakeSession(
        [
            [
                {
                    "season": 2026,
                    "race_count": 23,
                    "starts_on": None,
                    "ends_on": None,
                }
            ],
            [
                {
                    "entity_id": race_entity_id,
                    "slug": "2026-australian-grand-prix",
                    "display_name": "2026 Australian Grand Prix",
                    "round": 1,
                }
            ],
            [
                {
                    "races": 23,
                    "race_results": 308,
                    "qualifying_results": 303,
                    "sessions": 115,
                    "session_results": 1527,
                    "documents": 73,
                    "stories": 2,
                }
            ],
            [],
        ]
    )
    app.dependency_overrides[get_db] = override_with(fake_session)
    try:
        response = TestClient(app).get("/api/v1/context/season/2026")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["target"]["id"] == "2026"
    assert payload["target"]["metadata"]["race_count"] == 23
    assert payload["relations"][0]["type"] == "has_race"
    assert payload["provenance"] == []
    assert payload["related"][0]["key"] == "2026-australian-grand-prix"


def test_context_returns_404_for_missing_target() -> None:
    fake_session = FakeSession([[]])
    app.dependency_overrides[get_db] = override_with(fake_session)
    try:
        response = TestClient(app).get("/api/v1/context/driver/not-a-driver")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Driver context not found"
