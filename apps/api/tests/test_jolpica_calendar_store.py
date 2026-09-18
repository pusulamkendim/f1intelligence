from datetime import date
from decimal import Decimal

from app.ingestion.jolpica import JolpicaCircuit, JolpicaRace
from app.ingestion.jolpica_calendar_store import (
    _calendar_alias_candidates,
    _canonical_race_slug,
)


def _race(*, round_number: int, name: str = "Bahrain Grand Prix in Malaysia") -> JolpicaRace:
    return JolpicaRace(
        season=2026,
        round=round_number,
        name=name,
        race_date=date(2026, 10, 4),
        start_at=None,
        sprint_start_at=None,
        source_url="https://example.test/race",
        circuit=JolpicaCircuit(
            provider_id="sepang",
            name="Sepang International Circuit",
            locality="Sepang",
            country="Malaysia",
            latitude=Decimal("2.76083"),
            longitude=Decimal("101.738"),
            source_url="https://example.test/circuit",
        ),
    )


def test_canonical_race_slug_does_not_depend_on_mutable_round() -> None:
    round_16 = _race(round_number=16)
    round_23 = _race(round_number=23)

    assert _canonical_race_slug(round_16) == "2026-bahrain-grand-prix-in-malaysia"
    assert _canonical_race_slug(round_23) == _canonical_race_slug(round_16)


def test_calendar_alias_candidates_cover_event_and_venue_identity() -> None:
    candidates = _calendar_alias_candidates(_race(round_number=16))

    assert candidates == [
        "bahrain grand prix in malaysia",
        "sepang international circuit",
        "sepang",
    ]


def test_slugify_handles_accented_canonical_event_names() -> None:
    race = _race(round_number=20, name="Grande Prêmio de São Paulo")

    assert _canonical_race_slug(race) == "2026-grande-premio-de-sao-paulo"
