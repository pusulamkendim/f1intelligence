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
