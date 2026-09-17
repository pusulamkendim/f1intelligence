from datetime import UTC, datetime
from uuid import uuid4

from app.context.aggregation import RELATED_LIMIT, build_related
from app.context.resolver import ResolvedTarget
from app.schemas.context import ContextRelation, ContextTarget, ContextTargetRef, ContextTimelineEvent


def _ref(target_type: str, key: str) -> ContextTargetRef:
    return ContextTargetRef(
        type=target_type,
        id=str(uuid4()),
        key=key,
        label=key,
    )


def test_related_prefers_relations_then_adds_timeline_targets_without_duplicates() -> None:
    root = ResolvedTarget(
        target=ContextTarget(
            type="driver",
            id="driver-1",
            key="driver-1",
            label="Driver 1",
        )
    )
    team = _ref("team", "team-1")
    story = _ref("story", "story-1")
    relations = [ContextRelation(type="participated_for", target=team)]
    timeline = [
        ContextTimelineEvent(
            id="event-1",
            type="story",
            occurred_at=datetime(2026, 9, 17, tzinfo=UTC),
            label="Story 1",
            target=story,
            source="stories",
        ),
        ContextTimelineEvent(
            id="event-2",
            type="story",
            occurred_at=datetime(2026, 9, 16, tzinfo=UTC),
            label="Team duplicate",
            target=team,
            source="stories",
        ),
    ]

    related = build_related(root, relations, timeline)

    assert [item.key for item in related] == ["team-1", "story-1"]


def test_related_is_bounded() -> None:
    root = ResolvedTarget(
        target=ContextTarget(
            type="season",
            id="2026",
            key="2026",
            label="2026 Formula 1 season",
        )
    )
    relations = [
        ContextRelation(type="has_race", target=_ref("race", f"race-{index}"))
        for index in range(RELATED_LIMIT + 5)
    ]

    related = build_related(root, relations, [])

    assert len(related) == RELATED_LIMIT
