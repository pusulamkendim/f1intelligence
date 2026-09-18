from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.visualizations import VisualizationResponse
from app.visualizations.service import VisualizationNotFoundError, race_visualization

router = APIRouter(prefix="/api/v1/visualizations", tags=["visualizations"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/races/{race_key}/{chart}", response_model=VisualizationResponse)
async def race_chart(
    race_key: str,
    chart: Literal["positions", "lap-times", "stints"],
    db: DbSession,
    session_code: Annotated[str, Query()] = "race",
) -> VisualizationResponse:
    try:
        return await race_visualization(db, race_key, session_code, chart)
    except VisualizationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
