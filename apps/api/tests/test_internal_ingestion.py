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


def test_ingestion_queue_returns_counts_items_and_entities() -> None:
    now = datetime(2026, 9, 17, 0, 0, tzinfo=UTC)
    item_id = uuid4()
    entity_id = uuid4()
    fake_session = FakeSession(
        [
            [
                {"status": "attached", "count": 2},
                {"status": "unmatched", "count": 7},
                {"status": "filtered", "count": 8},
            ],
            [
                {
                    "id": item_id,
                    "source_key": "fia_press_release_rss",
                    "source_name": "FIA Press Releases",
                    "source_type": "official_feed",
                    "external_id": "example-1",
                    "source_url": "https://www.fia.com/example",
                    "title": "McLaren technical update",
                    "published_at": now,
                    "status": "unmatched",
                    "match_score": 0,
                    "ingested_at": now,
                    "matched_story_slug": None,
                    "matched_story_title": None,
                }
            ],
            [
                {
                    "id": entity_id,
                    "entity_type": "team",
                    "slug": "mclaren",
                    "display_name": "McLaren",
                    "matched_alias": "McLaren",
                    "confidence": 100,
                }
            ],
        ]
    )

    async def override_db() -> AsyncIterator[FakeSession]:
        yield fake_session

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).get("/api/v1/internal/ingestion/queue?status=unmatched")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["counts"] == {
        "attached": 2,
        "unmatched": 7,
        "ambiguous": 0,
        "filtered": 8,
    }
    assert payload["items"][0]["status"] == "unmatched"
    assert payload["items"][0]["entities"][0]["slug"] == "mclaren"


def test_ingestion_queue_validates_status_and_limit() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/internal/ingestion/queue?status=bogus").status_code == 422
    assert client.get("/api/v1/internal/ingestion/queue?limit=999").status_code == 422
