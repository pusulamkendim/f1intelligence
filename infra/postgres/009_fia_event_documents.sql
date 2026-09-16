CREATE TABLE IF NOT EXISTS race_documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    race_id uuid NOT NULL REFERENCES races(id) ON DELETE CASCADE,
    provider text NOT NULL,
    external_id text NOT NULL,
    document_number integer,
    title text NOT NULL,
    document_type text NOT NULL DEFAULT 'other',
    document_url text NOT NULL,
    source_page_url text NOT NULL,
    published_at timestamptz,
    published_label text,
    recalled boolean NOT NULL DEFAULT false,
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider, external_id)
);

CREATE INDEX IF NOT EXISTS race_documents_race_published_idx
    ON race_documents(race_id, published_at DESC);
CREATE INDEX IF NOT EXISTS race_documents_type_idx
    ON race_documents(document_type);

CREATE TABLE IF NOT EXISTS race_document_entities (
    race_document_id uuid NOT NULL REFERENCES race_documents(id) ON DELETE CASCADE,
    entity_id uuid NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    matched_alias text NOT NULL,
    confidence smallint NOT NULL CHECK (confidence BETWEEN 1 AND 100),
    match_method text NOT NULL DEFAULT 'alias',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (race_document_id, entity_id)
);

CREATE INDEX IF NOT EXISTS race_document_entities_entity_idx
    ON race_document_entities(entity_id);

-- FIA's 2026 decision-document section names the Madrid round "Spanish Grand Prix".
INSERT INTO entity_aliases (
    entity_id,
    alias,
    alias_type,
    confidence,
    valid_from_season,
    valid_to_season
)
SELECT id, 'Spanish Grand Prix', 'fia_event_name', 99, 2026, 2026
FROM entities
WHERE entity_type = 'race'
  AND slug = '2026-madrid-grand-prix'
ON CONFLICT (entity_id, alias) DO UPDATE
SET alias_type = EXCLUDED.alias_type,
    confidence = EXCLUDED.confidence,
    valid_from_season = EXCLUDED.valid_from_season,
    valid_to_season = EXCLUDED.valid_to_season,
    enabled = true,
    updated_at = now();
