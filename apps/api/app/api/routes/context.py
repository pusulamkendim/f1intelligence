from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.facets import ContextFacetNotSupportedError, read_context_facet
from app.context.resolver import ContextNotFoundError, build_context
from app.db.session import get_db
from app.schemas.context import ContextFacetPage, ContextResponse, ContextTargetType

router = APIRouter(prefix="/api/v1/context", tags=["context"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/{target_type}/{key}/facets/{facet}", response_model=ContextFacetPage)
async def get_context_facet(
    target_type: ContextTargetType,
    key: str,
    facet: str,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ContextFacetPage:
    try:
        return await read_context_facet(
            db,
            target_type,
            key,
            facet,
            limit=limit,
            offset=offset,
        )
    except (ContextNotFoundError, ContextFacetNotSupportedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


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
