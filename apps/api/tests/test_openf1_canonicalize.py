from app.ingestion.openf1_canonicalize import _slugify_driver_name


def test_slugify_driver_name_is_stable_for_openf1_names() -> None:
    assert _slugify_driver_name("Dino BEGANOVIC") == "dino-beganovic"
    assert _slugify_driver_name("Nico HÜLKENBERG") == "nico-hulkenberg"


def test_slugify_driver_name_collapses_provider_whitespace_and_punctuation() -> None:
    assert _slugify_driver_name("  Example  DRIVER Jr. ") == "example-driver-jr"
