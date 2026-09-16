CREATE TABLE IF NOT EXISTS ingestion_sources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    key text NOT NULL UNIQUE,
    provider text NOT NULL,
    name text NOT NULL,
    feed_url text NOT NULL,
    source_type text NOT NULL DEFAULT 'official_feed',
    enabled boolean NOT NULL DEFAULT true,
    last_checked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS story_ingestion_rules (
    story_id uuid PRIMARY KEY REFERENCES stories(id) ON DELETE CASCADE,
    min_score smallint NOT NULL DEFAULT 3 CHECK (min_score BETWEEN 1 AND 100),
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS story_match_terms (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id uuid NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    term text NOT NULL,
    weight smallint NOT NULL DEFAULT 1 CHECK (weight BETWEEN 1 AND 20),
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (story_id, term)
);

CREATE TABLE IF NOT EXISTS story_identifiers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id uuid NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    identifier text NOT NULL UNIQUE,
    identifier_type text NOT NULL DEFAULT 'case_reference',
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ingestion_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid NOT NULL REFERENCES ingestion_sources(id) ON DELETE CASCADE,
    external_id text NOT NULL,
    source_url text,
    title text NOT NULL,
    published_at timestamptz,
    matched_story_id uuid REFERENCES stories(id) ON DELETE SET NULL,
    evidence_id uuid REFERENCES evidence(id) ON DELETE SET NULL,
    status text NOT NULL,
    match_score smallint,
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    ingested_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_id, external_id)
);

CREATE INDEX IF NOT EXISTS story_match_terms_story_idx ON story_match_terms(story_id);
CREATE INDEX IF NOT EXISTS story_identifiers_story_idx ON story_identifiers(story_id);
CREATE INDEX IF NOT EXISTS ingestion_items_status_idx ON ingestion_items(status);
CREATE INDEX IF NOT EXISTS ingestion_items_story_idx ON ingestion_items(matched_story_id);
CREATE INDEX IF NOT EXISTS ingestion_items_published_idx ON ingestion_items(published_at DESC);
