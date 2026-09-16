from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.story import EvidenceItem, StoryDetail, StoryEntity, StorySummary

router = APIRouter(prefix="/api/v1/stories", tags=["stories"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[StorySummary])
async def list_stories(db: DbSession) -> list[StorySummary]:
    result = await db.execute(
        text(
            """
            SELECT
                s.id,
                s.slug,
                s.title,
                s.summary,
                s.status,
                s.updated_at,
                COUNT(e.id)::int AS evidence_count,
                MAX(COALESCE(e.published_at, e.captured_at)) AS latest_evidence_at
            FROM stories s
            LEFT JOIN evidence e ON e.story_id = s.id
            GROUP BY s.id
            ORDER BY s.updated_at DESC, s.title ASC
            """
        )
    )

    return [StorySummary(**dict(row)) for row in result.mappings().all()]


@router.get("/{slug}", response_model=StoryDetail)
async def get_story(slug: str, db: DbSession) -> StoryDetail:
    story_result = await db.execute(
        text(
            """
            SELECT
                id,
                slug,
                title,
                summary,
                status,
                significance,
                confidence,
                what_changed,
                why_it_matters,
                what_to_watch_next,
                created_at,
                updated_at
            FROM stories
            WHERE slug = :slug
            """
        ),
        {"slug": slug},
    )
    story = story_result.mappings().first()

    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    entity_result = await db.execute(
        text(
            """
            SELECT
                e.id,
                e.entity_type,
                e.slug,
                e.display_name,
                se.relation_type,
                se.confidence,
                se.match_method,
                se.matched_alias
            FROM story_entities se
            JOIN entities e ON e.id = se.entity_id
            WHERE se.story_id = :story_id
            ORDER BY
                CASE e.entity_type
                    WHEN 'race' THEN 1
                    WHEN 'team' THEN 2
                    WHEN 'person' THEN 3
                    ELSE 4
                END,
                e.display_name ASC
            """
        ),
        {"story_id": story["id"]},
    )
    entity_items = [StoryEntity(**dict(row)) for row in entity_result.mappings().all()]

    evidence_result = await db.execute(
        text(
            """
            SELECT
                id,
                source_type,
                source_name,
                source_url,
                published_at,
                captured_at,
                author_or_speaker,
                normalized_claim,
                raw_excerpt_or_reference,
                reliability_class,
                directness,
                raw_metadata
            FROM evidence
            WHERE story_id = :story_id
            ORDER BY COALESCE(published_at, captured_at) DESC, created_at DESC
            """
        ),
        {"story_id": story["id"]},
    )

    evidence_items: list[EvidenceItem] = []
    for row in evidence_result.mappings().all():
        metadata: dict[str, Any] = dict(row["raw_metadata"] or {})
        evidence_items.append(
            EvidenceItem(
                id=row["id"],
                presentation_type=metadata.get("presentation_type", "documented_fact"),
                source_type=row["source_type"],
                source_name=row["source_name"],
                source_url=row["source_url"],
                published_at=row["published_at"],
                captured_at=row["captured_at"],
                author_or_speaker=row["author_or_speaker"],
                normalized_claim=row["normalized_claim"],
                raw_excerpt_or_reference=row["raw_excerpt_or_reference"],
                reliability_class=row["reliability_class"],
                directness=row["directness"],
                metadata=metadata,
            )
        )

    return StoryDetail(
        **dict(story),
        entities=entity_items,
        evidence=evidence_items,
    )
