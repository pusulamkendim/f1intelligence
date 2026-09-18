from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.statistics import (
    DriverCareerStatisticsResponse,
    DriverModernRaceMetricsResponse,
    DriverSeasonStatisticsResponse,
)
from app.statistics.service import StatisticsNotFoundError, driver_modern_race_metrics, driver_statistics

router = APIRouter(prefix="/api/v1/statistics", tags=["statistics"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/drivers/{driver_key}", response_model=DriverCareerStatisticsResponse)
async def career(driver_key: str, db: DbSession):
    try:
        return await driver_statistics(db, driver_key)
    except StatisticsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/drivers/{driver_key}/seasons/{season}", response_model=DriverSeasonStatisticsResponse)
async def season(driver_key: str, season: int, db: DbSession):
    try:
        return await driver_statistics(db, driver_key, season)
    except StatisticsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/drivers/{driver_key}/races/{race_key}/modern", response_model=DriverModernRaceMetricsResponse)
async def modern_race(
    driver_key: str,
    race_key: str,
    db: DbSession,
    session_code: Annotated[str, Query()] = "race",
):
    try:
        return await driver_modern_race_metrics(db, driver_key, race_key, session_code)
    except StatisticsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
