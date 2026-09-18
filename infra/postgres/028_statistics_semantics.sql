-- Sprint classifications and stricter deterministic statistics semantics.
-- GP results remain separate from sprint results so conventional F1 race wins,
-- podiums and starts are never inflated by sprint classifications.

CREATE TABLE IF NOT EXISTS sprint_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    race_id uuid NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    provider text NOT NULL,
    provider_result_id text NOT NULL,
    driver_provider_id text NOT NULL,
    constructor_provider_id text,
    driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    team_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    car_number integer,
    grid_position integer,
    finish_position integer,
    position_text text,
    points numeric(8,3) NOT NULL DEFAULT 0,
    laps integer,
    status text,
    finish_time text,
    fastest_lap_rank integer,
    fastest_lap_number integer,
    fastest_lap_time text,
    source_url text,
    source_updated_at timestamptz,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (provider, provider_result_id)
);

CREATE INDEX IF NOT EXISTS sprint_results_race_position_idx
    ON sprint_results(race_id, finish_position);

CREATE INDEX IF NOT EXISTS sprint_results_driver_history_idx
    ON sprint_results(driver_entity_id, race_id)
    WHERE driver_entity_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS sprint_results_provider_driver_idx
    ON sprint_results(provider, driver_provider_id);
