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
    valid_from_season: int | None = 2026,
    valid_to_season: int | None = 2026,
) -> EntityAlias:
    return EntityAlias(
        entity_id=entity_id,
        entity_type=entity_type,
        slug=slug,
        display_name=name,
        alias=value,
        alias_type="test",
        confidence=confidence,
        valid_from_season=valid_from_season,
        valid_to_season=valid_to_season,
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


def test_explicit_future_season_does_not_link_current_race_edition() -> None:
    mclaren_id = uuid4()
    monaco_id = uuid4()
    aliases = [
        _alias(
            mclaren_id,
            entity_type="team",
            slug="mclaren",
            name="McLaren",
            value="McLaren",
            valid_to_season=None,
        ),
        _alias(
            monaco_id,
            entity_type="race",
            slug="2026-monaco-grand-prix",
            name="2026 Monaco Grand Prix",
            value="Monaco",
        ),
    ]

    result = classify_source_item_entities(
        SourceItemText(
            title="McLaren reacts to Monaco Sprint news for 2027 season",
            season=2026,
        ),
        aliases,
    )

    assert {item.slug for item in result} == {"mclaren"}


def test_body_only_race_reference_is_mentioned_not_context() -> None:
    race_id = uuid4()
    race = _alias(
        race_id,
        entity_type="race",
        slug="2026-italian-grand-prix",
        name="2026 Italian Grand Prix",
        value="Italian Grand Prix",
        confidence=95,
    )

    result = classify_source_item_entities(
        SourceItemText(
            title="Ferrari responds to staffing reports",
            body_excerpt="The topic was also discussed at the Italian Grand Prix.",
            season=2026,
        ),
        [race],
    )

    assert result[0].relation_type == "mentioned"


def test_previous_employer_in_title_is_background_mention() -> None:
    mercedes_id = uuid4()
    alpine_id = uuid4()
    elliott_id = uuid4()
    aliases = [
        _alias(
            mercedes_id,
            entity_type="team",
            slug="mercedes",
            name="Mercedes",
            value="Mercedes",
        ),
        _alias(
            alpine_id,
            entity_type="team",
            slug="alpine",
            name="Alpine",
            value="Alpine",
        ),
        _alias(
            elliott_id,
            entity_type="person",
            slug="mike-elliott",
            name="Mike Elliott",
            value="Elliott",
        ),
    ]

    result = classify_source_item_entities(
        SourceItemText(
            title="Former Mercedes F1 tech chief Elliott joins Alpine as CTO",
            season=2026,
        ),
        aliases,
    )
    by_slug = {item.slug: item for item in result}

    assert by_slug["mercedes"].relation_type == "mentioned"
    assert by_slug["mike-elliott"].relation_type == "subject"
    assert by_slug["alpine"].relation_type == "directly_involved"


def test_comparison_team_in_title_is_not_a_subject() -> None:
    mercedes_id = uuid4()
    ferrari_id = uuid4()
    wolff_id = uuid4()
    aliases = [
        _alias(
            mercedes_id,
            entity_type="team",
            slug="mercedes",
            name="Mercedes",
            value="Mercedes",
        ),
        _alias(
            ferrari_id,
            entity_type="team",
            slug="ferrari",
            name="Ferrari",
            value="Ferrari",
        ),
        _alias(
            wolff_id,
            entity_type="person",
            slug="toto-wolff",
            name="Toto Wolff",
            value="Wolff",
        ),
    ]

    result = classify_source_item_entities(
        SourceItemText(
            title="Mercedes risked looking like idiots, like Ferrari did at Monza – Wolff",
            season=2026,
        ),
        aliases,
    )
    by_slug = {item.slug: item for item in result}

    assert by_slug["mercedes"].relation_type == "subject"
    assert by_slug["ferrari"].relation_type == "mentioned"
    assert by_slug["toto-wolff"].relation_type == "subject"


def test_person_after_main_actor_is_background_mention() -> None:
    rosberg_id = uuid4()
    norris_id = uuid4()
    aliases = [
        _alias(
            rosberg_id,
            entity_type="person",
            slug="nico-rosberg",
            name="Nico Rosberg",
            value="Nico Rosberg",
        ),
        _alias(
            norris_id,
            entity_type="person",
            slug="lando-norris",
            name="Lando Norris",
            value="Lando Norris",
        ),
    ]

    result = classify_source_item_entities(
        SourceItemText(
            title="Nico Rosberg proposes major VSC rule change after Lando Norris setback",
            season=2026,
        ),
        aliases,
    )
    by_slug = {item.slug: item for item in result}

    assert by_slug["nico-rosberg"].relation_type == "subject"
    assert by_slug["lando-norris"].relation_type == "mentioned"


def test_team_driver_affiliation_is_direct_involvement_not_subject() -> None:
    norris_id = uuid4()
    mclaren_id = uuid4()
    aliases = [
        _alias(
            norris_id,
            entity_type="person",
            slug="lando-norris",
            name="Lando Norris",
            value="Lando Norris",
        ),
        _alias(
            mclaren_id,
            entity_type="team",
            slug="mclaren",
            name="McLaren",
            value="McLaren",
        ),
    ]

    result = classify_source_item_entities(
        SourceItemText(
            title="Lando Norris: McLaren driver reacts to Monaco Sprint news",
            season=2026,
        ),
        aliases,
    )
    by_slug = {item.slug: item for item in result}

    assert by_slug["lando-norris"].relation_type == "subject"
    assert by_slug["mclaren"].relation_type == "directly_involved"
