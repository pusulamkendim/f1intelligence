-- Unified timeline placement layer.
-- Canonical structured race/session/lap/stint data remains in its existing tables;
-- this table only records where content-like objects belong on the shared F1 timeline.

CREATE TABLE IF NOT EXISTS timeline_placements (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    item_type text NOT NULL CHECK (
        item_type IN ('story', 'evidence', 'document', 'publication', 'manual_event')
    ),
    item_id uuid NOT NULL,
    temporal_relation text NOT NULL CHECK (
        temporal_relation IN (
            'occurred_at', 'reported_at', 'scheduled_for', 'effective_from', 'applies_to'
        )
    ),
    precision text NOT NULL CHECK (
        precision IN ('season', 'race', 'session', 'stint', 'lap', 'timestamp')
    ),
    season integer NOT NULL,
    race_id uuid REFERENCES races(id) ON DELETE CASCADE,
    session_id uuid REFERENCES race_sessions(id) ON DELETE CASCADE,
    driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    stint_number integer CHECK (stint_number IS NULL OR stint_number > 0),
    lap_number integer CHECK (lap_number IS NULL OR lap_number > 0),
    timeline_at timestamptz,
    reported_at timestamptz,
    confidence smallint NOT NULL DEFAULT 90 CHECK (confidence BETWEEN 1 AND 100),
    match_method text NOT NULL,
    is_primary boolean NOT NULL DEFAULT true,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (session_id IS NULL OR race_id IS NOT NULL),
    CHECK (
        (stint_number IS NULL AND lap_number IS NULL)
        OR session_id IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS timeline_placements_season_time_idx
    ON timeline_placements(season, timeline_at);
CREATE INDEX IF NOT EXISTS timeline_placements_race_time_idx
    ON timeline_placements(race_id, timeline_at)
    WHERE race_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS timeline_placements_session_time_idx
    ON timeline_placements(session_id, timeline_at)
    WHERE session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS timeline_placements_driver_time_idx
    ON timeline_placements(driver_entity_id, timeline_at)
    WHERE driver_entity_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS timeline_placements_item_idx
    ON timeline_placements(item_type, item_id);

CREATE UNIQUE INDEX IF NOT EXISTS timeline_placements_coordinate_uniq
    ON timeline_placements (
        item_type,
        item_id,
        temporal_relation,
        season,
        race_id,
        session_id,
        driver_entity_id,
        stint_number,
        lap_number,
        is_primary
    ) NULLS NOT DISTINCT;

CREATE OR REPLACE FUNCTION cleanup_story_timeline_placements()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        DELETE FROM timeline_placements
        WHERE item_type = 'story' AND item_id = OLD.id;
        RETURN OLD;
    END IF;

    IF NEW.merged_into_story_id IS NOT NULL
       AND OLD.merged_into_story_id IS DISTINCT FROM NEW.merged_into_story_id THEN
        DELETE FROM timeline_placements
        WHERE item_type = 'story' AND item_id = NEW.id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS stories_timeline_placement_cleanup ON stories;
CREATE TRIGGER stories_timeline_placement_cleanup
AFTER DELETE OR UPDATE OF merged_into_story_id ON stories
FOR EACH ROW
EXECUTE FUNCTION cleanup_story_timeline_placements();
