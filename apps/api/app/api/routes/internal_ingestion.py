from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.ingestion import (
    IngestionEntity,
    IngestionQueue,
    IngestionQueueCounts,
    IngestionQueueItem,
)

router = APIRouter(prefix="/api/v1/internal/ingestion", tags=["internal-ingestion"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
QueueStatus = Literal["attached", "unmatched", "ambiguous", "filtered"]


def _require_internal_environment() -> None:
    if get_settings().app_env == "production":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get("/queue", response_model=IngestionQueue)
async def get_ingestion_queue(
    db: DbSession,
    item_status: Annotated[QueueStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
) -> IngestionQueue:
    _require_internal_environment()

    counts_result = await db.execute(
        text(
            """
            SELECT status, COUNT(*)::int AS count
            FROM ingestion_items
            WHERE status IN ('attached', 'unmatched', 'ambiguous', 'filtered')
            GROUP BY status
            """
        )
    )
    counts = IngestionQueueCounts()
    for row in counts_result.mappings().all():
        setattr(counts, row["status"], row["count"])

    items_result = await db.execute(
        text(
            """
            SELECT
                ii.id,
                src.key AS source_key,
                src.name AS source_name,
                src.source_type,
                ii.external_id,
                ii.source_url,
                ii.title,
                ii.published_at,
                ii.status,
                ii.match_score,
                ii.ingested_at,
                s.slug AS matched_story_slug,
                s.title AS matched_story_title
            FROM ingestion_items ii
            JOIN ingestion_sources src ON src.id = ii.source_id
            LEFT JOIN stories s ON s.id = ii.matched_story_id
            WHERE (:item_status IS NULL OR ii.status = :item_status)
            ORDER BY COALESCE(ii.published_at, ii.ingested_at) DESC, ii.ingested_at DESC
            LIMIT :limit
            """
        ),
        {"item_status": item_status, "limit": limit},
    )
    item_rows = items_result.mappings().all()

    items: list[IngestionQueueItem] = []
    for row in item_rows:
        entities_result = await db.execute(
            text(
                """
                SELECT
                    e.id,
                    e.entity_type,
                    e.slug,
                    e.display_name,
                    iie.matched_alias,
                    iie.confidence
                FROM ingestion_item_entities iie
                JOIN entities e ON e.id = iie.entity_id
                WHERE iie.ingestion_item_id = :item_id
                ORDER BY e.entity_type, e.display_name
                """
            ),
            {"item_id": row["id"]},
        )
        entities = [
            IngestionEntity(**dict(entity_row))
            for entity_row in entities_result.mappings().all()
        ]
        items.append(IngestionQueueItem(**dict(row), entities=entities))

    return IngestionQueue(counts=counts, items=items)
