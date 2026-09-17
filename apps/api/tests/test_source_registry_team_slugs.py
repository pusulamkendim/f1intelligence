from app.ingestion.source_registry import SOURCE_BY_KEY


def test_haas_source_context_uses_canonical_team_slug() -> None:
    assert SOURCE_BY_KEY["team_haas"].team_slug == "haas"
