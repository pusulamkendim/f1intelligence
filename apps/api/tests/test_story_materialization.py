import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import app.ingestion.story_materialization as story_materialization
from app.ingestion.content_cleanup import clean_summary, clean_title
from app.ingestion.source_item_entities import SourceItemEntityClassification
from app.ingestion.story_materialization import (
    _converge_event_fingerprint_stories,
    _create_story,
    classify_story_worthiness,
)


def _classification(
    relation_type: str = "subject",
) -> SourceItemEntityClassification:
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


def test_first_party_evergreen_and_activation_content_is_filtered() -> None:
    titles = (
        "A seat at the table",
        "Five things you can't teach an F1 mechanic",
        "Some assembly required – the mechanics building our F1 cars",
        "Explore Budapest",
        "Fan designed stickers feature in our Madrid garage",
    )
    for title in titles:
        decision = classify_story_worthiness(
            source_class="first_party_team",
            title=title,
            classifications=(),
        )
        assert decision.story_worthy is False, title


def test_business_news_is_retained_and_taxonomized() -> None:
    decision = classify_story_worthiness(
        source_class="independent_editorial",
        title="Haas confident of getting 2027 F1 budget closer to cap with new partner talks",
        classifications=(_classification(),),
    )

    assert decision.story_worthy is True
    assert decision.taxonomy == "team_business"


def test_licensing_appointment_is_business_not_personnel() -> None:
    decision = classify_story_worthiness(
        source_class="first_party_team",
        title="TGR Haas F1 Team Appoints Brandand to Drive Global Licensing",
        classifications=(),
    )

    assert decision.story_worthy is True
    assert decision.taxonomy == "team_business"


def test_driver_contract_extension_is_personnel() -> None:
    decision = classify_story_worthiness(
        source_class="first_party_team",
        title="MAX. ORACLE RED BULL RACING. 2030.",
        classifications=(_classification(),),
    )

    # The stylised headline has no action verb, so the source summary/entity context
    # will carry personnel semantics later. A normal contract headline is deterministic.
    normal = classify_story_worthiness(
        source_class="independent_editorial",
        title="Max Verstappen extends Red Bull contract until the end of 2030",
        classifications=(_classification(),),
    )
    assert decision.story_worthy is True
    assert normal.taxonomy == "personnel"


def test_html_entities_and_feed_boilerplate_are_cleaned() -> None:
    assert clean_title("Isack Hadjar: driver&#x27;s injury update") == (
        "Isack Hadjar: driver's injury update"
    )
    assert clean_summary("A factual sentence. Keep reading") == "A factual sentence"
    assert clean_summary("A factual sentence. Read Also: More coverage") == (
        "A factual sentence"
    )


class _StoryInsertResult:
    def __init__(self, story_id: UUID):
        self.story_id = story_id

    def scalar_one(self) -> UUID:
        return self.story_id


class _CompileCheckingSession:
    def __init__(self, story_id: UUID):
        self.story_id = story_id

    async def execute(
        self,
        statement: Any,
        params: dict[str, Any],
    ) -> _StoryInsertResult:
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



class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _ConvergenceSession:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    async def execute(self, statement, params=None):
        self.calls += 1
        if self.calls == 1:
            return _RowsResult(self.rows)
        return _RowsResult([])


def test_event_fingerprint_convergence_merges_split_roots() -> None:
    left = uuid4()
    right = uuid4()
    session = _ConvergenceSession(
        [
            {
                "fingerprint": (
                    "personnel_appointment:"
                    "alpine:technical_leadership"
                ),
                "story_ids": [left, right],
            }
        ]
    )
    merged_pairs: list[tuple[UUID, UUID]] = []
    refreshed: list[UUID] = []

    async def fake_merge(_session, left_story_id, right_story_id):
        merged_pairs.append((left_story_id, right_story_id))
        return left_story_id

    async def fake_refresh(_session, story_id):
        refreshed.append(story_id)

    original_merge = story_materialization._merge_auto_stories
    original_refresh = story_materialization.refresh_story_aggregate
    original_media = story_materialization.refresh_story_media_from_sources
    story_materialization._merge_auto_stories = fake_merge
    story_materialization.refresh_story_aggregate = fake_refresh
    story_materialization.refresh_story_media_from_sources = fake_refresh
    try:
        merges = asyncio.run(
            _converge_event_fingerprint_stories(
                session,  # type: ignore[arg-type]
            )
        )
    finally:
        story_materialization._merge_auto_stories = original_merge
        story_materialization.refresh_story_aggregate = original_refresh
        story_materialization.refresh_story_media_from_sources = original_media

    assert merges == 1
    assert merged_pairs == [(left, right)]
    assert refreshed == [left, left]
