-- Canonical starting grid for race/sprint sessions.
-- Provider/session/driver identifiers and raw payload are retained for provenance.
CREATE TABLE IF NOT EXISTS session_starting_grid (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES race_sessions(id) ON DELETE CASCADE,
    driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    team_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    provider text NOT NULL,
    provider_session_key bigint NOT NULL,
    provider_driver_number integer NOT NULL,
    position integer NOT NULL,
    qualifying_lap_duration_seconds double precision,
    source_url text NOT NULL,
    source_timestamp timestamptz,
    fetched_at timestamptz NOT NULL,
    raw_payload jsonb NOT NULL,
    UNIQUE (provider, provider_session_key, provider_driver_number)
);
CREATE INDEX IF NOT EXISTS idx_session_starting_grid_position
    ON session_starting_grid(session_id, position);
CREATE INDEX IF NOT EXISTS idx_session_starting_grid_driver
    ON session_starting_grid(driver_entity_id);
CREATE INDEX IF NOT EXISTS idx_session_starting_grid_team
    ON session_starting_grid(team_entity_id);
