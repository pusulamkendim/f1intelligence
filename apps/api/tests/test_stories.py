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


def test_list_stories_returns_public_story_summaries() -> None:
    now = datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
    story_id = uuid4()
    fake_session = FakeSession(
        [
            [
                {
                    "id": story_id,
                    "slug": "fia-2026-sporting-decisions",
                    "title": "2026 FIA Formula One sporting and regulatory decisions",
                    "summary": "Official FIA decisions and regulatory developments.",
                    "status": "monitoring",
                    "updated_at": now,
                    "evidence_count": 2,
                    "latest_evidence_at": now,
                }
            ]
        ]
    )

    async def override_db() -> AsyncIterator[FakeSession]:
        yield fake_session

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).get("/api/v1/stories")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["slug"] == "fia-2026-sporting-decisions"
    assert payload[0]["evidence_count"] == 2
    assert "confidence" not in payload[0]
    assert "significance" not in payload[0]


def test_get_story_returns_story_entities_and_evidence() -> None:
    now = datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
    story_id = uuid4()
    entity_id = uuid4()
    evidence_id = uuid4()
    fake_session = FakeSession(
        [
            [
                {
                    "id": story_id,
                    "slug": "demo-rear-stability",
                    "title": "Demo: Rear-stability development",
                    "summary": "Synthetic fixture.",
                    "status": "developing",
                    "significance": 60,
                    "confidence": "strong",
                    "what_changed": "A demo update changed the current read.",
                    "why_it_matters": "It validates the persistent-story UI.",
                    "what_to_watch_next": "Next evidence update.",
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            [
                {
                    "id": entity_id,
                    "entity_type": "team",
                    "slug": "red-bull-racing",
                    "display_name": "Red Bull Racing",
                    "relation_type": "mentioned",
                    "confidence": 95,
                    "match_method": "alias",
                    "matched_alias": "Red Bull",
                }
            ],
            [
                {
                    "id": evidence_id,
                    "source_type": "demo_fixture",
                    "source_name": "Synthetic fixture",
                    "source_url": None,
                    "published_at": now,
                    "captured_at": now,
                    "author_or_speaker": None,
                    "normalized_claim": "A synthetic technical change was recorded.",
                    "raw_excerpt_or_reference": "Demo only.",
                    "reliability_class": "fixture",
                    "directness": "direct",
                    "raw_metadata": {"presentation_type": "documented_change"},
                }
            ],
        ]
    )

    async def override_db() -> AsyncIterator[FakeSession]:
        yield fake_session

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).get("/api/v1/stories/demo-rear-stability")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["slug"] == "demo-rear-stability"
    assert payload["entities"][0]["slug"] == "red-bull-racing"
    assert payload["entities"][0]["matched_alias"] == "Red Bull"
    assert payload["evidence"][0]["presentation_type"] == "documented_change"
    assert (
        payload["evidence"][0]["normalized_claim"]
        == "A synthetic technical change was recorded."
    )


def test_get_story_returns_404() -> None:
    fake_session = FakeSession([[]])

    async def override_db() -> AsyncIterator[FakeSession]:
        yield fake_session

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).get("/api/v1/stories/missing-story")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Story not found"
