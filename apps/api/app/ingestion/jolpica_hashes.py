from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from app.ingestion.jolpica import JolpicaConstructorStanding, JolpicaDriverStanding


def _hash_rows(rows: list[dict[str, object]]) -> str:
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def driver_standings_hash(rows: Iterable[JolpicaDriverStanding]) -> str:
    canonical = [
        {
            "constructor_ids": sorted(row.constructor_ids),
            "driver_id": row.driver_id,
            "points": str(row.points),
            "position": row.position,
            "wins": row.wins,
        }
        for row in rows
    ]
    canonical.sort(key=lambda row: (int(row["position"]), str(row["driver_id"])))
    return _hash_rows(canonical)


def constructor_standings_hash(rows: Iterable[JolpicaConstructorStanding]) -> str:
    canonical = [
        {
            "constructor_id": row.constructor_id,
            "points": str(row.points),
            "position": row.position,
            "wins": row.wins,
        }
        for row in rows
    ]
    canonical.sort(key=lambda row: (int(row["position"]), str(row["constructor_id"])))
    return _hash_rows(canonical)
