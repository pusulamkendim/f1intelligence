from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict

from app.db.session import SessionLocal
from app.ingestion.story_materialization import materialize_existing_source_items


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize source items into canonical stories"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "optional maximum source items to evaluate in chronological order; "
            "omit for a full rematerialization"
        ),
    )
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    async with SessionLocal() as session:
        async with session.begin():
            stats = await materialize_existing_source_items(
                session,
                limit=max(1, args.limit) if args.limit is not None else None,
            )
    print(json.dumps(asdict(stats), indent=2))


if __name__ == "__main__":
    asyncio.run(async_main())
