-- OpenF1 approximate car locations for driver tracker / track-map views.
-- Historical samples are intentionally downsampled by the ingestion layer.
-- Coordinates are provider-native Cartesian x/y/z values; the origin is arbitrary.

CREATE TABLE IF NOT EXISTS session_locations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES race_sessions(id) ON DELETE CASCADE,
    driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    provider text NOT NULL,
    provider_session_key bigint NOT NULL,
    provider_driver_number integer NOT NULL,
    observed_at timestamptz NOT NULL,
    x integer NOT NULL,
    y integer NOT NULL,
    z integer NOT NULL,
    source_url text NOT NULL,
    source_timestamp timestamptz,
    fetched_at timestamptz NOT NULL,
    raw_payload jsonb NOT NULL,
    UNIQUE (
        provider,
        provider_session_key,
        provider_driver_number,
        observed_at
    )
);

CREATE INDEX IF NOT EXISTS idx_session_locations_session_time
    ON session_locations(session_id, observed_at);

CREATE INDEX IF NOT EXISTS idx_session_locations_driver_time
    ON session_locations(session_id, driver_entity_id, observed_at);

CREATE INDEX IF NOT EXISTS idx_session_locations_provider_driver_time
    ON session_locations(
        provider_session_key,
        provider_driver_number,
        observed_at
    );
