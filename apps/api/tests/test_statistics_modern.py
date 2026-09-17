from app.statistics.modern import (
    LapMetricInput,
    StintMetricInput,
    aggregate_modern_race_metrics,
)


def test_modern_metrics_ignore_pit_out_and_invalid_laps() -> None:
    metrics = aggregate_modern_race_metrics(
        [
            LapMetricInput(1, 92.0),
            LapMetricInput(2, 91.0),
            LapMetricInput(3, 120.0, is_pit_out_lap=True),
            LapMetricInput(4, None),
        ],
        [
            StintMetricInput(1, 1, 12, "MEDIUM", 0),
            StintMetricInput(2, 13, 30, "HARD", 0),
        ],
    )
    assert metrics.timed_laps == 2
    assert metrics.best_lap_seconds == 91.0
    assert metrics.median_lap_seconds == 91.5
    assert metrics.average_lap_seconds == 91.5
    assert metrics.stints == 2
    assert metrics.longest_stint_laps == 18
    assert metrics.compounds_used == ("HARD", "MEDIUM")


def test_modern_metrics_are_empty_safe() -> None:
    metrics = aggregate_modern_race_metrics([], [])
    assert metrics.timed_laps == 0
    assert metrics.best_lap_seconds is None
    assert metrics.longest_stint_laps is None
    assert metrics.compounds_used == ()
