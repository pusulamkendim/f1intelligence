CREATE TABLE IF NOT EXISTS ingestion_item_entities (
    ingestion_item_id uuid NOT NULL REFERENCES ingestion_items(id) ON DELETE CASCADE,
    entity_id uuid NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    matched_alias text NOT NULL,
    confidence smallint NOT NULL CHECK (confidence BETWEEN 1 AND 100),
    match_method text NOT NULL DEFAULT 'alias',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (ingestion_item_id, entity_id)
);

CREATE INDEX IF NOT EXISTS ingestion_item_entities_entity_idx
    ON ingestion_item_entities(entity_id);
