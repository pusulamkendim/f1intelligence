-- Materialized story layer for source items. This migration is replay-safe.
-- Source items remain immutable provenance records; stories are the canonical
-- user-facing representation of one news/event cluster.

ALTER TABLE stories
    ADD COLUMN IF NOT EXISTS taxonomy text,
    ADD COLUMN IF NOT EXISTS materialization_method text,
    ADD COLUMN IF NOT EXISTS canonical_source_item_id uuid REFERENCES source_items(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS first_published_at timestamptz,
    ADD COLUMN IF NOT EXISTS last_published_at timestamptz,
    ADD COLUMN IF NOT EXISTS source_count integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS merged_into_story_id uuid REFERENCES stories(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS materialization_metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS stories_canonical_source_item_idx
    ON stories(canonical_source_item_id)
    WHERE canonical_source_item_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS stories_first_published_idx
    ON stories(first_published_at DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS stories_merged_into_idx
    ON stories(merged_into_story_id)
    WHERE merged_into_story_id IS NOT NULL;

ALTER TABLE story_entities
    ADD COLUMN IF NOT EXISTS aggregation_method text NOT NULL DEFAULT 'manual';

CREATE TABLE IF NOT EXISTS source_item_story_decisions (
    source_item_id uuid PRIMARY KEY REFERENCES source_items(id) ON DELETE CASCADE,
    story_worthy boolean NOT NULL,
    taxonomy text NOT NULL,
    reason text NOT NULL,
    decision_method text NOT NULL DEFAULT 'story_worthy_v1',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS source_item_story_decisions_worthy_idx
    ON source_item_story_decisions(story_worthy, taxonomy);

-- A superseded auto-story remains as a redirect/audit row, but its automatically
-- aggregated entity links must not leak into entity context facets as duplicate stories.
CREATE OR REPLACE FUNCTION cleanup_superseded_story_entities()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.merged_into_story_id IS NOT NULL
       AND OLD.merged_into_story_id IS DISTINCT FROM NEW.merged_into_story_id THEN
        DELETE FROM story_entities
        WHERE story_id = NEW.id
          AND aggregation_method = 'source_aggregate_v1';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS stories_superseded_auto_entities_cleanup ON stories;
CREATE TRIGGER stories_superseded_auto_entities_cleanup
AFTER UPDATE OF merged_into_story_id ON stories
FOR EACH ROW
EXECUTE FUNCTION cleanup_superseded_story_entities();
