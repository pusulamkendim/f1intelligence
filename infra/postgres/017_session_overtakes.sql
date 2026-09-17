CREATE TABLE IF NOT EXISTS session_overtakes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES race_sessions(id) ON DELETE CASCADE,
    overtaking_driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    overtaken_driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    provider text NOT NULL,
    provider_session_key bigint NOT NULL,
    overtaking_driver_number integer NOT NULL,
    overtaken_driver_number integer NOT NULL,
    position integer NOT NULL,
    observed_at timestamptz NOT NULL,
    source_url text NOT NULL,
    source_timestamp timestamptz,
    fetched_at timestamptz NOT NULL,
    raw_payload jsonb NOT NULL,
    UNIQUE (
        provider,
        provider_session_key,
        overtaking_driver_number,
        overtaken_driver_number,
        observed_at
    )
);

CREATE INDEX IF NOT EXISTS idx_session_overtakes_session_time
    ON session_overtakes(session_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_session_overtakes_overtaking_driver
    ON session_overtakes(overtaking_driver_entity_id);
CREATE INDEX IF NOT EXISTS idx_session_overtakes_overtaken_driver
    ON session_overtakes(overtaken_driver_entity_id);
