from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

PLACEMENT_METHOD = "story_coordinate_v1"

_SEASON_RE = re.compile(r"\b(20\d{2})\b")
_HISTORICAL_EVENT_PATTERNS = (
    re.compile(r"\bon this day in\s+(20\d{2})\b", re.IGNORECASE),
    re.compile(
        r"\b(20\d{2})\b.{0,24}\b(?:grand prix|gp)\b",
        re.IGNORECASE,
    ),
)
_NON_F1_EVENT_TERMS = (
    "formula 2",
    "formula 3",
    "f2",
    "f3",
    "f1 academy",
    "le mans",
    "hypercar",
    "wec",
    "sxsw",
)
_LAP_RE = re.compile(r"\b(?:lap|lap number)\s*#?\s*(\d{1,3})\b", re.IGNORECASE)
_STINT_RE = re.compile(r"\bstint\s*#?\s*(\d{1,2})\b", re.IGNORECASE)
_ORDINAL_STINTS = {
    "first stint": 1,
    "second stint": 2,
    "third stint": 3,
    "fourth stint": 4,
}

_SESSION_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("sprint_qualifying", ("sprint qualifying", "sprint shootout")),
    ("practice_1", ("practice 1", "fp1", "free practice 1")),
    ("practice_2", ("practice 2", "fp2", "free practice 2")),
    ("practice_3", ("practice 3", "fp3", "free practice 3")),
    ("qualifying", ("qualifying", "quali")),
    (
        "sprint",
        (
            "sprint race",
            "sprint report",
            "sprint recap",
            "sprint result",
            "sprint results",
        ),
    ),
    (
        "race",
        (
            "race report",
            "race recap",
            "race result",
            "race results",
            "race review",
        ),
    ),
)

_FUTURE_TERMS = (
    "ahead of",
    "for the upcoming",
    "will bring",
    "will introduce",
    "will debut",
    "set to debut",
    "set to arrive",
    "to introduce",
    "to bring",
    "next race",
    "next season",
    "what to expect",
    "preview",
)

_RACE_LAP_TERMS = (
    "vsc",
    "virtual safety car",
    "safety car",
    "pit stop",
    "pitstop",
    "overtake",
    "race",
)


@dataclass(frozen=True)
class PlacementInference:
    season: int
    temporal_relation: str
    precision: str
    session_code: str | None
    lap_number: int | None
    stint_number: int | None
    confidence: int
    reason: str


def _normalized(value: str | None) -> str:
    return " ".join((value or "").casefold().replace("’", "'").split())


def explicit_season(value: str) -> int | None:
    match = _SEASON_RE.search(value)
    return int(match.group(1)) if match else None


def explicit_f1_season(value: str) -> int | None:
    normalized = _normalized(value)
    years = [int(match.group(1)) for match in _SEASON_RE.finditer(normalized)]
    for year in years:
        token = str(year)
        year_index = normalized.find(token)
        local = normalized[
            max(0, year_index - 32) : year_index + len(token) + 32
        ]
        if any(term in local for term in _NON_F1_EVENT_TERMS):
            continue

        strong_patterns = (
            rf"\b{token}\s+(?:formula 1|f1)\b",
            rf"\b(?:formula 1|f1)\s+{token}\b",
            rf"\b{token}\s+(?:formula 1|f1)\s+"
            rf"(?:season|car|calendar|opener|regulations?|rules?|budget|project)\b",
            rf"\b{token}\s+season\b",
            rf"\b(?:season|regulations?|rules?)\s+(?:for\s+)?{token}\b",
            rf"\b{token}\s+(?:grand prix|gp|opener)\b",
            rf"\b(?:grand prix|gp|opener)\s+{token}\b",
        )
        if any(re.search(pattern, normalized) for pattern in strong_patterns):
            return year
        if (
            ("f1" in normalized or "formula 1" in normalized)
            and any(
                phrase in local
                for phrase in (
                    f"{token} development",
                    f"{token} car",
                    f"{token} calendar",
                    f"{token} budget",
                )
            )
        ):
            return year
    return None


def explicit_historical_event_year(value: str) -> int | None:
    for pattern in _HISTORICAL_EVENT_PATTERNS:
        match = pattern.search(value)
        if match:
            return int(match.group(1))
    return None


def infer_session_code(value: str) -> str | None:
    normalized = _normalized(value)
    if normalized == "sprint":
        return "sprint"
    for code, phrases in _SESSION_PATTERNS:
        if any(phrase in normalized for phrase in phrases):
            return code
    return None


def infer_lap_number(value: str) -> int | None:
    match = _LAP_RE.search(value)
    if not match:
        return None
    lap = int(match.group(1))
    return lap if lap > 0 else None


def infer_stint_number(value: str) -> int | None:
    match = _STINT_RE.search(value)
    if match:
        stint = int(match.group(1))
        return stint if stint > 0 else None
    normalized = _normalized(value)
    return next((number for phrase, number in _ORDINAL_STINTS.items() if phrase in normalized), None)


def infer_story_coordinate(
    *,
    text_value: str,
    taxonomy: str | None,
    reported_at: datetime | None,
    race_season: int | None,
    race_anchor_at: datetime | None,
) -> PlacementInference:
    stated_season = explicit_f1_season(text_value)
    default_season = (
        race_season
        or stated_season
        or (reported_at.year if reported_at else datetime.now().year)
    )
    session_code = infer_session_code(text_value)
    lap_number = infer_lap_number(text_value)
    stint_number = infer_stint_number(text_value)
    normalized = _normalized(text_value)

    if (lap_number or stint_number) and session_code is None and any(
        term in normalized for term in _RACE_LAP_TERMS
    ):
        session_code = "race"

    future_season = bool(reported_at and stated_season and stated_season > reported_at.year)
    has_future_language = any(term in normalized for term in _FUTURE_TERMS)
    anchor_is_future = bool(
        reported_at and race_anchor_at and race_anchor_at > reported_at
    )

    if future_season and taxonomy == "regulation":
        temporal_relation = "effective_from"
    elif future_season or (anchor_is_future and has_future_language):
        temporal_relation = "scheduled_for"
    elif lap_number or stint_number or session_code:
        temporal_relation = "occurred_at"
    elif race_season is not None:
        temporal_relation = "applies_to"
    else:
        temporal_relation = "reported_at"

    season = stated_season if future_season else default_season

    if future_season and taxonomy == "regulation":
        precision = "season"
        confidence = 96
        reason = "explicit_future_effective_season"
    elif lap_number:
        precision = "lap"
        confidence = 98
        reason = "explicit_lap_reference"
    elif stint_number:
        precision = "stint"
        confidence = 96
        reason = "explicit_stint_reference"
    elif session_code:
        precision = "session"
        confidence = 96
        reason = "session_title_cue"
    elif race_season is not None:
        precision = "race"
        confidence = 94
        reason = "canonical_race_entity"
    elif stated_season:
        precision = "season"
        confidence = 90
        reason = "explicit_season_reference"
    else:
        precision = "timestamp"
        confidence = 80
        reason = "report_time_fallback"

    return PlacementInference(
        season=season,
        temporal_relation=temporal_relation,
        precision=precision,
        session_code=session_code,
        lap_number=lap_number,
        stint_number=stint_number,
        confidence=confidence,
        reason=reason,
    )


async def _story_row(session: AsyncSession, story_id: UUID):
    result = await session.execute(
        text(
            """
            SELECT
                id,
                title,
                summary,
                taxonomy,
                first_published_at,
                first_observed_at,
                created_at
            FROM stories
            WHERE id = :story_id
              AND merged_into_story_id IS NULL
            """
        ),
        {"story_id": story_id},
    )
    return result.mappings().first()


async def _story_races(session: AsyncSession, story_id: UUID):
    result = await session.execute(
        text(
            """
            SELECT
                r.id,
                r.season,
                r.slug,
                r.official_name,
                r.round,
                COALESCE(
                    r.start_at,
                    r.weekend_start_date::timestamptz
                ) AS anchor_at,
                se.relation_type,
                se.confidence,
                se.matched_alias
            FROM story_entities se
            JOIN entities e ON e.id = se.entity_id
            JOIN races r ON r.entity_id = e.id
            WHERE se.story_id = :story_id
              AND se.relation_type <> 'mentioned'
            ORDER BY
                CASE se.relation_type
                    WHEN 'subject' THEN 1
                    WHEN 'directly_involved' THEN 2
                    WHEN 'affected' THEN 3
                    WHEN 'context' THEN 4
                    ELSE 5
                END,
                se.confidence DESC,
                r.season DESC,
                r.round NULLS LAST
            """
        ),
        {"story_id": story_id},
    )
    return list(result.mappings().all())


def _strong_race_title_match(
    race: dict,
    text_value: str,
) -> bool:
    alias = _normalized(str(race.get("matched_alias") or ""))
    title = _normalized(text_value)
    if not alias or alias not in title:
        return False
    return "grand prix" in alias or bool(
        re.search(r"\bgp\b", alias)
    )


def _select_story_race(
    races: list[dict],
    *,
    text_value: str,
    reported_at: datetime | None,
) -> dict | None:
    if not races:
        return None

    historical_year = explicit_historical_event_year(text_value)
    if historical_year is not None:
        historical_matches = [
            race for race in races if race["season"] == historical_year
        ]
        if not historical_matches:
            return None
        races = historical_matches

    normalized = _normalized(text_value)
    if any(term in normalized for term in _NON_F1_EVENT_TERMS):
        strong_matches = [
            race
            for race in races
            if _strong_race_title_match(race, text_value)
        ]
        if not strong_matches:
            return None
        races = strong_matches

    has_future_language = any(
        term in normalized for term in _FUTURE_TERMS
    )
    if reported_at is not None and has_future_language:
        future_races = [
            race
            for race in races
            if race["anchor_at"] is not None
            and race["anchor_at"] >= reported_at
        ]
        if future_races:
            return min(
                future_races,
                key=lambda race: race["anchor_at"],
            )

    title_matches = []
    for race in races:
        alias = _normalized(str(race.get("matched_alias") or ""))
        if alias and alias in normalized:
            title_matches.append(race)
    if len(title_matches) == 1:
        return title_matches[0]
    if title_matches:
        races = title_matches

    return sorted(
        races,
        key=lambda race: (
            -int(race["confidence"]),
            race["season"],
            race["round"] or 999,
        ),
    )[0]


async def _session_for_code(
    session: AsyncSession,
    race_id: UUID,
    session_code: str | None,
):
    if session_code is None:
        return None
    result = await session.execute(
        text(
            """
            SELECT id, session_code, session_name, starts_at, ends_at
            FROM race_sessions
            WHERE race_id = :race_id
              AND session_code = :session_code
              AND is_cancelled = false
            LIMIT 1
            """
        ),
        {"race_id": race_id, "session_code": session_code},
    )
    return result.mappings().first()


async def _story_driver_in_session(
    session: AsyncSession,
    story_id: UUID,
    session_id: UUID,
):
    result = await session.execute(
        text(
            """
            SELECT e.id, e.slug, e.display_name, se.relation_type, se.confidence
            FROM story_entities se
            JOIN entities e ON e.id = se.entity_id
            JOIN session_entries entry
              ON entry.session_id = :session_id
             AND entry.driver_entity_id = e.id
            WHERE se.story_id = :story_id
              AND e.entity_type = 'person'
            ORDER BY
                CASE se.relation_type
                    WHEN 'subject' THEN 1
                    WHEN 'directly_involved' THEN 2
                    ELSE 3
                END,
                se.confidence DESC
            LIMIT 1
            """
        ),
        {"story_id": story_id, "session_id": session_id},
    )
    return result.mappings().first()


async def _deep_anchor(
    session: AsyncSession,
    *,
    session_id: UUID,
    driver_entity_id: UUID | None,
    lap_number: int | None,
    stint_number: int | None,
    fallback: datetime | None,
) -> tuple[datetime | None, int | None]:
    resolved_lap = lap_number
    if stint_number is not None and driver_entity_id is not None:
        result = await session.execute(
            text(
                """
                SELECT lap_start
                FROM session_stints
                WHERE session_id = :session_id
                  AND driver_entity_id = :driver_entity_id
                  AND stint_number = :stint_number
                ORDER BY fetched_at DESC
                LIMIT 1
                """
            ),
            {
                "session_id": session_id,
                "driver_entity_id": driver_entity_id,
                "stint_number": stint_number,
            },
        )
        resolved_lap = result.scalar_one_or_none() or resolved_lap

    if resolved_lap is None:
        return fallback, lap_number

    result = await session.execute(
        text(
            """
            SELECT MIN(started_at)
            FROM session_laps
            WHERE session_id = :session_id
              AND lap_number = :lap_number
              AND (
                    :driver_entity_id IS NULL
                    OR driver_entity_id = :driver_entity_id
                  )
            """
        ),
        {
            "session_id": session_id,
            "lap_number": resolved_lap,
            "driver_entity_id": driver_entity_id,
        },
    )
    return result.scalar_one_or_none() or fallback, lap_number


async def refresh_story_timeline_placement(
    session: AsyncSession,
    story_id: UUID,
) -> None:
    story = await _story_row(session, story_id)
    if story is None:
        return

    await session.execute(
        text(
            """
            DELETE FROM timeline_placements
            WHERE item_type = 'story'
              AND item_id = :story_id
              AND match_method = :match_method
            """
        ),
        {"story_id": story_id, "match_method": PLACEMENT_METHOD},
    )

    reported_at = (
        story["first_published_at"]
        or story["first_observed_at"]
        or story["created_at"]
    )
    text_value = " ".join(
        part for part in (story["title"], story["summary"]) if part
    )
    race_candidates = await _story_races(session, story_id)
    race = _select_story_race(
        [dict(row) for row in race_candidates],
        text_value=text_value,
        reported_at=reported_at,
    )
    inference = infer_story_coordinate(
        text_value=text_value,
        taxonomy=story["taxonomy"],
        reported_at=reported_at,
        race_season=race["season"] if race else None,
        race_anchor_at=race["anchor_at"] if race else None,
    )

    race_id = race["id"] if race else None
    if (
        race is not None
        and inference.precision == "season"
        and inference.season != race["season"]
    ):
        race_id = None

    session_row = (
        await _session_for_code(session, race_id, inference.session_code)
        if race_id is not None
        else None
    )
    session_id = session_row["id"] if session_row else None
    driver = (
        await _story_driver_in_session(session, story_id, session_id)
        if session_id is not None and (inference.lap_number or inference.stint_number)
        else None
    )
    driver_entity_id = driver["id"] if driver else None

    precision = inference.precision
    temporal_relation = inference.temporal_relation
    confidence = inference.confidence
    reason = inference.reason
    if precision in {"lap", "stint", "session"} and session_row is None:
        if race_id is not None:
            precision = "race"
        else:
            precision = "timestamp"
            temporal_relation = "reported_at"
            confidence = 80
            reason = "unresolved_session_fallback"
    if precision == "stint" and driver_entity_id is None:
        precision = "session" if session_row else ("race" if race_id else "timestamp")

    anchor_at = (
        session_row["starts_at"]
        if session_row
        else (
            race["anchor_at"]
            if race is not None and race_id is not None
            else None
        )
    )
    if session_id is not None and precision in {"lap", "stint"}:
        anchor_at, _ = await _deep_anchor(
            session,
            session_id=session_id,
            driver_entity_id=driver_entity_id,
            lap_number=inference.lap_number,
            stint_number=inference.stint_number,
            fallback=anchor_at,
        )

    timeline_at = anchor_at
    if temporal_relation == "reported_at" and timeline_at is None:
        timeline_at = reported_at

    await session.execute(
        text(
            """
            INSERT INTO timeline_placements (
                item_type,
                item_id,
                temporal_relation,
                precision,
                season,
                race_id,
                session_id,
                driver_entity_id,
                stint_number,
                lap_number,
                timeline_at,
                reported_at,
                confidence,
                match_method,
                is_primary,
                metadata
            ) VALUES (
                'story',
                :story_id,
                :temporal_relation,
                :precision,
                :season,
                :race_id,
                :session_id,
                :driver_entity_id,
                :stint_number,
                :lap_number,
                :timeline_at,
                :reported_at,
                :confidence,
                :match_method,
                true,
                jsonb_strip_nulls(CAST(:metadata AS jsonb))
            )
            """
        ),
        {
            "story_id": story_id,
            "temporal_relation": temporal_relation,
            "precision": precision,
            "season": inference.season,
            "race_id": race_id,
            "session_id": session_id,
            "driver_entity_id": driver_entity_id,
            "stint_number": inference.stint_number if precision == "stint" else None,
            "lap_number": inference.lap_number if precision == "lap" else None,
            "timeline_at": timeline_at,
            "reported_at": reported_at,
            "confidence": confidence,
            "match_method": PLACEMENT_METHOD,
            "metadata": json.dumps(
                {
                    "reason": reason,
                    "session_code": (
                        session_row["session_code"]
                        if session_row
                        else None
                    ),
                    "race_key": (
                        race["slug"]
                        if race is not None and race_id is not None
                        else None
                    ),
                    "driver_key": driver["slug"] if driver else None,
                }
            ),
        },
    )
