from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.ingestion.run_media_discovery import (
    _normalize_media_context,
    _race_id_from_classifications,
)


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _CaptureSession:
    def __init__(self, race_id):
        self.race_id = race_id
        self.calls = []

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return _ScalarResult(self.race_id)


def test_media_context_expands_common_gp_shorthand() -> None:
    assert _normalize_media_context(
        "Photos of Friday Practice before the 2026 Italian F1 GP"
    ) == "Photos of Friday Practice before the 2026 Italian Grand Prix"
    assert _normalize_media_context(
        "2026 British GP FP1 Results"
    ) == "2026 British Grand Prix FP1 Results"


@pytest.mark.asyncio
async def test_media_race_lookup_uses_canonical_races_entity_id() -> None:
    entity_id = uuid4()
    race_id = uuid4()
    session = _CaptureSession(race_id)
    classifications = (
        SimpleNamespace(entity_type="race", entity_id=entity_id),
    )

    resolved = await _race_id_from_classifications(session, classifications)

    assert resolved == race_id
    sql, params = session.calls[0]
    assert "WHERE entity_id = :entity_id" in sql
    assert "canonical_entity_id" not in sql
    assert params == {"entity_id": entity_id}
