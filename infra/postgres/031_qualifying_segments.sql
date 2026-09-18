-- Qualifying Q1/Q2/Q3 are canonical child segments of one qualifying session.
-- Timing values remain sourced from session_results to avoid duplicating provider data.

CREATE TABLE IF NOT EXISTS session_segments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES race_sessions(id) ON DELETE CASCADE,
    segment_code text NOT NULL,
    segment_name text NOT NULL,
    segment_type text NOT NULL DEFAULT 'qualifying_phase',
    sequence smallint NOT NULL CHECK (sequence > 0),
    starts_at timestamptz,
    ends_at timestamptz,
    provider text NOT NULL,
    provider_segment_id text,
    source_url text,
    source_timestamp timestamptz,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (session_id, segment_code),
    CHECK (segment_type = 'qualifying_phase'),
    CHECK (segment_code IN ('q1', 'q2', 'q3')),
    CHECK (ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at)
);

CREATE INDEX IF NOT EXISTS session_segments_session_sequence_idx
    ON session_segments(session_id, sequence);

INSERT INTO session_segments (
    session_id,
    segment_code,
    segment_name,
    segment_type,
    sequence,
    provider,
    source_url,
    source_timestamp,
    fetched_at,
    raw_metadata
)
SELECT
    rs.id,
    segment.segment_code,
    upper(segment.segment_code),
    'qualifying_phase',
    segment.sequence,
    rs.provider,
    rs.source_url,
    rs.source_updated_at,
    rs.fetched_at,
    jsonb_build_object(
        'derived_from', 'race_sessions',
        'provider_session_id', rs.provider_session_id
    )
FROM race_sessions rs
CROSS JOIN (
    VALUES
        ('q1', 1),
        ('q2', 2),
        ('q3', 3)
) AS segment(segment_code, sequence)
WHERE rs.session_code = 'qualifying'
ON CONFLICT (session_id, segment_code) DO UPDATE
SET segment_name = EXCLUDED.segment_name,
    segment_type = EXCLUDED.segment_type,
    sequence = EXCLUDED.sequence,
    provider = EXCLUDED.provider,
    source_url = EXCLUDED.source_url,
    source_timestamp = EXCLUDED.source_timestamp,
    fetched_at = EXCLUDED.fetched_at,
    raw_metadata = EXCLUDED.raw_metadata;

CREATE OR REPLACE VIEW qualifying_segment_results AS
WITH expanded AS (
    SELECT
        sg.id AS segment_id,
        sg.session_id,
        sg.segment_code,
        sg.segment_name,
        sg.sequence,
        sr.id AS session_result_id,
        sr.driver_entity_id,
        sr.team_entity_id,
        sr.driver_number,
        sr.driver_provider_id,
        sr.position AS final_qualifying_position,
        CASE sg.segment_code
            WHEN 'q1' THEN sr.q1_seconds
            WHEN 'q2' THEN sr.q2_seconds
            WHEN 'q3' THEN sr.q3_seconds
        END AS duration_seconds,
        CASE sg.segment_code
            WHEN 'q1' THEN sr.q1_gap_seconds
            WHEN 'q2' THEN sr.q2_gap_seconds
            WHEN 'q3' THEN sr.q3_gap_seconds
        END AS gap_to_leader_seconds,
        CASE sg.segment_code
            WHEN 'q1' THEN sr.q2_seconds IS NOT NULL
            WHEN 'q2' THEN sr.q3_seconds IS NOT NULL
            ELSE NULL
        END AS reached_next_segment,
        sr.provider,
        sr.source_url,
        sr.source_updated_at,
        sr.fetched_at
    FROM session_segments sg
    JOIN session_results sr ON sr.session_id = sg.session_id
    WHERE sg.segment_type = 'qualifying_phase'
),
ranked AS (
    SELECT
        expanded.*,
        CASE
            WHEN duration_seconds IS NULL THEN NULL
            ELSE rank() OVER (
                PARTITION BY segment_id
                ORDER BY duration_seconds ASC NULLS LAST
            )::integer
        END AS segment_position
    FROM expanded
)
SELECT *
FROM ranked;

ALTER TABLE timeline_placements
    ADD COLUMN IF NOT EXISTS segment_id uuid REFERENCES session_segments(id) ON DELETE CASCADE;

ALTER TABLE timeline_placements
    DROP CONSTRAINT IF EXISTS timeline_placements_precision_check;

ALTER TABLE timeline_placements
    ADD CONSTRAINT timeline_placements_precision_check
    CHECK (
        precision IN (
            'season',
            'race',
            'session',
            'segment',
            'stint',
            'lap',
            'timestamp'
        )
    );

ALTER TABLE timeline_placements
    DROP CONSTRAINT IF EXISTS timeline_placements_check;

ALTER TABLE timeline_placements
    ADD CONSTRAINT timeline_placements_segment_requires_session_check
    CHECK (segment_id IS NULL OR session_id IS NOT NULL);

CREATE INDEX IF NOT EXISTS timeline_placements_segment_time_idx
    ON timeline_placements(segment_id, timeline_at)
    WHERE segment_id IS NOT NULL;

DROP INDEX IF EXISTS timeline_placements_coordinate_uniq;

CREATE UNIQUE INDEX timeline_placements_coordinate_uniq
    ON timeline_placements (
        item_type,
        item_id,
        temporal_relation,
        season,
        race_id,
        session_id,
        segment_id,
        driver_entity_id,
        stint_number,
        lap_number,
        is_primary
    ) NULLS NOT DISTINCT;
