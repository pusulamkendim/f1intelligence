from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.resolver import ContextNotFoundError, build_context
from app.db.session import get_db
from app.schemas.context import ContextResponse, ContextTargetType

router = APIRouter(prefix="/api/v1/context", tags=["context"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/{target_type}/{key}", response_model=ContextResponse)
async def get_context(
    target_type: ContextTargetType,
    key: str,
    db: DbSession,
) -> ContextResponse:
    try:
        return await build_context(db, target_type, key)
    except ContextNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
