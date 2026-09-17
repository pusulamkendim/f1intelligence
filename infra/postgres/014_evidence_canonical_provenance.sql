-- Canonical evidence links and provider provenance for analysis/story foundations.
-- Evidence stores concise claims/references, not full copyrighted source bodies.

ALTER TABLE evidence
    ADD COLUMN IF NOT EXISTS race_id uuid REFERENCES races(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS session_id uuid REFERENCES race_sessions(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS team_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS provider text,
    ADD COLUMN IF NOT EXISTS provider_evidence_id text,
    ADD COLUMN IF NOT EXISTS evidence_type text NOT NULL DEFAULT 'source_claim',
    ADD COLUMN IF NOT EXISTS source_timestamp timestamptz,
    ADD COLUMN IF NOT EXISTS fetched_at timestamptz NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

CREATE UNIQUE INDEX IF NOT EXISTS evidence_provider_identity_idx
    ON evidence(provider, provider_evidence_id)
    WHERE provider IS NOT NULL AND provider_evidence_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS evidence_race_idx ON evidence(race_id);
CREATE INDEX IF NOT EXISTS evidence_session_idx ON evidence(session_id);
CREATE INDEX IF NOT EXISTS evidence_driver_entity_idx ON evidence(driver_entity_id);
CREATE INDEX IF NOT EXISTS evidence_team_entity_idx ON evidence(team_entity_id);
CREATE INDEX IF NOT EXISTS evidence_type_idx ON evidence(evidence_type);
CREATE INDEX IF NOT EXISTS evidence_source_timestamp_idx ON evidence(source_timestamp DESC);

COMMENT ON COLUMN evidence.raw_excerpt_or_reference IS
    'Short excerpt or source reference only; do not use as storage for full copyrighted article bodies.';
COMMENT ON COLUMN evidence.provider_evidence_id IS
    'Stable provider-side identity used with provider for idempotent ingestion when available.';
