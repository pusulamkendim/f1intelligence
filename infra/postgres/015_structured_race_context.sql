-- Canonical OpenF1 race context used to explain pace and race-state changes.
-- All provider rows retain source URL/timestamps and raw payload for provenance.

ALTER TABLE session_laps ADD COLUMN IF NOT EXISTS sector_1_duration_seconds double precision;
ALTER TABLE session_laps ADD COLUMN IF NOT EXISTS sector_2_duration_seconds double precision;
ALTER TABLE session_laps ADD COLUMN IF NOT EXISTS sector_3_duration_seconds double precision;
ALTER TABLE session_laps ADD COLUMN IF NOT EXISTS i1_speed_kph integer;
ALTER TABLE session_laps ADD COLUMN IF NOT EXISTS i2_speed_kph integer;
ALTER TABLE session_laps ADD COLUMN IF NOT EXISTS st_speed_kph integer;
ALTER TABLE session_laps ADD COLUMN IF NOT EXISTS segments_sector_1 jsonb;
ALTER TABLE session_laps ADD COLUMN IF NOT EXISTS segments_sector_2 jsonb;
ALTER TABLE session_laps ADD COLUMN IF NOT EXISTS segments_sector_3 jsonb;

CREATE TABLE IF NOT EXISTS session_race_control_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), session_id uuid NOT NULL REFERENCES race_sessions(id) ON DELETE CASCADE, driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
 provider text NOT NULL, provider_session_key bigint NOT NULL, provider_driver_number integer, observed_at timestamptz NOT NULL, category text, flag text, scope text, message text NOT NULL,
 lap_number integer, sector integer, source_url text NOT NULL, source_timestamp timestamptz, fetched_at timestamptz NOT NULL, raw_payload jsonb NOT NULL,
 UNIQUE (provider, provider_session_key, observed_at, message));
CREATE INDEX IF NOT EXISTS idx_session_race_control_time ON session_race_control_events(session_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_session_race_control_driver ON session_race_control_events(session_id, driver_entity_id, observed_at);

CREATE TABLE IF NOT EXISTS session_intervals (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), session_id uuid NOT NULL REFERENCES race_sessions(id) ON DELETE CASCADE, driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
 provider text NOT NULL, provider_session_key bigint NOT NULL, provider_driver_number integer NOT NULL, observed_at timestamptz NOT NULL, interval_seconds double precision, interval_text text,
 gap_to_leader_seconds double precision, gap_to_leader_text text, source_url text NOT NULL, source_timestamp timestamptz, fetched_at timestamptz NOT NULL, raw_payload jsonb NOT NULL,
 UNIQUE (provider, provider_session_key, provider_driver_number, observed_at));
CREATE INDEX IF NOT EXISTS idx_session_intervals_driver_time ON session_intervals(session_id, driver_entity_id, observed_at);

CREATE TABLE IF NOT EXISTS session_pit_stops (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), session_id uuid NOT NULL REFERENCES race_sessions(id) ON DELETE CASCADE, driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
 provider text NOT NULL, provider_session_key bigint NOT NULL, provider_driver_number integer NOT NULL, lap_number integer NOT NULL, observed_at timestamptz NOT NULL,
 lane_duration_seconds double precision, stop_duration_seconds double precision, source_url text NOT NULL, source_timestamp timestamptz, fetched_at timestamptz NOT NULL, raw_payload jsonb NOT NULL,
 UNIQUE (provider, provider_session_key, provider_driver_number, lap_number, observed_at));
CREATE INDEX IF NOT EXISTS idx_session_pit_stops_driver_lap ON session_pit_stops(session_id, driver_entity_id, lap_number);

CREATE TABLE IF NOT EXISTS session_weather (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), session_id uuid NOT NULL REFERENCES race_sessions(id) ON DELETE CASCADE, provider text NOT NULL, provider_session_key bigint NOT NULL,
 observed_at timestamptz NOT NULL, air_temperature_c double precision, track_temperature_c double precision, humidity_percent double precision, pressure_mbar double precision,
 rainfall boolean, wind_direction_degrees integer, wind_speed_mps double precision, source_url text NOT NULL, source_timestamp timestamptz, fetched_at timestamptz NOT NULL, raw_payload jsonb NOT NULL,
 UNIQUE (provider, provider_session_key, observed_at));
CREATE INDEX IF NOT EXISTS idx_session_weather_time ON session_weather(session_id, observed_at);
