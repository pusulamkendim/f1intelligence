from uuid import uuid4

from app.ingestion.entity_matcher import EntityAlias
from app.ingestion.source_item_entities import (
    SourceItemText,
    classify_source_item_entities,
    detect_source_item_entity_candidates,
)


def _alias(
    *,
    entity_type: str,
    slug: str,
    name: str,
    value: str,
    confidence: int = 95,
) -> EntityAlias:
    return EntityAlias(
        entity_id=uuid4(),
        entity_type=entity_type,
        slug=slug,
        display_name=name,
        alias=value,
        alias_type="test",
        confidence=confidence,
        valid_from_season=2026,
        valid_to_season=2026,
    )


def test_detection_is_separate_from_relation_assignment() -> None:
    mercedes = _alias(
        entity_type="team",
        slug="mercedes",
        name="Mercedes",
        value="Mercedes",
    )
    item = SourceItemText(
        title="Mercedes begins work on its 2027 car",
        season=2026,
    )

    candidates = detect_source_item_entity_candidates(item, [mercedes])

    assert len(candidates) == 1
    assert candidates[0].slug == "mercedes"
    assert candidates[0].strongest_scope == "title"
    assert candidates[0].detected_in == ("title",)


def test_first_party_team_source_adds_context_when_team_is_not_in_text() -> None:
    mclaren = _alias(
        entity_type="team",
        slug="mclaren",
        name="McLaren",
        value="McLaren",
        confidence=100,
    )

    result = classify_source_item_entities(
        SourceItemText(
            title="WATCH: Behind the scenes of Designed to Race: Front Row",
            season=2026,
            source_context_team_slug="mclaren",
        ),
        [mclaren],
    )

    assert len(result) == 1
    assert result[0].slug == "mclaren"
    assert result[0].relation_type == "context"
    assert result[0].confidence == 100
    assert result[0].match_method == "source_context"
    assert result[0].detected_in == ("source",)


def test_textual_relation_wins_over_source_context_for_same_team() -> None:
    alpine = _alias(
        entity_type="team",
        slug="alpine",
        name="Alpine",
        value="Alpine",
        confidence=100,
    )

    result = classify_source_item_entities(
        SourceItemText(
            title="Mike Elliott joins Alpine as Chief Technical Officer",
            season=2026,
            source_context_team_slug="alpine",
        ),
        [alpine],
    )

    assert len(result) == 1
    assert result[0].relation_type == "subject"
    assert result[0].match_method == "title_alias"
