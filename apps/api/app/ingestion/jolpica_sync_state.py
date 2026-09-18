from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def imported_result_rounds(session: AsyncSession, season: int) -> set[int]:
    result = await session.execute(
        text(
            """
            SELECT r.round
            FROM races r
            WHERE r.season = :season
              AND r.round IS NOT NULL
              AND EXISTS (
                  SELECT 1
                  FROM race_results rr
                  WHERE rr.race_id = r.id AND rr.provider = 'jolpica'
              )
              AND EXISTS (
                  SELECT 1
                  FROM qualifying_results qr
                  WHERE qr.race_id = r.id AND qr.provider = 'jolpica'
              )
            """
        ),
        {"season": season},
    )
    return {int(row.round) for row in result}



async def imported_sprint_rounds(
    session: AsyncSession,
    season: int,
) -> set[int]:
    result = await session.execute(
        text(
            """
            SELECT r.round
            FROM races r
            WHERE r.season = :season
              AND r.round IS NOT NULL
              AND EXISTS (
                  SELECT 1
                  FROM sprint_results sr
                  WHERE sr.race_id = r.id
                    AND sr.provider = 'jolpica'
              )
            """
        ),
        {"season": season},
    )
    return {int(row.round) for row in result}
