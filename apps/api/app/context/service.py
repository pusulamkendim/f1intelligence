from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.context.aggregation import build_related, load_timeline
from app.context.resolver import load_facets, load_provenance, load_relations, resolve_target
from app.schemas.context import ContextResponse, ContextTargetType


async def build_context(
    db: AsyncSession,
    target_type: ContextTargetType,
    key: str,
) -> ContextResponse:
    target = await resolve_target(db, target_type, key)
    relations = await load_relations(db, target)
    facets = await load_facets(db, target)
    provenance = await load_provenance(db, target)
    timeline = await load_timeline(db, target)
    related = build_related(target, relations, timeline)
    return ContextResponse(
        target=target.target,
        relations=relations,
        facets=facets,
        timeline=timeline,
        related=related,
        provenance=provenance,
    )
