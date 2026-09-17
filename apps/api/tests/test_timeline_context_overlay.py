import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.context.resolver import ResolvedTarget
from app.schemas.context import ContextTarget, ContextTargetRef, ContextTimelineEvent
from app.timeline.context_overlay import overlay_story_placements


class _Mappings:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows

    def all(self) -> list[dict[str, Any]]:
        return self.rows


class _Result:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows

    def mappings(self) -> _Mappings:
        return _Mappings(self.rows)


class _Session:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows

    async def execute(self, *_args: Any, **_kwargs: Any) -> _Result:
        return _Result(self.rows)


def test_placement_replaces_legacy_story_timestamp_and_keeps_story_target() -> None:
    story_id = uuid4()
    race_time = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
    report_time = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)
    legacy = ContextTimelineEvent(
        id=str(story_id),
        type="story",
        occurred_at=report_time,
        label="Ferrari upgrade",
        target=ContextTargetRef(
            type="story",
            id=str(story_id),
            key="ferrari-upgrade",
            label="Ferrari upgrade",
        ),
        source="stories",
    )
    target = ResolvedTarget(
        target=ContextTarget(
            type="season",
            id="2026",
            key="2026",
            label="2026 Formula 1 season",
        ),
        season=2026,
    )
    session = _Session(
        [
            {
                "story_id": story_id,
                "slug": "ferrari-upgrade",
                "title": "Ferrari will bring a new floor to Singapore",
                "status": "emerging",
                "occurred_at": race_time,
                "timeline_at": race_time,
                "reported_at": report_time,
                "temporal_relation": "scheduled_for",
                "precision": "race",
                "season": 2026,
                "race_key": "2026-singapore-grand-prix",
                "race_label": "2026 Singapore Grand Prix",
                "session_code": None,
                "session_name": None,
                "driver_key": None,
                "driver_label": None,
                "stint_number": None,
                "lap_number": None,
                "placement_confidence": 94,
                "match_method": "story_coordinate_v1",
                "metadata": {"reason": "canonical_race_entity"},
                "provider": "autosport.com",
                "source_url": "https://example.test/upgrade",
                "fetched_at": report_time,
            }
        ]
    )

    events = asyncio.run(
        overlay_story_placements(
            session,  # type: ignore[arg-type]
            target,
            [legacy],
        )
    )

    assert len(events) == 1
    event = events[0]
    assert event.source == "timeline_placements"
    assert event.temporal_relation == "scheduled_for"
    assert event.precision == "race"
    assert event.reported_at == report_time
    assert event.occurred_at == race_time
    assert event.target is not None
    assert event.target.key == "ferrari-upgrade"
    assert event.metadata["race_key"] == "2026-singapore-grand-prix"
