from uuid import uuid4

from app.ingestion.entity_matcher import EntityAlias
from app.ingestion.source_item_entities import SourceItemText, classify_source_item_entities
from app.ingestion.source_item_store import TeamContextPerson, build_team_context_aliases


def test_team_context_aliases_resolve_first_names_without_global_aliases() -> None:
    lando_id = uuid4()
    oscar_id = uuid4()
    mclaren_id = uuid4()
    people = [
        TeamContextPerson(
            entity_id=lando_id,
            slug="lando-norris",
            display_name="Lando Norris",
            role="driver",
            season=2026,
        ),
        TeamContextPerson(
            entity_id=oscar_id,
            slug="oscar-piastri",
            display_name="Oscar Piastri",
            role="driver",
            season=2026,
        ),
    ]
    contextual = build_team_context_aliases(people)
    assert {alias.alias for alias in contextual} == {"Lando", "Oscar"}
    assert {alias.alias_type for alias in contextual} == {"team_first_name"}

    mclaren = EntityAlias(
        entity_id=mclaren_id,
        entity_type="team",
        slug="mclaren",
        display_name="McLaren",
        alias="McLaren",
        alias_type="canonical",
        confidence=100,
        valid_from_season=2026,
    )
    result = classify_source_item_entities(
        SourceItemText(
            title="Lando and Oscar focused on the positives from Spain",
            season=2026,
            source_context_team_slug="mclaren",
        ),
        [mclaren, *contextual],
    )
    by_slug = {item.slug: item for item in result}

    assert by_slug["lando-norris"].relation_type == "subject"
    assert by_slug["oscar-piastri"].relation_type == "subject"
    assert by_slug["mclaren"].match_method == "source_context"


def test_team_context_aliases_drop_ambiguous_first_names() -> None:
    people = [
        TeamContextPerson(
            entity_id=uuid4(),
            slug="alex-one",
            display_name="Alex One",
            role="driver",
            season=2026,
        ),
        TeamContextPerson(
            entity_id=uuid4(),
            slug="alex-two",
            display_name="Alex Two",
            role="reserve",
            season=2026,
        ),
    ]

    assert build_team_context_aliases(people) == []
