from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.resolver import ResolvedTarget, resolve_target
from app.schemas.context import ContextFacetPage, ContextTargetType


class ContextFacetNotSupportedError(LookupError):
    pass


@dataclass(frozen=True)
class FacetSpec:
    select_sql: str
    order_by: str


def _spec(select_sql: str, order_by: str) -> FacetSpec:
    return FacetSpec(select_sql=select_sql.strip(), order_by=order_by)


def _session_driver_spec(table: str, alias: str, order_by: str) -> FacetSpec:
    return _spec(
        f"""
        SELECT
            {alias}.*,
            d.slug AS driver_key,
            d.display_name AS driver_name,
            r.slug AS race_key,
            rs.session_code,
            rs.session_name
        FROM {table} {alias}
        JOIN race_sessions rs ON rs.id = {alias}.session_id
        JOIN races r ON r.id = rs.race_id
        LEFT JOIN entities d ON d.id = {alias}.driver_entity_id
        WHERE {alias}.session_id = :session_id
        """,
        order_by,
    )


def _race_session_spec(table: str, alias: str, order_by: str) -> FacetSpec:
    return _spec(
        f"""
        SELECT
            {alias}.*,
            r.slug AS race_key,
            rs.session_code,
            rs.session_name
        FROM {table} {alias}
        JOIN race_sessions rs ON rs.id = {alias}.session_id
        JOIN races r ON r.id = rs.race_id
        WHERE rs.race_id = :race_id
        """,
        order_by,
    )


def _driver_session_spec(table: str, alias: str, order_by: str) -> FacetSpec:
    return _spec(
        f"""
        SELECT
            {alias}.*,
            r.slug AS race_key,
            r.season,
            r.round,
            rs.session_code,
            rs.session_name
        FROM {table} {alias}
        JOIN race_sessions rs ON rs.id = {alias}.session_id
        JOIN races r ON r.id = rs.race_id
        WHERE {alias}.driver_entity_id = :entity_id
        """,
        order_by,
    )


SESSION_FACETS: dict[str, FacetSpec] = {
    "entries": _spec(
        """
        SELECT se.*, d.slug AS driver_key, d.display_name AS driver_name,
               t.slug AS team_key, t.display_name AS team_name_canonical
        FROM session_entries se
        LEFT JOIN entities d ON d.id = se.driver_entity_id
        LEFT JOIN entities t ON t.id = se.team_entity_id
        WHERE se.session_id = :session_id
        """,
        "driver_number, driver_name",
    ),
    "results": _spec(
        """
        SELECT sr.*, d.slug AS driver_key, d.display_name AS driver_name,
               t.slug AS team_key, t.display_name AS team_name
        FROM session_results sr
        LEFT JOIN entities d ON d.id = sr.driver_entity_id
        LEFT JOIN entities t ON t.id = sr.team_entity_id
        WHERE sr.session_id = :session_id
        """,
        "position NULLS LAST, driver_number",
    ),
    "laps": _session_driver_spec("session_laps", "sl", "lap_number, driver_name"),
    "stints": _session_driver_spec("session_stints", "ss", "driver_name, stint_number"),
    "positions": _session_driver_spec("session_positions", "sp", "observed_at, driver_name"),
    "intervals": _session_driver_spec("session_intervals", "si", "observed_at, driver_name"),
    "pit_stops": _session_driver_spec("session_pit_stops", "ps", "lap_number, driver_name"),
    "starting_grid": _spec(
        """
        SELECT sg.*, d.slug AS driver_key, d.display_name AS driver_name,
               t.slug AS team_key, t.display_name AS team_name
        FROM session_starting_grid sg
        LEFT JOIN entities d ON d.id = sg.driver_entity_id
        LEFT JOIN entities t ON t.id = sg.team_entity_id
        WHERE sg.session_id = :session_id
        """,
        "position, driver_name",
    ),
    "overtakes": _spec(
        """
        SELECT so.*,
               od.slug AS overtaking_driver_key,
               od.display_name AS overtaking_driver_name,
               dd.slug AS overtaken_driver_key,
               dd.display_name AS overtaken_driver_name
        FROM session_overtakes so
        LEFT JOIN entities od ON od.id = so.overtaking_driver_entity_id
        LEFT JOIN entities dd ON dd.id = so.overtaken_driver_entity_id
        WHERE so.session_id = :session_id
        """,
        "observed_at NULLS LAST, id",
    ),
    "race_control": _spec(
        """
        SELECT rc.*, d.slug AS driver_key, d.display_name AS driver_name
        FROM session_race_control_events rc
        LEFT JOIN entities d ON d.id = rc.driver_entity_id
        WHERE rc.session_id = :session_id
        """,
        "observed_at, id",
    ),
    "weather": _spec(
        "SELECT sw.* FROM session_weather sw WHERE sw.session_id = :session_id",
        "observed_at, id",
    ),
    "evidence": _spec(
        "SELECT e.* FROM evidence e WHERE e.session_id = :session_id",
        "COALESCE(source_timestamp, published_at, captured_at) DESC NULLS LAST, id",
    ),
}


RACE_FACETS: dict[str, FacetSpec] = {
    "sessions": _spec(
        "SELECT rs.* FROM race_sessions rs WHERE rs.race_id = :race_id",
        "starts_at, sequence NULLS LAST",
    ),
    "race_results": _spec(
        """
        SELECT rr.*, d.slug AS driver_key, d.display_name AS driver_name,
               t.slug AS team_key, t.display_name AS team_name
        FROM race_results rr
        LEFT JOIN entities d ON d.id = rr.driver_entity_id
        LEFT JOIN entities t ON t.id = rr.team_entity_id
        WHERE rr.race_id = :race_id
        """,
        "finish_position NULLS LAST, driver_name",
    ),
    "qualifying_results": _spec(
        """
        SELECT qr.*, d.slug AS driver_key, d.display_name AS driver_name,
               t.slug AS team_key, t.display_name AS team_name
        FROM qualifying_results qr
        LEFT JOIN entities d ON d.id = qr.driver_entity_id
        LEFT JOIN entities t ON t.id = qr.team_entity_id
        WHERE qr.race_id = :race_id
        """,
        "position, driver_name",
    ),
    "session_results": _race_session_spec("session_results", "sr", "session_code, position NULLS LAST"),
    "laps": _race_session_spec("session_laps", "sl", "session_code, lap_number"),
    "stints": _race_session_spec("session_stints", "ss", "session_code, stint_number"),
    "positions": _race_session_spec("session_positions", "sp", "session_code, observed_at"),
    "intervals": _race_session_spec("session_intervals", "si", "session_code, observed_at"),
    "pit_stops": _race_session_spec("session_pit_stops", "ps", "session_code, lap_number"),
    "starting_grid": _race_session_spec("session_starting_grid", "sg", "session_code, position"),
    "overtakes": _race_session_spec("session_overtakes", "so", "session_code, observed_at NULLS LAST"),
    "race_control": _race_session_spec(
        "session_race_control_events", "rc", "session_code, observed_at"
    ),
    "weather": _race_session_spec("session_weather", "sw", "session_code, observed_at"),
    "documents": _spec(
        "SELECT rd.* FROM race_documents rd WHERE rd.race_id = :race_id",
        "published_at DESC NULLS LAST, document_number DESC NULLS LAST, id",
    ),
    "stories": _spec(
        """
        SELECT s.*, se.relation_type, se.confidence AS relation_confidence
        FROM story_entities se
        JOIN stories s ON s.id = se.story_id
        WHERE se.entity_id = :entity_id
        """,
        "updated_at DESC, title",
    ),
    "evidence": _spec(
        "SELECT e.* FROM evidence e WHERE e.race_id = :race_id",
        "COALESCE(source_timestamp, published_at, captured_at) DESC NULLS LAST, id",
    ),
}


DRIVER_FACETS: dict[str, FacetSpec] = {
    "race_results": _spec(
        """
        SELECT rr.*, r.season, r.round, r.slug AS race_key, r.official_name AS race_name,
               t.slug AS team_key, t.display_name AS team_name
        FROM race_results rr
        JOIN races r ON r.id = rr.race_id
        LEFT JOIN entities t ON t.id = rr.team_entity_id
        WHERE rr.driver_entity_id = :entity_id
        """,
        "season DESC, round DESC NULLS LAST",
    ),
    "qualifying_results": _spec(
        """
        SELECT qr.*, r.season, r.round, r.slug AS race_key, r.official_name AS race_name,
               t.slug AS team_key, t.display_name AS team_name
        FROM qualifying_results qr
        JOIN races r ON r.id = qr.race_id
        LEFT JOIN entities t ON t.id = qr.team_entity_id
        WHERE qr.driver_entity_id = :entity_id
        """,
        "season DESC, round DESC NULLS LAST",
    ),
    "session_results": _driver_session_spec(
        "session_results", "sr", "season DESC, round DESC NULLS LAST, session_code"
    ),
    "laps": _driver_session_spec("session_laps", "sl", "season DESC, round DESC NULLS LAST, lap_number"),
    "stints": _driver_session_spec(
        "session_stints", "ss", "season DESC, round DESC NULLS LAST, stint_number"
    ),
    "positions": _driver_session_spec(
        "session_positions", "sp", "season DESC, round DESC NULLS LAST, observed_at DESC"
    ),
    "intervals": _driver_session_spec(
        "session_intervals", "si", "season DESC, round DESC NULLS LAST, observed_at DESC"
    ),
    "pit_stops": _driver_session_spec(
        "session_pit_stops", "ps", "season DESC, round DESC NULLS LAST, lap_number"
    ),
    "starting_grid": _driver_session_spec(
        "session_starting_grid", "sg", "season DESC, round DESC NULLS LAST, position"
    ),
    "overtakes": _spec(
        """
        SELECT so.*, r.season, r.round, r.slug AS race_key, rs.session_code,
               od.slug AS overtaking_driver_key, dd.slug AS overtaken_driver_key
        FROM session_overtakes so
        JOIN race_sessions rs ON rs.id = so.session_id
        JOIN races r ON r.id = rs.race_id
        LEFT JOIN entities od ON od.id = so.overtaking_driver_entity_id
        LEFT JOIN entities dd ON dd.id = so.overtaken_driver_entity_id
        WHERE so.overtaking_driver_entity_id = :entity_id
           OR so.overtaken_driver_entity_id = :entity_id
        """,
        "season DESC, round DESC NULLS LAST, observed_at DESC NULLS LAST",
    ),
    "standings": _spec(
        """
        SELECT dsr.*, dss.season, dss.after_round, dss.fetched_at, dss.source_url
        FROM driver_standing_rows dsr
        JOIN driver_standings_snapshots dss ON dss.id = dsr.snapshot_id
        WHERE dsr.driver_entity_id = :entity_id
        """,
        "season DESC, after_round DESC, fetched_at DESC",
    ),
    "stories": _spec(
        """
        SELECT s.*, se.relation_type, se.confidence AS relation_confidence
        FROM story_entities se JOIN stories s ON s.id = se.story_id
        WHERE se.entity_id = :entity_id
        """,
        "updated_at DESC, title",
    ),
    "documents": _spec(
        """
        SELECT rd.*, rde.matched_alias, rde.match_method,
               rde.confidence AS relation_confidence
        FROM race_document_entities rde
        JOIN race_documents rd ON rd.id = rde.race_document_id
        WHERE rde.entity_id = :entity_id
        """,
        "published_at DESC NULLS LAST, id",
    ),
    "evidence": _spec(
        "SELECT e.* FROM evidence e WHERE e.driver_entity_id = :entity_id",
        "COALESCE(source_timestamp, published_at, captured_at) DESC NULLS LAST, id",
    ),
}


TEAM_FACETS: dict[str, FacetSpec] = {
    "race_results": _spec(
        """
        SELECT rr.*, r.season, r.round, r.slug AS race_key, r.official_name AS race_name,
               d.slug AS driver_key, d.display_name AS driver_name
        FROM race_results rr
        JOIN races r ON r.id = rr.race_id
        LEFT JOIN entities d ON d.id = rr.driver_entity_id
        WHERE rr.team_entity_id = :entity_id
        """,
        "season DESC, round DESC NULLS LAST, finish_position NULLS LAST",
    ),
    "qualifying_results": _spec(
        """
        SELECT qr.*, r.season, r.round, r.slug AS race_key, r.official_name AS race_name,
               d.slug AS driver_key, d.display_name AS driver_name
        FROM qualifying_results qr
        JOIN races r ON r.id = qr.race_id
        LEFT JOIN entities d ON d.id = qr.driver_entity_id
        WHERE qr.team_entity_id = :entity_id
        """,
        "season DESC, round DESC NULLS LAST, position",
    ),
    "session_results": _spec(
        """
        SELECT sr.*, r.season, r.round, r.slug AS race_key, rs.session_code,
               d.slug AS driver_key, d.display_name AS driver_name
        FROM session_results sr
        JOIN race_sessions rs ON rs.id = sr.session_id
        JOIN races r ON r.id = rs.race_id
        LEFT JOIN entities d ON d.id = sr.driver_entity_id
        WHERE sr.team_entity_id = :entity_id
        """,
        "season DESC, round DESC NULLS LAST, session_code, position NULLS LAST",
    ),
    "session_entries": _spec(
        """
        SELECT se.*, r.season, r.round, r.slug AS race_key, rs.session_code,
               d.slug AS driver_key, d.display_name AS driver_name
        FROM session_entries se
        JOIN race_sessions rs ON rs.id = se.session_id
        JOIN races r ON r.id = rs.race_id
        LEFT JOIN entities d ON d.id = se.driver_entity_id
        WHERE se.team_entity_id = :entity_id
        """,
        "season DESC, round DESC NULLS LAST, session_code, driver_number",
    ),
    "starting_grid": _spec(
        """
        SELECT sg.*, r.season, r.round, r.slug AS race_key, rs.session_code,
               d.slug AS driver_key, d.display_name AS driver_name
        FROM session_starting_grid sg
        JOIN race_sessions rs ON rs.id = sg.session_id
        JOIN races r ON r.id = rs.race_id
        LEFT JOIN entities d ON d.id = sg.driver_entity_id
        WHERE sg.team_entity_id = :entity_id
        """,
        "season DESC, round DESC NULLS LAST, position",
    ),
    "standings": _spec(
        """
        SELECT csr.*, css.season, css.after_round, css.fetched_at, css.source_url
        FROM constructor_standing_rows csr
        JOIN constructor_standings_snapshots css ON css.id = csr.snapshot_id
        WHERE csr.team_entity_id = :entity_id
        """,
        "season DESC, after_round DESC, fetched_at DESC",
    ),
    "stories": DRIVER_FACETS["stories"],
    "documents": DRIVER_FACETS["documents"],
    "evidence": _spec(
        "SELECT e.* FROM evidence e WHERE e.team_entity_id = :entity_id",
        "COALESCE(source_timestamp, published_at, captured_at) DESC NULLS LAST, id",
    ),
}


SEASON_FACETS: dict[str, FacetSpec] = {
    "races": _spec(
        "SELECT r.* FROM races r WHERE r.season = :season",
        "round NULLS LAST, start_at NULLS LAST",
    ),
    "race_results": _spec(
        """
        SELECT rr.*, r.round, r.slug AS race_key, r.official_name AS race_name,
               d.slug AS driver_key, d.display_name AS driver_name,
               t.slug AS team_key, t.display_name AS team_name
        FROM race_results rr
        JOIN races r ON r.id = rr.race_id
        LEFT JOIN entities d ON d.id = rr.driver_entity_id
        LEFT JOIN entities t ON t.id = rr.team_entity_id
        WHERE r.season = :season
        """,
        "round DESC NULLS LAST, finish_position NULLS LAST",
    ),
    "qualifying_results": _spec(
        """
        SELECT qr.*, r.round, r.slug AS race_key, r.official_name AS race_name,
               d.slug AS driver_key, d.display_name AS driver_name,
               t.slug AS team_key, t.display_name AS team_name
        FROM qualifying_results qr
        JOIN races r ON r.id = qr.race_id
        LEFT JOIN entities d ON d.id = qr.driver_entity_id
        LEFT JOIN entities t ON t.id = qr.team_entity_id
        WHERE r.season = :season
        """,
        "round DESC NULLS LAST, position",
    ),
    "sessions": _spec(
        """
        SELECT rs.*, r.round, r.slug AS race_key, r.official_name AS race_name
        FROM race_sessions rs JOIN races r ON r.id = rs.race_id
        WHERE r.season = :season
        """,
        "round DESC NULLS LAST, starts_at",
    ),
    "session_results": _spec(
        """
        SELECT sr.*, r.round, r.slug AS race_key, rs.session_code,
               d.slug AS driver_key, d.display_name AS driver_name,
               t.slug AS team_key, t.display_name AS team_name
        FROM session_results sr
        JOIN race_sessions rs ON rs.id = sr.session_id
        JOIN races r ON r.id = rs.race_id
        LEFT JOIN entities d ON d.id = sr.driver_entity_id
        LEFT JOIN entities t ON t.id = sr.team_entity_id
        WHERE r.season = :season
        """,
        "round DESC NULLS LAST, session_code, position NULLS LAST",
    ),
    "documents": _spec(
        """
        SELECT rd.*, r.round, r.slug AS race_key, r.official_name AS race_name
        FROM race_documents rd JOIN races r ON r.id = rd.race_id
        WHERE r.season = :season
        """,
        "published_at DESC NULLS LAST, id",
    ),
    "stories": _spec(
        """
        SELECT DISTINCT s.*
        FROM story_entities se
        JOIN races r ON r.entity_id = se.entity_id
        JOIN stories s ON s.id = se.story_id
        WHERE r.season = :season
        """,
        "updated_at DESC, title",
    ),
}


STORY_FACETS: dict[str, FacetSpec] = {
    "evidence": _spec(
        "SELECT e.* FROM evidence e WHERE e.story_id = :story_id",
        "COALESCE(source_timestamp, published_at, captured_at) DESC NULLS LAST, id",
    ),
    "entities": _spec(
        """
        SELECT se.*, e.entity_type, e.slug AS entity_key, e.display_name,
               e.metadata AS entity_metadata
        FROM story_entities se JOIN entities e ON e.id = se.entity_id
        WHERE se.story_id = :story_id
        """,
        "confidence DESC, display_name",
    ),
    "publications": _spec(
        """
        SELECT p.*
        FROM publication_stories ps JOIN publications p ON p.id = ps.publication_id
        WHERE ps.story_id = :story_id
        """,
        "published_at DESC NULLS LAST, updated_at DESC, headline",
    ),
}


FACET_SPECS: dict[str, dict[str, FacetSpec]] = {
    "driver": DRIVER_FACETS,
    "team": TEAM_FACETS,
    "race": RACE_FACETS,
    "session": SESSION_FACETS,
    "season": SEASON_FACETS,
    "story": STORY_FACETS,
}


def _params(target: ResolvedTarget) -> dict[str, Any]:
    return {
        "entity_id": target.entity_id,
        "race_id": target.race_id,
        "session_id": target.session_id,
        "story_id": target.story_id,
        "season": target.season,
    }


async def read_context_facet(
    db: AsyncSession,
    target_type: ContextTargetType,
    key: str,
    facet: str,
    *,
    limit: int,
    offset: int,
) -> ContextFacetPage:
    target = await resolve_target(db, target_type, key)
    spec = FACET_SPECS[target_type].get(facet)
    if spec is None:
        raise ContextFacetNotSupportedError(
            f"Facet {facet!r} is not supported for {target_type} context"
        )

    params = _params(target)
    count_result = await db.execute(
        text(f"SELECT COUNT(*)::int AS total FROM ({spec.select_sql}) facet_items"),
        params,
    )
    count_row = count_result.mappings().first()
    total = int(count_row["total"]) if count_row is not None else 0

    page_params = {**params, "limit": limit, "offset": offset}
    page_result = await db.execute(
        text(
            f"""
            WITH facet_items AS (
                {spec.select_sql}
            )
            SELECT to_jsonb(facet_items) - 'raw_payload' - 'raw_metadata' AS item
            FROM facet_items
            ORDER BY {spec.order_by}
            LIMIT :limit OFFSET :offset
            """
        ),
        page_params,
    )
    items = [dict(row["item"]) for row in page_result.mappings().all()]
    next_offset = offset + len(items) if offset + len(items) < total else None
    return ContextFacetPage(
        target=target.target,
        facet=facet,
        total=total,
        limit=limit,
        offset=offset,
        next_offset=next_offset,
        items=items,
    )
