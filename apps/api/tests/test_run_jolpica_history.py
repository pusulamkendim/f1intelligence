import pytest

import app.ingestion.run_jolpica_history as history


def test_historical_seasons_is_inclusive_in_both_directions() -> None:
    assert history.historical_seasons(2022, 2024) == [2022, 2023, 2024]
    assert history.historical_seasons(2024, 2022) == [2024, 2023, 2022]


@pytest.mark.asyncio
async def test_multi_season_sync_runs_every_requested_season(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[int] = []

    async def fake_sync(season: int) -> dict[str, object]:
        seen.append(season)
        return {"season": season}

    monkeypatch.setattr(history, "sync_jolpica", fake_sync)

    summaries = await history.sync_jolpica_history(2022, 2024)

    assert seen == [2022, 2023, 2024]
    assert summaries == [
        {"season": 2022},
        {"season": 2023},
        {"season": 2024},
    ]
