import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.ingestion.source_item_entities import SourceItemEntityClassification
from app.ingestion.story_materialization import _create_story, classify_story_worthiness


def _classification(relation_type: str = "subject") -> SourceItemEntityClassification:
    return SourceItemEntityClassification(
        entity_id=uuid4(),
        entity_type="person",
        slug="example-driver",
        display_name="Example Driver",
        relation_type=relation_type,
        confidence=100,
        match_method="title_alias",
        matched_alias="Example Driver",
        detected_in=("title",),
        classification_method="deterministic_v2",
    )


def test_editorial_calendar_story_is_retained_without_entity_links() -> None:
    decision = classify_story_worthiness(
        source_class="independent_editorial",
        title="Formula 1 2027 calendar announced with 10 Sprint weekends",
        classifications=(),
    )

    assert decision.story_worthy is True
    assert decision.taxonomy == "sporting"


def test_generic_reddit_discussion_is_not_a_story() -> None:
    decision = classify_story_worthiness(
        source_class="community_signal",
        title="Ask r/Formula1 Anything - Daily Discussion Thread",
        classifications=(),
    )

    assert decision.story_worthy is False
    assert decision.reason == "non_story_container"


def test_community_signal_needs_a_strong_entity() -> None:
    weak = classify_story_worthiness(
        source_class="community_signal",
        title="Interesting paddock observation",
        classifications=(_classification("mentioned"),),
    )
    strong = classify_story_worthiness(
        source_class="community_signal",
        title="Lewis Hamilton responds to recent reports",
        classifications=(_classification("subject"),),
    )

    assert weak.story_worthy is False
    assert strong.story_worthy is True


def test_first_party_photo_gallery_is_not_materialized_as_a_story() -> None:
    decision = classify_story_worthiness(
        source_class="first_party_team",
        title="In Photos: The Spanish GP through our lens",
        classifications=(_classification("context"),),
    )

    assert decision.story_worthy is False


def test_business_news_is_retained_and_taxonomized() -> None:
    decision = classify_story_worthiness(
        source_class="independent_editorial",
        title="Haas confident of getting 2027 F1 budget closer to cap with new partner talks",
        classifications=(_classification(),),
    )

    assert decision.story_worthy is True
    assert decision.taxonomy == "team_business"


class _StoryInsertResult:
    def __init__(self, story_id: UUID):
        self.story_id = story_id

    def scalar_one(self) -> UUID:
        return self.story_id


class _CompileCheckingSession:
    def __init__(self, story_id: UUID):
        self.story_id = story_id

    async def execute(self, statement: Any, params: dict[str, Any]) -> _StoryInsertResult:
        compiled_params = statement.compile().params
        assert "1" not in compiled_params
        assert set(compiled_params) == {
            "slug",
            "title",
            "summary",
            "taxonomy",
            "method",
            "source_item_id",
            "published_at",
        }
        assert set(params) == set(compiled_params)
        return _StoryInsertResult(self.story_id)


def test_create_story_sql_does_not_parse_json_as_bind_parameter() -> None:
    story_id = uuid4()
    source_item_id = uuid4()
    session = _CompileCheckingSession(story_id)

    result = asyncio.run(
        _create_story(
            session,  # type: ignore[arg-type]
            source_item_id=source_item_id,
            title="Example F1 story",
            summary="Example summary",
            taxonomy="general",
            published_at=datetime(2026, 9, 17, 12, 0, tzinfo=UTC),
        )
    )

    assert result == story_id
