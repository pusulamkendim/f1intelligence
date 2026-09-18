from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.qualifying import QualifyingSegmentNotFoundError, qualifying_segment
from app.schemas.qualifying import QualifyingSegmentCode, QualifyingSegmentResponse

router = APIRouter(prefix="/api/v1/qualifying", tags=["qualifying"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/races/{race_key}/segments/{segment_code}",
    response_model=QualifyingSegmentResponse,
)
async def get_qualifying_segment(
    race_key: str,
    segment_code: QualifyingSegmentCode,
    db: DbSession,
) -> QualifyingSegmentResponse:
    try:
        return await qualifying_segment(
            db,
            race_key=race_key,
            segment_code=segment_code,
        )
    except QualifyingSegmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
