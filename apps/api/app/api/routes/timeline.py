from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.timeline import UnifiedTimelineResponse
from app.timeline.service import build_unified_timeline

router = APIRouter(prefix="/api/v1/timeline", tags=["timeline"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=UnifiedTimelineResponse)
async def get_timeline(
    db: DbSession,
    season: Annotated[int, Query(ge=1950, le=2100)],
    race: str | None = None,
    session: str | None = None,
    driver: str | None = None,
    lap: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> UnifiedTimelineResponse:
    return await build_unified_timeline(
        db,
        season=season,
        race_key=race,
        session_code=session,
        driver_key=driver,
        lap_number=lap,
        limit=limit,
    )
