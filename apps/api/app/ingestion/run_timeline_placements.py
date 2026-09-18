from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import text

from app.db.session import SessionLocal
from app.timeline.placement import refresh_story_timeline_placement


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Place canonical stories on the unified F1 timeline"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="optional maximum canonical stories; omit for a full backfill",
    )
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    async with SessionLocal() as session:
        async with session.begin():
            if args.limit is None:
                result = await session.execute(
                    text(
                        """
                        SELECT id
                        FROM stories
                        WHERE merged_into_story_id IS NULL
                        ORDER BY COALESCE(
                            last_published_at,
                            last_observed_at,
                            updated_at
                        ) DESC,
                        id
                        """
                    )
                )
            else:
                result = await session.execute(
                    text(
                        """
                        SELECT id
                        FROM stories
                        WHERE merged_into_story_id IS NULL
                        ORDER BY COALESCE(
                            last_published_at,
                            last_observed_at,
                            updated_at
                        ) DESC,
                        id
                        LIMIT :limit
                        """
                    ),
                    {"limit": max(1, args.limit)},
                )
            story_ids = list(result.scalars().all())
            for story_id in story_ids:
                await refresh_story_timeline_placement(session, story_id)

            audit = await session.execute(
                text(
                    """
                    SELECT
                        COUNT(*)::int AS placements,
                        COUNT(*) FILTER (WHERE precision = 'season')::int
                            AS season,
                        COUNT(*) FILTER (WHERE precision = 'race')::int
                            AS race,
                        COUNT(*) FILTER (WHERE precision = 'session')::int
                            AS session,
                        COUNT(*) FILTER (WHERE precision = 'stint')::int
                            AS stint,
                        COUNT(*) FILTER (WHERE precision = 'lap')::int
                            AS lap,
                        COUNT(*) FILTER (WHERE precision = 'timestamp')::int
                            AS timestamp,
                        COUNT(*) FILTER (
                            WHERE temporal_relation = 'scheduled_for'
                        )::int AS scheduled_for,
                        COUNT(*) FILTER (
                            WHERE temporal_relation = 'effective_from'
                        )::int AS effective_from
                    FROM timeline_placements
                    WHERE item_type = 'story'
                      AND match_method = 'story_coordinate_v1'
                    """
                )
            )
            payload = dict(audit.mappings().one())
            payload["stories_processed"] = len(story_ids)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    asyncio.run(async_main())
