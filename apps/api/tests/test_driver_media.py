from uuid import uuid4

import pytest

from app.ingestion.media_source_registry import policy_for_provider
from app.ingestion.run_driver_media import (
    GROUP_PHOTOS,
    load_grid_driver_portraits,
)


class _Mappings:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return _Mappings(self._rows)


class _CaptureSession:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return _Result(self.rows)


@pytest.mark.asyncio
async def test_driver_portrait_query_uses_2026_grid_roles_and_latest_openf1_headshot() -> None:
    entity_id = uuid4()
    session = _CaptureSession(
        [
            {
                "entity_id": entity_id,
                "person_slug": "lando-norris",
                "display_name": "Lando Norris",
                "team_name": "McLaren",
                "car_number": 1,
                "headshot_reference_url": "https://example.com/lando.png",
                "source_url": "https://api.openf1.org/v1/drivers?session_key=123",
            }
        ]
    )

    rows = await load_grid_driver_portraits(session, season=2026)

    assert len(rows) == 1
    assert rows[0].entity_id == entity_id
    assert rows[0].person_slug == "lando-norris"
    assert rows[0].headshot_url == "https://example.com/lando.png"

    sql, params = session.calls[0]
    assert "tpr.role = 'driver'" in sql
    assert "tpr.season = :season" in sql
    assert "r.season = :season" in sql
    assert "headshot_reference_url" in sql
    assert "ORDER BY rs.starts_at DESC" in sql
    assert params == {"season": 2026}


def test_openf1_driver_portraits_remain_remote_references() -> None:
    policy = policy_for_provider("openf1_headshot")
    assert policy.source_role == "discovery"
    assert policy.storage_policy == "remote_reference"
    assert policy.rights_status == "unknown"


def test_2026_group_photo_seed_is_official_formula1_reference() -> None:
    assert len(GROUP_PHOTOS) >= 1
    seed = GROUP_PHOTOS[0]

    assert seed.source_asset_id == "2026-f1-class-preseason-group"
    assert seed.page_url.startswith("https://www.formula1.com/")
    assert "class-of-2026" in seed.page_url
    assert seed.image_url.startswith("https://d2n9h2wits23hf.cloudfront.net/")
    assert "2026 Formula 1 drivers" in seed.caption
