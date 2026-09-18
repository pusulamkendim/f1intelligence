-- Generic audit trail for automatic provider-to-canonical entity reconciliation.
-- This is schema infrastructure, not a season-specific registry seed.

CREATE TABLE IF NOT EXISTS entity_reconciliation_audit (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL,
    provider_entity_type text NOT NULL CHECK (
        provider_entity_type IN ('driver', 'constructor')
    ),
    provider_id text NOT NULL,
    season integer NOT NULL,
    resolved_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    resolution_method text NOT NULL CHECK (
        resolution_method IN (
            'exact_provider_id',
            'provider_validity_extension',
            'exact_identity',
            'auto_created',
            'ambiguous'
        )
    ),
    confidence smallint NOT NULL CHECK (confidence BETWEEN 0 AND 100),
    review_required boolean NOT NULL DEFAULT false,
    source_url text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (
        provider,
        provider_entity_type,
        provider_id,
        season
    )
);

CREATE INDEX IF NOT EXISTS entity_reconciliation_audit_season_idx
    ON entity_reconciliation_audit(
        season,
        provider_entity_type,
        review_required
    );

CREATE INDEX IF NOT EXISTS entity_reconciliation_audit_entity_idx
    ON entity_reconciliation_audit(resolved_entity_id)
    WHERE resolved_entity_id IS NOT NULL;
