from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
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


def test_list_teams_returns_current_catalog_counts() -> None:
    fake_session = FakeSession(
        [
            [
                {
                    "id": uuid4(),
                    "slug": "mclaren",
                    "name": "McLaren",
                    "active_season": 2026,
                    "driver_count": 2,
                    "story_count": 1,
                }
            ]
        ]
    )
    app.dependency_overrides[get_db] = override_with(fake_session)
    try:
        response = TestClient(app).get("/api/v1/teams")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["slug"] == "mclaren"
    assert response.json()[0]["driver_count"] == 2


def test_get_team_returns_members_and_linked_stories() -> None:
    now = datetime(2026, 9, 17, 0, 0, tzinfo=UTC)
    team_id = uuid4()
    entity_id = uuid4()
    fake_session = FakeSession(
        [
            [
                {
                    "id": team_id,
                    "slug": "mclaren",
                    "name": "McLaren",
                    "active_season": 2026,
                    "entity_id": entity_id,
                }
            ],
            [
                {
                    "id": uuid4(),
                    "slug": "lando-norris",
                    "display_name": "Lando Norris",
                    "role": "driver",
                    "season": 2026,
                    "car_number": 1,
                },
                {
                    "id": uuid4(),
                    "slug": "andrea-stella",
                    "display_name": "Andrea Stella",
                    "role": "team_principal",
                    "season": 2026,
                    "car_number": None,
                },
            ],
            [
                {
                    "id": uuid4(),
                    "slug": "fia-2026-sporting-decisions",
                    "title": "2026 FIA Formula One sporting and regulatory decisions",
                    "summary": "Official FIA decisions.",
                    "status": "monitoring",
                    "updated_at": now,
                    "evidence_count": 2,
                    "latest_evidence_at": now,
                }
            ],
        ]
    )
    app.dependency_overrides[get_db] = override_with(fake_session)
    try:
        response = TestClient(app).get("/api/v1/teams/mclaren")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "McLaren"
    assert payload["members"][0]["car_number"] == 1
    assert [member["role"] for member in payload["members"]] == ["driver", "team_principal"]
    assert payload["stories"][0]["slug"] == "fia-2026-sporting-decisions"


def test_list_races_returns_calendar_order_data() -> None:
    fake_session = FakeSession(
        [
            [
                {
                    "id": uuid4(),
                    "season": 2026,
                    "round": 15,
                    "slug": "2026-azerbaijan-grand-prix",
                    "official_name": "Grand Prix of Azerbaijan",
                    "circuit": "Baku",
                    "country": "Azerbaijan",
                    "start_at": None,
                    "weekend_start_date": date(2026, 9, 24),
                    "weekend_end_date": date(2026, 9, 26),
                    "status": "upcoming",
                    "story_count": 0,
                }
            ]
        ]
    )
    app.dependency_overrides[get_db] = override_with(fake_session)
    try:
        response = TestClient(app).get("/api/v1/races")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["round"] == 15
    assert payload["weekend_start_date"] == "2026-09-24"


def test_next_race_context_returns_countdowns_and_next_session() -> None:
    race_id = uuid4()
    session_id = uuid4()
    start = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    session_start = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)
    fake_session = FakeSession(
        [
            [
                {
                    "id": race_id,
                    "season": 2026,
                    "round": 15,
                    "slug": "2026-azerbaijan-grand-prix",
                    "official_name": "Azerbaijan Grand Prix",
                    "circuit": "Baku City Circuit",
                    "country": "Azerbaijan",
                    "start_at": start,
                    "weekend_start_date": date(2026, 9, 18),
                    "weekend_end_date": date(2026, 9, 20),
                    "status": "scheduled",
                    "story_count": 0,
                    "seconds_until_race": 1000,
                }
            ],
            [
                {
                    "id": session_id,
                    "session_code": "practice_1",
                    "session_name": "Practice 1",
                    "session_type": "Practice",
                    "sequence": 1,
                    "starts_at": session_start,
                    "ends_at": datetime(2026, 9, 18, 10, 0, tzinfo=UTC),
                    "is_cancelled": False,
                    "result_count": 0,
                    "seconds_until_next_session": 500,
                }
            ],
        ]
    )
    app.dependency_overrides[get_db] = override_with(fake_session)
    try:
        response = TestClient(app).get("/api/v1/races/next-context")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["race"]["round"] == 15
    assert payload["seconds_until_race"] == 1000
    assert payload["next_session"]["session_code"] == "practice_1"
    assert payload["seconds_until_next_session"] == 500


def test_get_race_returns_linked_stories_documents_and_sessions() -> None:
    now = datetime(2026, 9, 17, 0, 0, tzinfo=UTC)
    race_id = uuid4()
    entity_id = uuid4()
    fake_session = FakeSession(
        [
            [
                {
                    "id": race_id,
                    "season": 2026,
                    "round": 13,
                    "slug": "2026-italian-grand-prix",
                    "official_name": "Grand Prix of Italy",
                    "circuit": "Monza",
                    "country": "Italy",
                    "start_at": None,
                    "weekend_start_date": date(2026, 9, 4),
                    "weekend_end_date": date(2026, 9, 6),
                    "status": "completed",
                    "synthesis": None,
                    "entity_id": entity_id,
                    "story_count": 1,
                }
            ],
            [
                {
                    "id": uuid4(),
                    "slug": "monza-example",
                    "title": "Monza technical development",
                    "summary": None,
                    "status": "developing",
                    "updated_at": now,
                    "evidence_count": 1,
                    "latest_evidence_at": now,
                }
            ],
            [
                {
                    "id": uuid4(),
                    "document_number": 10,
                    "title": "Car Presentation Submissions",
                    "document_type": "car_presentation",
                    "document_url": "https://www.fia.com/example.pdf",
                    "published_at": now,
                    "recalled": False,
                }
            ],
            [
                {
                    "id": uuid4(),
                    "session_code": "practice_2",
                    "session_name": "Practice 2",
                    "session_type": "Practice",
                    "sequence": 2,
                    "starts_at": now,
                    "ends_at": now,
                    "is_cancelled": False,
                    "result_count": 22,
                }
            ],
        ]
    )
    app.dependency_overrides[get_db] = override_with(fake_session)
    try:
        response = TestClient(app).get("/api/v1/races/2026-italian-grand-prix")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["circuit"] == "Monza"
    assert payload["stories"][0]["slug"] == "monza-example"
    assert payload["documents"][0]["document_type"] == "car_presentation"
    assert payload["sessions"][0]["session_code"] == "practice_2"
    assert payload["sessions"][0]["result_count"] == 22


def test_catalog_detail_routes_return_404_for_missing_items() -> None:
    for path in ("/api/v1/teams/missing", "/api/v1/races/missing"):
        fake_session = FakeSession([[]])
        app.dependency_overrides[get_db] = override_with(fake_session)
        try:
            response = TestClient(app).get(path)
        finally:
            app.dependency_overrides.clear()
        assert response.status_code == 404
