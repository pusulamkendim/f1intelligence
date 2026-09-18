from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.visualizations import VisualizationResponse
from app.visualizations.historical import (
    driver_season_results,
    race_classification,
    season_standings,
)
from app.visualizations.service import (
    VisualizationNotFoundError,
    race_visualization,
)

router = APIRouter(prefix="/api/v1/visualizations", tags=["visualizations"])
DbSession = Annotated[AsyncSession, Depends(get_db)]

RaceChart = Literal[
    "positions",
    "lap-times",
    "stints",
    "sectors",
    "speeds",
    "intervals",
    "pit-stops",
    "weather",
    "overtakes",
    "starting-grid",
    "race-result",
    "qualifying-result",
]
StandingsChart = Literal["driver-standings", "constructor-standings"]


@router.get(
    "/races/{race_key}/{chart}",
    response_model=VisualizationResponse,
)
async def race_chart(
    race_key: str,
    chart: RaceChart,
    db: DbSession,
    session_code: Annotated[str, Query()] = "race",
) -> VisualizationResponse:
    try:
        if chart in {"race-result", "qualifying-result"}:
            return await race_classification(db, race_key, chart)
        return await race_visualization(db, race_key, session_code, chart)
    except VisualizationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/seasons/{season}/{chart}",
    response_model=VisualizationResponse,
)
async def standings_chart(
    season: int,
    chart: StandingsChart,
    db: DbSession,
) -> VisualizationResponse:
    try:
        return await season_standings(db, season, chart)
    except VisualizationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/seasons/{season}/drivers/{driver_key}/results",
    response_model=VisualizationResponse,
)
async def driver_results_chart(
    season: int,
    driver_key: str,
    db: DbSession,
) -> VisualizationResponse:
    try:
        return await driver_season_results(db, season, driver_key)
    except VisualizationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
