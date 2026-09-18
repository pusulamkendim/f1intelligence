from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.qualifying import (
    QualifyingSegmentCode,
    QualifyingSegmentDriverResult,
    QualifyingSegmentResponse,
)


class QualifyingSegmentNotFoundError(ValueError):
    pass


async def qualifying_segment(
    db: AsyncSession,
    *,
    race_key: str,
    segment_code: QualifyingSegmentCode,
) -> QualifyingSegmentResponse:
    segment_result = await db.execute(
        text(
            """
            SELECT
                r.slug AS race_key,
                r.official_name AS race_label,
                rs.id::text AS session_id,
                sg.id::text AS segment_id,
                sg.segment_code,
                sg.segment_name AS segment_label,
                sg.sequence,
                sg.provider,
                sg.source_url
            FROM races r
            JOIN race_sessions rs
              ON rs.race_id = r.id
             AND rs.session_code = 'qualifying'
             AND rs.is_cancelled = false
            JOIN session_segments sg
              ON sg.session_id = rs.id
             AND sg.segment_type = 'qualifying_phase'
            WHERE (r.slug = :race_key OR r.id::text = :race_key)
              AND sg.segment_code = :segment_code
            LIMIT 1
            """
        ),
        {"race_key": race_key, "segment_code": segment_code},
    )
    segment = segment_result.mappings().first()
    if segment is None:
        raise QualifyingSegmentNotFoundError(
            f"qualifying segment not found: {race_key}/{segment_code}"
        )

    rows_result = await db.execute(
        text(
            """
            SELECT
                qsr.driver_number,
                de.slug AS driver_key,
                de.display_name AS driver_label,
                te.slug AS team_key,
                te.display_name AS team_label,
                qsr.segment_position,
                qsr.final_qualifying_position,
                qsr.duration_seconds,
                qsr.gap_to_leader_seconds,
                qsr.reached_next_segment
            FROM qualifying_segment_results qsr
            LEFT JOIN entities de ON de.id = qsr.driver_entity_id
            LEFT JOIN entities te ON te.id = qsr.team_entity_id
            WHERE qsr.segment_id = CAST(:segment_id AS uuid)
            ORDER BY
                qsr.segment_position NULLS LAST,
                qsr.final_qualifying_position NULLS LAST,
                qsr.driver_number
            """
        ),
        {"segment_id": segment["segment_id"]},
    )

    return QualifyingSegmentResponse(
        **dict(segment),
        rows=[
            QualifyingSegmentDriverResult(**dict(row))
            for row in rows_result.mappings().all()
        ],
    )
