from decimal import Decimal

from app.ingestion.jolpica import JolpicaConstructorStanding, JolpicaDriverStanding
from app.ingestion.jolpica_hashes import constructor_standings_hash, driver_standings_hash


def test_driver_hash_is_order_independent_and_changes_with_points() -> None:
    first = JolpicaDriverStanding(
        position=1,
        points=Decimal("25"),
        wins=1,
        driver_id="driver-a",
        given_name="A",
        family_name="Driver",
        permanent_number=1,
        code="AAA",
        constructor_ids=("team-a",),
    )
    second = JolpicaDriverStanding(
        position=2,
        points=Decimal("18"),
        wins=0,
        driver_id="driver-b",
        given_name="B",
        family_name="Driver",
        permanent_number=2,
        code="BBB",
        constructor_ids=("team-b",),
    )
    assert driver_standings_hash([first, second]) == driver_standings_hash([second, first])

    changed = JolpicaDriverStanding(**{**first.__dict__, "points": Decimal("26")})
    assert driver_standings_hash([first, second]) != driver_standings_hash([changed, second])


def test_constructor_hash_is_order_independent() -> None:
    first = JolpicaConstructorStanding(1, Decimal("43"), 1, "team-a", "Team A", None)
    second = JolpicaConstructorStanding(2, Decimal("27"), 0, "team-b", "Team B", None)
    assert constructor_standings_hash([first, second]) == constructor_standings_hash(
        [second, first]
    )
