-- Article/source-level ingestion and canonical entity links.
-- This layer is intentionally separate from story_entities: a source item records
-- what one article/transcript/post is about, while story_entities represents the
-- aggregate semantics of a clustered story.

CREATE TABLE IF NOT EXISTS source_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL,
    external_id text NOT NULL,
    source_type text NOT NULL DEFAULT 'article',
    source_class text NOT NULL DEFAULT 'editorial',
    source_url text,
    title text NOT NULL,
    standfirst text,
    summary text,
    body_excerpt text,
    author text,
    language text,
    published_at timestamptz,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    content_hash text,
    rights_policy text,
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider, external_id)
);

CREATE INDEX IF NOT EXISTS source_items_published_idx
    ON source_items(published_at DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS source_items_provider_type_idx
    ON source_items(provider, source_type);
CREATE INDEX IF NOT EXISTS source_items_source_class_idx
    ON source_items(source_class);

CREATE TABLE IF NOT EXISTS source_item_entities (
    source_item_id uuid NOT NULL REFERENCES source_items(id) ON DELETE CASCADE,
    entity_id uuid NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation_type text NOT NULL DEFAULT 'mentioned'
        CHECK (relation_type IN ('subject', 'directly_involved', 'affected', 'mentioned', 'context')),
    confidence smallint NOT NULL DEFAULT 90 CHECK (confidence BETWEEN 1 AND 100),
    match_method text NOT NULL DEFAULT 'alias',
    matched_alias text,
    detected_in text[] NOT NULL DEFAULT '{}',
    classification_method text NOT NULL DEFAULT 'deterministic_v1',
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_item_id, entity_id)
);

CREATE INDEX IF NOT EXISTS source_item_entities_entity_idx
    ON source_item_entities(entity_id);
CREATE INDEX IF NOT EXISTS source_item_entities_relation_idx
    ON source_item_entities(relation_type, confidence DESC);

-- Evidence can point back to the exact source item that produced the claim/quote.
ALTER TABLE evidence
    ADD COLUMN IF NOT EXISTS source_item_id uuid REFERENCES source_items(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS evidence_source_item_idx
    ON evidence(source_item_id)
    WHERE source_item_id IS NOT NULL;
