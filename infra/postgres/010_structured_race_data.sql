-- Canonical structured F1 data imported from providers such as Jolpica/OpenF1.
-- Provider identifiers and retrieval metadata are retained so imports are auditable
-- and can be replayed without coupling public reads to an upstream API.

CREATE TABLE data_sync_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL,
    dataset text NOT NULL,
    season integer,
    round integer,
    status text NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'succeeded', 'failed')),
    source_url text,
    source_updated_at timestamptz,
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    records_seen integer NOT NULL DEFAULT 0,
    records_written integer NOT NULL DEFAULT 0,
    error_message text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX data_sync_runs_lookup_idx
    ON data_sync_runs(provider, dataset, season, round, started_at DESC);

ALTER TABLE races
    ADD COLUMN IF NOT EXISTS provider text,
    ADD COLUMN IF NOT EXISTS provider_race_id text,
    ADD COLUMN IF NOT EXISTS circuit_provider_id text,
    ADD COLUMN IF NOT EXISTS locality text,
    ADD COLUMN IF NOT EXISTS latitude numeric(9,6),
    ADD COLUMN IF NOT EXISTS longitude numeric(9,6),
    ADD COLUMN IF NOT EXISTS source_url text,
    ADD COLUMN IF NOT EXISTS source_updated_at timestamptz,
    ADD COLUMN IF NOT EXISTS fetched_at timestamptz;

CREATE UNIQUE INDEX IF NOT EXISTS races_provider_id_unique_idx
    ON races(provider, provider_race_id)
    WHERE provider IS NOT NULL AND provider_race_id IS NOT NULL;

CREATE TABLE race_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    race_id uuid NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    provider text NOT NULL,
    provider_result_id text NOT NULL,
    driver_provider_id text NOT NULL,
    constructor_provider_id text,
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

CREATE INDEX race_results_race_position_idx ON race_results(race_id, finish_position);
CREATE INDEX race_results_driver_idx ON race_results(provider, driver_provider_id);

CREATE TABLE qualifying_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    race_id uuid NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    provider text NOT NULL,
    provider_result_id text NOT NULL,
    driver_provider_id text NOT NULL,
    constructor_provider_id text,
    car_number integer,
    position integer NOT NULL,
    q1 text,
    q2 text,
    q3 text,
    source_url text,
    source_updated_at timestamptz,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (provider, provider_result_id)
);

CREATE INDEX qualifying_results_race_position_idx ON qualifying_results(race_id, position);

CREATE TABLE driver_standings_snapshots (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL,
    season integer NOT NULL,
    after_round integer NOT NULL,
    source_url text,
    source_updated_at timestamptz,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    content_hash text NOT NULL,
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (provider, season, after_round, content_hash)
);

CREATE INDEX driver_standings_snapshots_latest_idx
    ON driver_standings_snapshots(provider, season, after_round DESC, fetched_at DESC);

CREATE TABLE driver_standing_rows (
    snapshot_id uuid NOT NULL REFERENCES driver_standings_snapshots(id) ON DELETE CASCADE,
    driver_provider_id text NOT NULL,
    position integer NOT NULL,
    position_text text,
    points numeric(10,3) NOT NULL DEFAULT 0,
    wins integer NOT NULL DEFAULT 0,
    constructor_provider_ids text[] NOT NULL DEFAULT '{}',
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (snapshot_id, driver_provider_id)
);

CREATE INDEX driver_standing_rows_position_idx ON driver_standing_rows(snapshot_id, position);

CREATE TABLE constructor_standings_snapshots (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL,
    season integer NOT NULL,
    after_round integer NOT NULL,
    source_url text,
    source_updated_at timestamptz,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    content_hash text NOT NULL,
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (provider, season, after_round, content_hash)
);

CREATE INDEX constructor_standings_snapshots_latest_idx
    ON constructor_standings_snapshots(provider, season, after_round DESC, fetched_at DESC);

CREATE TABLE constructor_standing_rows (
    snapshot_id uuid NOT NULL REFERENCES constructor_standings_snapshots(id) ON DELETE CASCADE,
    constructor_provider_id text NOT NULL,
    position integer NOT NULL,
    position_text text,
    points numeric(10,3) NOT NULL DEFAULT 0,
    wins integer NOT NULL DEFAULT 0,
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (snapshot_id, constructor_provider_id)
);

CREATE INDEX constructor_standing_rows_position_idx
    ON constructor_standing_rows(snapshot_id, position);
