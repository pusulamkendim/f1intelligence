-- OpenF1 historical session telemetry summaries.
-- Provider IDs are retained for idempotent upserts and provenance.

CREATE TABLE IF NOT EXISTS session_laps (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES race_sessions(id) ON DELETE CASCADE,
    driver_id uuid REFERENCES drivers(id),
    provider text NOT NULL,
    provider_session_key bigint NOT NULL,
    provider_driver_number integer NOT NULL,
    lap_number integer NOT NULL,
    lap_duration_seconds double precision,
    is_pit_out_lap boolean NOT NULL DEFAULT false,
    started_at timestamptz,
    source_url text NOT NULL,
    source_timestamp timestamptz,
    fetched_at timestamptz NOT NULL,
    raw_payload jsonb NOT NULL,
    UNIQUE (provider, provider_session_key, provider_driver_number, lap_number)
);

CREATE INDEX IF NOT EXISTS idx_session_laps_session_driver ON session_laps(session_id, driver_id, lap_number);

CREATE TABLE IF NOT EXISTS session_stints (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES race_sessions(id) ON DELETE CASCADE,
    driver_id uuid REFERENCES drivers(id),
    provider text NOT NULL,
    provider_session_key bigint NOT NULL,
    provider_driver_number integer NOT NULL,
    stint_number integer NOT NULL,
    lap_start integer,
    lap_end integer,
    compound text,
    tyre_age_at_start integer,
    source_url text NOT NULL,
    source_timestamp timestamptz,
    fetched_at timestamptz NOT NULL,
    raw_payload jsonb NOT NULL,
    UNIQUE (provider, provider_session_key, provider_driver_number, stint_number)
);

CREATE INDEX IF NOT EXISTS idx_session_stints_session_driver ON session_stints(session_id, driver_id, stint_number);

CREATE TABLE IF NOT EXISTS session_positions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES race_sessions(id) ON DELETE CASCADE,
    driver_id uuid REFERENCES drivers(id),
    provider text NOT NULL,
    provider_session_key bigint NOT NULL,
    provider_driver_number integer NOT NULL,
    observed_at timestamptz NOT NULL,
    position integer NOT NULL,
    source_url text NOT NULL,
    source_timestamp timestamptz,
    fetched_at timestamptz NOT NULL,
    raw_payload jsonb NOT NULL,
    UNIQUE (provider, provider_session_key, provider_driver_number, observed_at)
);

CREATE INDEX IF NOT EXISTS idx_session_positions_session_driver_time ON session_positions(session_id, driver_id, observed_at);
