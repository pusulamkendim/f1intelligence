-- Preserve source-level provenance while allowing multiple publishers to support
-- the same story. Cross-source similarity is recorded as a candidate first; it is
-- intentionally non-destructive and does not auto-merge stories.

CREATE TABLE IF NOT EXISTS story_source_items (
    story_id uuid NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    source_item_id uuid NOT NULL REFERENCES source_items(id) ON DELETE CASCADE,
    relation_type text NOT NULL DEFAULT 'corroborating'
        CHECK (relation_type IN ('primary', 'corroborating', 'background', 'mention')),
    cluster_method text NOT NULL DEFAULT 'manual',
    cluster_confidence smallint NOT NULL DEFAULT 100
        CHECK (cluster_confidence BETWEEN 1 AND 100),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (story_id, source_item_id)
);

CREATE INDEX IF NOT EXISTS story_source_items_source_idx
    ON story_source_items(source_item_id);
CREATE INDEX IF NOT EXISTS story_source_items_story_relation_idx
    ON story_source_items(story_id, relation_type);

CREATE TABLE IF NOT EXISTS source_item_cluster_candidates (
    left_source_item_id uuid NOT NULL REFERENCES source_items(id) ON DELETE CASCADE,
    right_source_item_id uuid NOT NULL REFERENCES source_items(id) ON DELETE CASCADE,
    score smallint NOT NULL CHECK (score BETWEEN 1 AND 100),
    method text NOT NULL,
    status text NOT NULL DEFAULT 'candidate'
        CHECK (status IN ('candidate', 'accepted', 'rejected')),
    reasons jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (left_source_item_id, right_source_item_id),
    CHECK (left_source_item_id <> right_source_item_id)
);

CREATE INDEX IF NOT EXISTS source_item_cluster_candidates_status_score_idx
    ON source_item_cluster_candidates(status, score DESC);
CREATE INDEX IF NOT EXISTS source_item_cluster_candidates_right_idx
    ON source_item_cluster_candidates(right_source_item_id);
