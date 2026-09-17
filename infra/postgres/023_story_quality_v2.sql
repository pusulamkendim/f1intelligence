-- Story quality v2: keep publication time distinct from ingestion/observation time.
-- Replay-safe and intentionally limited to automatically materialized story metadata.

ALTER TABLE stories
    ADD COLUMN IF NOT EXISTS first_observed_at timestamptz,
    ADD COLUMN IF NOT EXISTS last_observed_at timestamptz;

CREATE INDEX IF NOT EXISTS stories_last_observed_idx
    ON stories(last_observed_at DESC NULLS LAST);

-- PR 57 upgrades auto story entity aggregation from v1 to v2. Superseded
-- auto-stories must never leak either generation into context facets.
CREATE OR REPLACE FUNCTION cleanup_superseded_story_entities()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.merged_into_story_id IS NOT NULL
       AND OLD.merged_into_story_id IS DISTINCT FROM NEW.merged_into_story_id THEN
        DELETE FROM story_entities
        WHERE story_id = NEW.id
          AND aggregation_method IN ('source_aggregate_v1', 'source_aggregate_v2');
    END IF;
    RETURN NEW;
END;
$$;
