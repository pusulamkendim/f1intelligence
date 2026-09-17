from uuid import uuid4

from app.ingestion.source_item_entities import SourceItemEntityClassification
from app.ingestion.story_materialization import classify_story_worthiness


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
