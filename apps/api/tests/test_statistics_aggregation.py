from decimal import Decimal

from app.statistics.aggregation import (
    DriverQualifying,
    DriverResult,
    DriverSeasonStanding,
    aggregate_driver_statistics,
)


def test_driver_statistics_are_derived_deterministically_from_results() -> None:
    stats = aggregate_driver_statistics(
        [
            DriverResult(2025, 1, 1, 3, Decimal("25"), "Finished", 2),
            DriverResult(2025, 2, 2, 1, Decimal("18"), "+4.2", 1),
            DriverResult(2025, 3, 8, 5, Decimal("4"), "Collision", None),
        ],
        [
            DriverQualifying(2025, 1, 3),
            DriverQualifying(2025, 2, 1),
            DriverQualifying(2025, 3, 5),
        ],
        [DriverSeasonStanding(2024, 1), DriverSeasonStanding(2025, 2)],
    )

    assert stats.starts == 3
    assert stats.wins == 1
    assert stats.podiums == 2
    assert stats.poles == 1
    assert stats.fastest_laps == 1
    assert stats.points == Decimal("47")
    assert stats.dnfs == 1
    assert stats.average_grid == 3
    assert stats.average_finish == 11 / 3
    assert stats.win_rate == 1 / 3
    assert stats.podium_rate == 2 / 3
    assert stats.positions_gained == -2
    assert stats.championships == 1


def test_empty_statistics_do_not_invent_rates_or_averages() -> None:
    stats = aggregate_driver_statistics([])
    assert stats.starts == 0
    assert stats.average_grid is None
    assert stats.average_finish is None
    assert stats.win_rate is None
    assert stats.podium_rate is None
    assert stats.championships == 0
