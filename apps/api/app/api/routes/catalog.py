from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.catalog import RaceDetail, RaceSummary, TeamDetail, TeamMember, TeamSummary
from app.schemas.story import StorySummary

router = APIRouter(tags=["catalog"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def _linked_stories(db: AsyncSession, entity_id: Any) -> list[StorySummary]:
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
            FROM story_entities se
            JOIN stories s ON s.id = se.story_id
            LEFT JOIN evidence e ON e.story_id = s.id
            WHERE se.entity_id = :entity_id
            GROUP BY s.id
            ORDER BY s.updated_at DESC, s.title ASC
            """
        ),
        {"entity_id": entity_id},
    )
    return [StorySummary(**dict(row)) for row in result.mappings().all()]


@router.get("/api/v1/teams", response_model=list[TeamSummary])
async def list_teams(db: DbSession) -> list[TeamSummary]:
    result = await db.execute(
        text(
            """
            SELECT
                t.id,
                t.slug,
                t.name,
                t.active_season,
                COUNT(DISTINCT CASE
                    WHEN tpr.role = 'driver'
                     AND (t.active_season IS NULL OR tpr.season = t.active_season)
                    THEN tpr.person_id
                END)::int AS driver_count,
                COUNT(DISTINCT se.story_id)::int AS story_count
            FROM teams t
            LEFT JOIN team_person_roles tpr ON tpr.team_id = t.id
            LEFT JOIN story_entities se ON se.entity_id = t.entity_id
            GROUP BY t.id
            ORDER BY t.name ASC
            """
        )
    )
    return [TeamSummary(**dict(row)) for row in result.mappings().all()]


@router.get("/api/v1/teams/{slug}", response_model=TeamDetail)
async def get_team(slug: str, db: DbSession) -> TeamDetail:
    result = await db.execute(
        text(
            """
            SELECT id, slug, name, active_season, entity_id
            FROM teams
            WHERE slug = :slug
            """
        ),
        {"slug": slug},
    )
    team = result.mappings().first()
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    members_result = await db.execute(
        text(
            """
            SELECT
                p.id,
                p.slug,
                p.display_name,
                tpr.role,
                tpr.season,
                tpr.car_number
            FROM team_person_roles tpr
            JOIN persons p ON p.id = tpr.person_id
            WHERE tpr.team_id = :team_id
              AND (:season IS NULL OR tpr.season = :season)
            ORDER BY
                CASE tpr.role
                    WHEN 'driver' THEN 1
                    WHEN 'team_principal' THEN 2
                    WHEN 'racing_director' THEN 3
                    WHEN 'managing_director' THEN 4
                    WHEN 'executive_advisor' THEN 5
                    ELSE 6
                END,
                p.display_name ASC
            """
        ),
        {"team_id": team["id"], "season": team["active_season"]},
    )
    members = [TeamMember(**dict(row)) for row in members_result.mappings().all()]
    stories = await _linked_stories(db, team["entity_id"]) if team["entity_id"] else []

    return TeamDetail(
        id=team["id"],
        slug=team["slug"],
        name=team["name"],
        active_season=team["active_season"],
        members=members,
        stories=stories,
    )


@router.get("/api/v1/races", response_model=list[RaceSummary])
async def list_races(db: DbSession) -> list[RaceSummary]:
    result = await db.execute(
        text(
            """
            SELECT
                r.id,
                r.season,
                r.round,
                r.slug,
                r.official_name,
                r.circuit,
                r.country,
                r.start_at,
                r.weekend_start_date,
                r.weekend_end_date,
                r.status,
                COUNT(DISTINCT se.story_id)::int AS story_count
            FROM races r
            LEFT JOIN story_entities se ON se.entity_id = r.entity_id
            GROUP BY r.id
            ORDER BY r.season DESC, r.round ASC NULLS LAST, r.official_name ASC
            """
        )
    )
    return [RaceSummary(**dict(row)) for row in result.mappings().all()]


@router.get("/api/v1/races/{slug}", response_model=RaceDetail)
async def get_race(slug: str, db: DbSession) -> RaceDetail:
    result = await db.execute(
        text(
            """
            SELECT
                r.id,
                r.season,
                r.round,
                r.slug,
                r.official_name,
                r.circuit,
                r.country,
                r.start_at,
                r.weekend_start_date,
                r.weekend_end_date,
                r.status,
                r.synthesis,
                r.entity_id,
                COUNT(DISTINCT se.story_id)::int AS story_count
            FROM races r
            LEFT JOIN story_entities se ON se.entity_id = r.entity_id
            WHERE r.slug = :slug
            GROUP BY r.id
            """
        ),
        {"slug": slug},
    )
    race = result.mappings().first()
    if race is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Race not found")

    stories = await _linked_stories(db, race["entity_id"]) if race["entity_id"] else []
    return RaceDetail(
        id=race["id"],
        season=race["season"],
        round=race["round"],
        slug=race["slug"],
        official_name=race["official_name"],
        circuit=race["circuit"],
        country=race["country"],
        start_at=race["start_at"],
        weekend_start_date=race["weekend_start_date"],
        weekend_end_date=race["weekend_end_date"],
        status=race["status"],
        story_count=race["story_count"],
        synthesis=race["synthesis"],
        stories=stories,
    )
