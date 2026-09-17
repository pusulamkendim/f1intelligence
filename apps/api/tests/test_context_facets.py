from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from app.context.facets import FACET_SPECS
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


def session_target_row() -> dict[str, Any]:
    session_id = uuid4()
    race_id = uuid4()
    return {
        "session_id": session_id,
        "session_code": "race",
        "session_name": "Race",
        "session_type": "Race",
        "starts_at": datetime(2026, 9, 13, 13, 0, tzinfo=UTC),
        "ends_at": None,
        "provider": "openf1",
        "source_url": "https://example.test/session",
        "fetched_at": datetime(2026, 9, 13, 16, 0, tzinfo=UTC),
        "race_id": race_id,
        "season": 2026,
        "race_slug": "2026-madrid-grand-prix",
        "race_entity_id": uuid4(),
        "race_label": "2026 Madrid Grand Prix",
        "context_key": "2026-madrid-grand-prix-race",
    }


def test_session_laps_facet_returns_paginated_items() -> None:
    target_row = session_target_row()
    fake_session = FakeSession(
        [
            [target_row],
            [{"total": 3}],
            [
                {
                    "item": {
                        "id": str(uuid4()),
                        "lap_number": 1,
                        "lap_duration_seconds": 91.2,
                        "driver_key": "max-verstappen",
                    }
                },
                {
                    "item": {
                        "id": str(uuid4()),
                        "lap_number": 2,
                        "lap_duration_seconds": 90.8,
                        "driver_key": "max-verstappen",
                    }
                },
            ],
        ]
    )
    app.dependency_overrides[get_db] = override_with(fake_session)
    try:
        response = TestClient(app).get(
            "/api/v1/context/session/2026-madrid-grand-prix-race/facets/laps",
            params={"limit": 2, "offset": 0},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["target"]["type"] == "session"
    assert payload["facet"] == "laps"
    assert payload["total"] == 3
    assert payload["limit"] == 2
    assert payload["offset"] == 0
    assert payload["next_offset"] == 2
    assert [item["lap_number"] for item in payload["items"]] == [1, 2]


def test_facet_last_page_has_no_next_offset() -> None:
    target_row = session_target_row()
    fake_session = FakeSession(
        [
            [target_row],
            [{"total": 3}],
            [{"item": {"id": str(uuid4()), "lap_number": 3}}],
        ]
    )
    app.dependency_overrides[get_db] = override_with(fake_session)
    try:
        response = TestClient(app).get(
            "/api/v1/context/session/2026-madrid-grand-prix-race/facets/laps",
            params={"limit": 2, "offset": 2},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["next_offset"] is None


def test_unsupported_facet_returns_404() -> None:
    fake_session = FakeSession([[session_target_row()]])
    app.dependency_overrides[get_db] = override_with(fake_session)
    try:
        response = TestClient(app).get(
            "/api/v1/context/session/2026-madrid-grand-prix-race/facets/not-real"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert "not supported" in response.json()["detail"]


def test_facet_limit_is_bounded() -> None:
    fake_session = FakeSession([])
    app.dependency_overrides[get_db] = override_with(fake_session)
    try:
        response = TestClient(app).get(
            "/api/v1/context/session/2026-madrid-grand-prix-race/facets/laps",
            params={"limit": 201},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_registry_covers_overview_facets_for_each_target_type() -> None:
    expected = {
        "driver": {
            "race_results",
            "qualifying_results",
            "session_results",
            "laps",
            "stints",
            "positions",
            "intervals",
            "pit_stops",
            "starting_grid",
            "overtakes",
            "standings",
            "stories",
            "documents",
            "evidence",
        },
        "team": {
            "race_results",
            "qualifying_results",
            "session_results",
            "session_entries",
            "starting_grid",
            "standings",
            "stories",
            "documents",
            "evidence",
        },
        "race": {
            "sessions",
            "race_results",
            "qualifying_results",
            "session_results",
            "laps",
            "stints",
            "positions",
            "intervals",
            "pit_stops",
            "starting_grid",
            "overtakes",
            "race_control",
            "weather",
            "documents",
            "stories",
            "evidence",
        },
        "session": {
            "entries",
            "results",
            "laps",
            "stints",
            "positions",
            "intervals",
            "pit_stops",
            "starting_grid",
            "overtakes",
            "race_control",
            "weather",
            "evidence",
        },
        "season": {
            "races",
            "race_results",
            "qualifying_results",
            "sessions",
            "session_results",
            "documents",
            "stories",
        },
        "story": {"evidence", "entities", "publications"},
    }

    assert {target_type: set(specs) for target_type, specs in FACET_SPECS.items()} == expected


def test_document_facet_uses_real_document_entity_columns() -> None:
    sql = FACET_SPECS["driver"]["documents"].select_sql

    assert "rde.matched_alias" in sql
    assert "rde.match_method" in sql
    assert "rde.relation_type" not in sql
