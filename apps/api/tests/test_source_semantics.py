from app.ingestion.source_semantics import classification_title


def test_haas_publisher_branding_is_removed_only_for_classification() -> None:
    title = "Haas F1 Team | Formula 1 announces 2027 calendar with 10 Sprints"
    assert classification_title("team_haas", title) == (
        "Formula 1 announces 2027 calendar with 10 Sprints"
    )
    assert classification_title("autosport_f1", title) == title


def test_racing_bulls_trailing_branding_is_removed() -> None:
    assert classification_title(
        "team_racing_bulls",
        "2026 Creator Platform Recap | VCARB | Visa Cash App RB",
    ) == "2026 Creator Platform Recap"


def test_unknown_source_keeps_original_title() -> None:
    title = "Mercedes risked looking silly at Monza"
    assert classification_title("unknown", title) == title
