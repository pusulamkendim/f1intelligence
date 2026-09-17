-- Historical statistics are derived from canonical provider-backed result tables.
-- This migration deliberately stores no arbitrary external career counters.
-- It only adds replay-safe indexes used by deterministic aggregation APIs.

CREATE INDEX IF NOT EXISTS race_results_driver_history_idx
    ON race_results(driver_entity_id, race_id)
    WHERE driver_entity_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS qualifying_results_driver_history_idx
    ON qualifying_results(driver_entity_id, race_id)
    WHERE driver_entity_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS driver_standing_rows_driver_history_idx
    ON driver_standing_rows(driver_entity_id, snapshot_id)
    WHERE driver_entity_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS session_laps_driver_history_idx
    ON session_laps(driver_entity_id, session_id, lap_number)
    WHERE driver_entity_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS session_stints_driver_history_idx
    ON session_stints(driver_entity_id, session_id, stint_number)
    WHERE driver_entity_id IS NOT NULL;
