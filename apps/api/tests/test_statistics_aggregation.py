from decimal import Decimal

from app.statistics.aggregation import (
    DriverQualifying,
    DriverResult,
    DriverSeasonStanding,
    DriverSprintResult,
    aggregate_driver_statistics,
)


def test_driver_statistics_separate_gp_and_sprint_semantics() -> None:
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
        [
            DriverSeasonStanding(
                2025,
                3,
                2,
                Decimal("55"),
                True,
            )
        ],
        [
            DriverSprintResult(
                2025,
                2,
                1,
                2,
                Decimal("8"),
                "Finished",
            )
        ],
    )

    assert stats.race_entries == 3
    assert stats.starts == 3
    assert stats.wins == 1
    assert stats.podiums == 2
    assert stats.poles == 1
    assert stats.qualifying_p1s == 1
    assert stats.fastest_laps == 1

    assert stats.race_points == Decimal("47")
    assert stats.sprint_points == Decimal("8")
    assert stats.points == Decimal("55")
    assert stats.points_adjustment == Decimal("0")

    assert stats.classified_finishes == 2
    assert stats.dnfs == 1
    assert stats.dns == 0
    assert stats.dsqs == 0

    assert stats.sprint_entries == 1
    assert stats.sprint_starts == 1
    assert stats.sprint_wins == 1
    assert stats.sprint_top3s == 1

    assert stats.average_grid == 3
    assert stats.average_finish == 1.5
    assert stats.average_classification_position == 11 / 3
    assert stats.win_rate == 1 / 3
    assert stats.podium_rate == 2 / 3
    assert stats.positions_gained == -2
    assert stats.championships == 0


def test_official_standings_points_capture_adjustments() -> None:
    stats = aggregate_driver_statistics(
        [
            DriverResult(
                2024,
                1,
                1,
                1,
                Decimal("25"),
                "Finished",
                1,
            )
        ],
        standings=[
            DriverSeasonStanding(
                2024,
                1,
                1,
                Decimal("22"),
                True,
            )
        ],
    )

    assert stats.race_points == Decimal("25")
    assert stats.points == Decimal("22")
    assert stats.points_adjustment == Decimal("-3")
    assert stats.championships == 1


def test_incomplete_season_leader_is_not_counted_as_champion() -> None:
    stats = aggregate_driver_statistics(
        [
            DriverResult(
                2026,
                1,
                1,
                1,
                Decimal("25"),
                "Finished",
                None,
            )
        ],
        standings=[
            DriverSeasonStanding(
                2026,
                1,
                1,
                Decimal("25"),
                False,
            )
        ],
    )

    assert stats.points == Decimal("25")
    assert stats.championships == 0


def test_dns_dsq_dnf_and_grid_zero_have_distinct_semantics() -> None:
    stats = aggregate_driver_statistics(
        [
            DriverResult(
                2025,
                1,
                None,
                0,
                Decimal("0"),
                "Did not start",
                None,
            ),
            DriverResult(
                2025,
                2,
                20,
                4,
                Decimal("0"),
                "Disqualified",
                None,
            ),
            DriverResult(
                2025,
                3,
                18,
                5,
                Decimal("0"),
                "Engine",
                None,
            ),
            DriverResult(
                2025,
                4,
                10,
                6,
                Decimal("1"),
                "+1 Lap",
                None,
            ),
        ]
    )

    assert stats.race_entries == 4
    assert stats.starts == 3
    assert stats.dns == 1
    assert stats.dsqs == 1
    assert stats.dnfs == 1
    assert stats.classified_finishes == 1
    assert stats.average_grid == 5
    assert stats.average_finish == 10
    assert stats.average_classification_position == 16
    assert stats.positions_gained == -33


def test_points_fall_back_to_event_totals_without_standings() -> None:
    stats = aggregate_driver_statistics(
        [
            DriverResult(
                2025,
                1,
                1,
                1,
                Decimal("25"),
                "Finished",
                None,
            )
        ],
        sprints=[
            DriverSprintResult(
                2025,
                1,
                2,
                1,
                Decimal("7"),
                "Finished",
            )
        ],
    )

    assert stats.points == Decimal("32")
    assert stats.points_adjustment == Decimal("0")


def test_empty_statistics_do_not_invent_rates_or_averages() -> None:
    stats = aggregate_driver_statistics([])

    assert stats.race_entries == 0
    assert stats.starts == 0
    assert stats.average_grid is None
    assert stats.average_finish is None
    assert stats.average_classification_position is None
    assert stats.win_rate is None
    assert stats.podium_rate is None
    assert stats.championships == 0



def test_poles_follow_main_race_grid_while_qualifying_p1_is_separate() -> None:
    stats = aggregate_driver_statistics(
        [
            DriverResult(
                2021,
                10,
                1,
                1,
                Decimal("25"),
                "Finished",
                None,
            )
        ],
        qualifying=[
            DriverQualifying(
                2021,
                10,
                2,
            )
        ],
    )

    assert stats.poles == 1
    assert stats.qualifying_p1s == 0



def test_pole_is_retained_when_driver_does_not_start() -> None:
    stats = aggregate_driver_statistics(
        [
            DriverResult(
                2025,
                1,
                None,
                1,
                Decimal("0"),
                "Did not start",
                None,
            )
        ]
    )

    assert stats.poles == 1
    assert stats.starts == 0



def test_points_extend_standings_with_newer_sprint_before_gp_result() -> None:
    stats = aggregate_driver_statistics(
        [
            DriverResult(
                2026,
                10,
                2,
                2,
                Decimal("18"),
                "Finished",
                None,
            )
        ],
        standings=[
            DriverSeasonStanding(
                2026,
                10,
                1,
                Decimal("210"),
                False,
            )
        ],
        sprints=[
            DriverSprintResult(
                2026,
                11,
                1,
                1,
                Decimal("8"),
                "Finished",
            )
        ],
    )

    assert stats.points == Decimal("218")
    assert stats.race_points == Decimal("18")
    assert stats.sprint_points == Decimal("8")
    assert stats.points_adjustment == Decimal("192")
