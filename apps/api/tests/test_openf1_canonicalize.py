from app.ingestion.openf1_canonicalize import _slugify_driver_name


def test_slugify_driver_name_is_stable_for_openf1_names() -> None:
    assert _slugify_driver_name("Dino BEGANOVIC") == "dino-beganovic"
    assert _slugify_driver_name("Nico HÜLKENBERG") == "nico-hulkenberg"


def test_slugify_driver_name_collapses_provider_whitespace_and_punctuation() -> None:
    assert _slugify_driver_name("  Example  DRIVER Jr. ") == "example-driver-jr"


def test_same_person_slug_is_independent_of_session_number_or_team() -> None:
    observations = [
        {"full_name": "Example DRIVER", "driver_number": 97, "team": "Team A"},
        {"full_name": "Example DRIVER", "driver_number": 61, "team": "Team B"},
    ]
    assert {_slugify_driver_name(row["full_name"]) for row in observations} == {"example-driver"}
    assert {row["driver_number"] for row in observations} == {61, 97}
