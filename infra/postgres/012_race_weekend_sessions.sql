-- Canonical race-weekend sessions and session-level participants/results.
-- Provider identifiers are retained separately from canonical race/driver/team links.

CREATE TABLE IF NOT EXISTS race_provider_ids (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    race_id uuid NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    provider text NOT NULL,
    provider_id text NOT NULL,
    provider_entity_type text NOT NULL DEFAULT 'meeting',
    source_url text,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (provider, provider_entity_type, provider_id)
);

CREATE INDEX IF NOT EXISTS race_provider_ids_race_idx ON race_provider_ids(race_id);

CREATE TABLE IF NOT EXISTS race_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    race_id uuid NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    provider text NOT NULL,
    provider_session_id text NOT NULL,
    provider_meeting_id text,
    session_code text NOT NULL,
    session_name text NOT NULL,
    session_type text,
    sequence integer,
    starts_at timestamptz NOT NULL,
    ends_at timestamptz,
    gmt_offset text,
    is_cancelled boolean NOT NULL DEFAULT false,
    source_url text,
    source_updated_at timestamptz,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (provider, provider_session_id),
    UNIQUE (race_id, session_code)
);

CREATE INDEX IF NOT EXISTS race_sessions_race_start_idx
    ON race_sessions(race_id, starts_at);
CREATE INDEX IF NOT EXISTS race_sessions_next_idx
    ON race_sessions(starts_at)
    WHERE is_cancelled = false;

CREATE TABLE IF NOT EXISTS session_entries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES race_sessions(id) ON DELETE CASCADE,
    provider text NOT NULL,
    driver_provider_id text NOT NULL,
    driver_number integer NOT NULL,
    driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    team_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    broadcast_name text,
    first_name text,
    last_name text,
    full_name text,
    name_acronym text,
    team_name text,
    team_colour text,
    headshot_reference_url text,
    headshot_rights_status text NOT NULL DEFAULT 'external_reference_only',
    source_url text,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (session_id, provider, driver_provider_id)
);

CREATE INDEX IF NOT EXISTS session_entries_driver_entity_idx
    ON session_entries(driver_entity_id);
CREATE INDEX IF NOT EXISTS session_entries_team_entity_idx
    ON session_entries(team_entity_id);

CREATE TABLE IF NOT EXISTS session_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES race_sessions(id) ON DELETE CASCADE,
    provider text NOT NULL,
    provider_result_id text NOT NULL,
    driver_provider_id text NOT NULL,
    driver_number integer NOT NULL,
    driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    team_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    position integer,
    dnf boolean NOT NULL DEFAULT false,
    dns boolean NOT NULL DEFAULT false,
    dsq boolean NOT NULL DEFAULT false,
    number_of_laps integer,
    duration_seconds numeric(12,3),
    q1_seconds numeric(12,3),
    q2_seconds numeric(12,3),
    q3_seconds numeric(12,3),
    gap_to_leader_seconds numeric(12,3),
    gap_to_leader_text text,
    q1_gap_seconds numeric(12,3),
    q2_gap_seconds numeric(12,3),
    q3_gap_seconds numeric(12,3),
    source_url text,
    source_updated_at timestamptz,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (provider, provider_result_id)
);

CREATE INDEX IF NOT EXISTS session_results_session_position_idx
    ON session_results(session_id, position);
CREATE INDEX IF NOT EXISTS session_results_driver_entity_idx
    ON session_results(driver_entity_id);
CREATE INDEX IF NOT EXISTS session_results_team_entity_idx
    ON session_results(team_entity_id);
