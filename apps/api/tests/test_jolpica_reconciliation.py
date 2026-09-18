from datetime import date
from uuid import UUID

import pytest

from app.ingestion.jolpica import (
    JolpicaConstructorIdentity,
    JolpicaDriverIdentity,
    JolpicaDriverStanding,
)
from app.ingestion.jolpica_reconciliation import (
    AmbiguousEntityMatch,
    CanonicalCandidate,
    ProviderMapping,
    _constructor_identity_match,
    _driver_identity_match,
    _mapping_method,
    _season_roster_pairs,
)


def _driver(
    driver_id: str = "historical_driver",
    given_name: str = "Historical",
    family_name: str = "Driver",
    birth_date: date | None = date(1990, 1, 1),
) -> JolpicaDriverIdentity:
    return JolpicaDriverIdentity(
        driver_id=driver_id,
        given_name=given_name,
        family_name=family_name,
        date_of_birth=birth_date,
        nationality="British",
        permanent_number=None,
        code=None,
        source_url="https://example.test/driver",
    )


def test_known_provider_mapping_needs_no_extension() -> None:
    mapping = ProviderMapping(
        entity_id=UUID("12345678-1234-5678-1234-567812345678"),
        valid_from_season=2020,
        valid_to_season=2026,
    )

    assert _mapping_method(mapping, 2024) == "exact_provider_id"


def test_provider_mapping_extends_for_older_season() -> None:
    mapping = ProviderMapping(
        entity_id=UUID("12345678-1234-5678-1234-567812345678"),
        valid_from_season=2025,
        valid_to_season=2026,
    )

    assert _mapping_method(mapping, 2024) == "provider_validity_extension"


def test_new_historical_driver_has_no_existing_identity_match() -> None:
    identity = _driver()

    assert _driver_identity_match(identity, []) is None


def test_driver_exact_identity_accepts_missing_canonical_birth_date() -> None:
    identity = _driver()
    candidate = CanonicalCandidate(
        entity_id=UUID("12345678-1234-5678-1234-567812345678"),
        slug="historical-driver",
        display_name="Historical Driver",
        birth_date=None,
    )

    assert _driver_identity_match(identity, [candidate]) == candidate


def test_driver_birth_date_conflict_fails_fast() -> None:
    identity = _driver()
    candidate = CanonicalCandidate(
        entity_id=UUID("12345678-1234-5678-1234-567812345678"),
        slug="historical-driver",
        display_name="Historical Driver",
        birth_date=date(1980, 1, 1),
    )

    with pytest.raises(
        AmbiguousEntityMatch,
        match="birth date",
    ):
        _driver_identity_match(identity, [candidate])


def test_duplicate_driver_identity_fails_fast() -> None:
    identity = _driver()
    candidates = [
        CanonicalCandidate(
            entity_id=UUID("12345678-1234-5678-1234-567812345678"),
            slug="historical-driver-a",
            display_name="Historical Driver",
        ),
        CanonicalCandidate(
            entity_id=UUID("22345678-1234-5678-1234-567812345678"),
            slug="historical-driver-b",
            display_name="Historical Driver",
        ),
    ]

    with pytest.raises(
        AmbiguousEntityMatch,
        match="ambiguous driver identity",
    ):
        _driver_identity_match(identity, candidates)


def test_unknown_historical_constructor_stays_distinct() -> None:
    identity = JolpicaConstructorIdentity(
        constructor_id="historical_team",
        name="Historical Racing",
        nationality="British",
        source_url="https://example.test/team",
    )

    assert _constructor_identity_match(identity, []) is None


def test_constructor_exact_identity_is_conservative() -> None:
    identity = JolpicaConstructorIdentity(
        constructor_id="historical_team",
        name="Historical Racing",
        nationality="British",
        source_url="https://example.test/team",
    )
    candidate = CanonicalCandidate(
        entity_id=UUID("12345678-1234-5678-1234-567812345678"),
        slug="historical-racing",
        display_name="Historical Racing",
    )

    assert _constructor_identity_match(identity, [candidate]) == candidate


def test_midseason_driver_can_have_multiple_team_participations() -> None:
    standings = [
        JolpicaDriverStanding(
            position=10,
            points=0,
            wins=0,
            driver_id="driver-a",
            given_name="Driver",
            family_name="A",
            permanent_number=None,
            code=None,
            constructor_ids=("team-a", "team-b"),
        )
    ]

    assert _season_roster_pairs(standings) == {
        ("driver-a", "team-a"),
        ("driver-a", "team-b"),
    }
