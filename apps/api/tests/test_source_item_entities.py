from uuid import UUID, uuid4

from app.ingestion.entity_matcher import EntityAlias
from app.ingestion.source_item_entities import SourceItemText, classify_source_item_entities


def _alias(
    entity_id: UUID,
    *,
    entity_type: str,
    slug: str,
    name: str,
    value: str,
    confidence: int = 95,
) -> EntityAlias:
    return EntityAlias(
        entity_id=entity_id,
        entity_type=entity_type,
        slug=slug,
        display_name=name,
        alias=value,
        alias_type="test",
        confidence=confidence,
        valid_from_season=2026,
        valid_to_season=2026,
    )


def test_classifier_separates_subject_direct_involvement_and_race_context() -> None:
    max_id = uuid4()
    red_bull_id = uuid4()
    race_id = uuid4()
    aliases = [
        _alias(
            max_id,
            entity_type="person",
            slug="max-verstappen",
            name="Max Verstappen",
            value="Verstappen",
        ),
        _alias(
            red_bull_id,
            entity_type="team",
            slug="red-bull-racing",
            name="Red Bull Racing",
            value="Red Bull",
        ),
        _alias(
            race_id,
            entity_type="race",
            slug="2026-azerbaijan-grand-prix",
            name="2026 Azerbaijan Grand Prix",
            value="Azerbaijan Grand Prix",
            confidence=99,
        ),
    ]
    item = SourceItemText(
        title="Verstappen explains qualifying problems at Azerbaijan Grand Prix",
        standfirst="Red Bull struggled with balance throughout qualifying.",
        summary="Red Bull is investigating the setup direction after the session.",
        body_excerpt="The Red Bull driver described the car as inconsistent.",
        season=2026,
    )

    result = classify_source_item_entities(item, aliases)
    by_slug = {classification.slug: classification for classification in result}

    assert by_slug["max-verstappen"].relation_type == "subject"
    assert by_slug["max-verstappen"].match_method == "title_alias"
    assert by_slug["red-bull-racing"].relation_type == "directly_involved"
    assert by_slug["red-bull-racing"].detected_in == (
        "standfirst",
        "summary",
        "body_excerpt",
    )
    assert by_slug["2026-azerbaijan-grand-prix"].relation_type == "context"
    assert by_slug["2026-azerbaijan-grand-prix"].confidence == 100


def test_classifier_keeps_single_body_reference_as_mentioned() -> None:
    hamilton_id = uuid4()
    aliases = [
        _alias(
            hamilton_id,
            entity_type="person",
            slug="lewis-hamilton",
            name="Lewis Hamilton",
            value="Lewis Hamilton",
            confidence=96,
        )
    ]

    result = classify_source_item_entities(
        SourceItemText(
            title="Ferrari reviews its qualifying execution",
            body_excerpt="Lewis Hamilton was also referenced in the comparison.",
            season=2026,
        ),
        aliases,
    )

    assert len(result) == 1
    assert result[0].relation_type == "mentioned"
    assert result[0].confidence == 90
    assert result[0].match_method == "body_excerpt_alias"


def test_classifier_deduplicates_aliases_for_same_entity_and_prefers_title_scope() -> None:
    team_id = uuid4()
    aliases = [
        _alias(
            team_id,
            entity_type="team",
            slug="red-bull-racing",
            name="Red Bull Racing",
            value="Red Bull",
            confidence=95,
        ),
        _alias(
            team_id,
            entity_type="team",
            slug="red-bull-racing",
            name="Red Bull Racing",
            value="Oracle Red Bull Racing",
            confidence=98,
        ),
    ]

    result = classify_source_item_entities(
        SourceItemText(
            title="Oracle Red Bull Racing brings a revised floor",
            summary="Red Bull expects to evaluate the package on Friday.",
            season=2026,
        ),
        aliases,
    )

    assert len(result) == 1
    assert result[0].relation_type == "subject"
    assert result[0].matched_alias == "Oracle Red Bull Racing"
    assert result[0].detected_in == ("title", "summary")
