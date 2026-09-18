import pytest

from app.visualizations import service


def test_classic_f1_presentation_exposes_timing_tokens_and_columns():
    presentation = service._presentation("sector-timing")
    assert presentation["driver_label_mode"] == "acronym"
    assert presentation["semantic_tokens"]["timing-purple"]
    assert presentation["semantic_tokens"]["tyre-soft"]
    columns = {column["key"]: column for column in presentation["columns"]}
    assert columns["s1_seconds"]["status_key"] == "s1_status"
    assert columns["s2_seconds"]["status_key"] == "s2_status"
    assert columns["s3_seconds"]["status_key"] == "s3_status"


def test_position_axis_can_render_p1_at_the_top():
    axis = service._axis(
        "position",
        "Position",
        unit="position",
        direction="reversed",
        formatter="position",
        min_value=1,
        max_value=22,
    )
    assert axis["direction"] == "reversed"
    assert axis["min"] == 1
    assert axis["max"] == 22


@pytest.mark.parametrize(
    ("flag", "category", "label", "expected"),
    [
        ("RED", "Flag", "Red flag", "flag-red"),
        ("YELLOW", "Flag", "Yellow flag", "flag-yellow"),
        ("GREEN", "Flag", "Green flag", "flag-green"),
        ("BLUE", "Flag", "Blue flag", "flag-blue"),
        ("CHEQUERED", "Flag", "Chequered flag", "flag-chequered"),
        (None, "SafetyCar", "VIRTUAL SAFETY CAR DEPLOYED", "virtual-safety-car"),
        (None, "SafetyCar", "SAFETY CAR DEPLOYED", "safety-car"),
        (None, "Drs", "DRS ENABLED", "drs"),
    ],
)
def test_race_control_events_map_to_f1_semantic_tokens(
    flag,
    category,
    label,
    expected,
):
    assert service._annotation_token(
        {"flag": flag, "category": category, "label": label}
    ) == expected


@pytest.mark.asyncio
async def test_sector_chart_uses_sector_dispatch_not_stint_fallback(monkeypatch):
    async def fake_session(db, race_key, session_code):
        return {
            "id": "session-id",
            "session_name": "Race",
            "source_url": "https://example.test/session",
            "fetched_at": None,
            "official_name": "Example Grand Prix",
        }

    async def fake_driver_rows(db, session_id, table, columns):
        assert table == "session_laps"
        assert "sector_1_duration_seconds" in columns
        return [
            {
                "driver_key": "max-verstappen",
                "driver_label": "Max Verstappen",
                "driver_number": 1,
                "driver_acronym": "VER",
                "team_key": "red-bull-racing",
                "team_label": "Red Bull Racing",
                "team_color": "3671C6",
                "lap_number": 1,
                "sector_1_duration_seconds": 30.0,
                "sector_2_duration_seconds": 31.0,
                "sector_3_duration_seconds": 32.0,
            }
        ]

    async def fake_annotations(db, session_id):
        return []

    async def fake_provenance(db, session_id, tables):
        return []

    monkeypatch.setattr(service, "_session", fake_session)
    monkeypatch.setattr(service, "_driver_rows", fake_driver_rows)
    monkeypatch.setattr(service, "_annotations", fake_annotations)
    monkeypatch.setattr(service, "_dataset_provenance", fake_provenance)

    response = await service.race_visualization(
        None,
        "example-grand-prix",
        "race",
        "sectors",
    )

    assert response.chart_type == "timing_table"
    assert response.presentation.preset == "sector-timing"
    assert response.series[0].points[0]["s1_status"] == "purple"
