-- Rights-aware media registry and story media candidates.
-- Binary storage is optional: discovery/reference metadata can exist without R2.

CREATE TABLE IF NOT EXISTS media_assets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_type text NOT NULL DEFAULT 'photo',
    content_role text NOT NULL DEFAULT 'article_hero',
    source_role text NOT NULL DEFAULT 'discovery',
    source_provider text NOT NULL,
    source_asset_id text,
    origin_provider text,
    origin_asset_id text,
    discovered_via text NOT NULL,
    discovery_page_url text,
    original_url text NOT NULL,
    caption text,
    alt_text text,
    photographer text,
    agency text,
    copyright_holder text,
    credit_line text,
    license_type text,
    license_url text,
    usage_scope text NOT NULL DEFAULT 'unknown',
    rights_status text NOT NULL DEFAULT 'unknown',
    storage_policy text NOT NULL DEFAULT 'metadata_only',
    attribution_required boolean NOT NULL DEFAULT false,
    modification_allowed boolean,
    rights_evidence_url text,
    rights_verified_at timestamptz,
    season integer,
    race_id uuid REFERENCES races(id) ON DELETE SET NULL,
    session_id uuid REFERENCES race_sessions(id) ON DELETE SET NULL,
    lap_number integer,
    captured_at timestamptz,
    published_at timestamptz,
    mime_type text,
    width integer,
    height integer,
    aspect_ratio numeric(8,5),
    content_hash text,
    r2_bucket text,
    r2_key text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (
        content_role IN (
            'article_hero',
            'race_hero',
            'podium',
            'winner',
            'race_start',
            'overtake',
            'incident',
            'pit_stop',
            'strategy',
            'driver_action',
            'team_action',
            'technical_detail',
            'celebration',
            'reaction',
            'driver_portrait',
            'car_profile',
            'launch',
            'garage',
            'circuit',
            'generic'
        )
    ),
    CHECK (
        source_role IN (
            'origin',
            'discovery',
            'license_resolver'
        )
    ),
    CHECK (
        usage_scope IN (
            'editorial',
            'news',
            'commercial',
            'personal',
            'unknown'
        )
    ),
    CHECK (
        rights_status IN (
            'unknown',
            'restricted',
            'editorial_only',
            'license_required',
            'verified'
        )
    ),
    CHECK (
        storage_policy IN (
            'metadata_only',
            'remote_reference',
            'cache_allowed',
            'self_host_allowed'
        )
    )
);

-- Upgrade the legacy media_assets table created by 001_init.sql.
-- CREATE TABLE IF NOT EXISTS does not add missing columns to an existing table,
-- so every field introduced by the rights-aware registry must be replay-safe.
ALTER TABLE media_assets
    ADD COLUMN IF NOT EXISTS content_role text NOT NULL DEFAULT 'article_hero',
    ADD COLUMN IF NOT EXISTS source_role text NOT NULL DEFAULT 'discovery',
    ADD COLUMN IF NOT EXISTS source_asset_id text,
    ADD COLUMN IF NOT EXISTS origin_provider text,
    ADD COLUMN IF NOT EXISTS origin_asset_id text,
    ADD COLUMN IF NOT EXISTS discovered_via text,
    ADD COLUMN IF NOT EXISTS discovery_page_url text,
    ADD COLUMN IF NOT EXISTS original_url text,
    ADD COLUMN IF NOT EXISTS caption text,
    ADD COLUMN IF NOT EXISTS photographer text,
    ADD COLUMN IF NOT EXISTS agency text,
    ADD COLUMN IF NOT EXISTS copyright_holder text,
    ADD COLUMN IF NOT EXISTS credit_line text,
    ADD COLUMN IF NOT EXISTS license_type text,
    ADD COLUMN IF NOT EXISTS license_url text,
    ADD COLUMN IF NOT EXISTS usage_scope text NOT NULL DEFAULT 'unknown',
    ADD COLUMN IF NOT EXISTS storage_policy text NOT NULL DEFAULT 'metadata_only',
    ADD COLUMN IF NOT EXISTS modification_allowed boolean,
    ADD COLUMN IF NOT EXISTS rights_evidence_url text,
    ADD COLUMN IF NOT EXISTS rights_verified_at timestamptz,
    ADD COLUMN IF NOT EXISTS season integer,
    ADD COLUMN IF NOT EXISTS race_id uuid REFERENCES races(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS session_id uuid REFERENCES race_sessions(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS lap_number integer,
    ADD COLUMN IF NOT EXISTS captured_at timestamptz,
    ADD COLUMN IF NOT EXISTS published_at timestamptz,
    ADD COLUMN IF NOT EXISTS aspect_ratio numeric(8,5),
    ADD COLUMN IF NOT EXISTS content_hash text,
    ADD COLUMN IF NOT EXISTS r2_bucket text,
    ADD COLUMN IF NOT EXISTS r2_key text,
    ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

UPDATE media_assets
SET
    discovered_via = COALESCE(discovered_via, source_provider),
    discovery_page_url = COALESCE(discovery_page_url, source_page_url),
    original_url = COALESCE(
        original_url,
        original_file_url,
        source_page_url
    ),
    caption = COALESCE(caption, title, description),
    photographer = COALESCE(photographer, creator_name),
    copyright_holder = COALESCE(copyright_holder, rights_holder),
    credit_line = COALESCE(credit_line, attribution_text),
    license_type = COALESCE(license_type, licence_name),
    license_url = COALESCE(license_url, licence_url),
    rights_evidence_url = COALESCE(
        rights_evidence_url,
        permission_reference,
        attribution_url
    ),
    rights_verified_at = COALESCE(rights_verified_at, rights_checked_at),
    content_hash = COALESCE(content_hash, checksum)
WHERE
    discovered_via IS NULL
    OR discovery_page_url IS NULL
    OR original_url IS NULL
    OR caption IS NULL
    OR photographer IS NULL
    OR copyright_holder IS NULL
    OR credit_line IS NULL
    OR license_type IS NULL
    OR license_url IS NULL
    OR rights_evidence_url IS NULL
    OR rights_verified_at IS NULL
    OR content_hash IS NULL;

ALTER TABLE media_assets
    ALTER COLUMN discovered_via SET NOT NULL,
    ALTER COLUMN original_url SET NOT NULL,
    ALTER COLUMN source_page_url DROP NOT NULL,
    ALTER COLUMN rights_checked_at DROP NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS media_assets_provider_url_uq
    ON media_assets(source_provider, original_url);

CREATE UNIQUE INDEX IF NOT EXISTS media_assets_provider_asset_id_uq
    ON media_assets(source_provider, source_asset_id)
    WHERE source_asset_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS media_assets_origin_asset_id_idx
    ON media_assets(origin_provider, origin_asset_id)
    WHERE origin_provider IS NOT NULL
      AND origin_asset_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS media_assets_race_idx
    ON media_assets(race_id, captured_at);

CREATE INDEX IF NOT EXISTS media_assets_role_idx
    ON media_assets(content_role, season);

CREATE INDEX IF NOT EXISTS media_assets_rights_idx
    ON media_assets(rights_status, storage_policy);

CREATE TABLE IF NOT EXISTS media_asset_entities (
    media_asset_id uuid NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    entity_id uuid NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation_type text NOT NULL DEFAULT 'depicted',
    confidence smallint NOT NULL DEFAULT 80 CHECK (confidence BETWEEN 0 AND 100),
    match_method text NOT NULL DEFAULT 'caption_entity_match_v1',
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (media_asset_id, entity_id)
);

CREATE INDEX IF NOT EXISTS media_asset_entities_entity_idx
    ON media_asset_entities(entity_id, media_asset_id);

CREATE TABLE IF NOT EXISTS source_item_media_assets (
    source_item_id uuid NOT NULL REFERENCES source_items(id) ON DELETE CASCADE,
    media_asset_id uuid NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    relation_type text NOT NULL DEFAULT 'article_hero',
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_item_id, media_asset_id)
);

CREATE TABLE IF NOT EXISTS story_media_candidates (
    story_id uuid NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    media_asset_id uuid NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    story_role text NOT NULL DEFAULT 'hero',
    match_reason text NOT NULL,
    confidence smallint NOT NULL CHECK (confidence BETWEEN 0 AND 100),
    selected boolean NOT NULL DEFAULT false,
    manual_override boolean NOT NULL DEFAULT false,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (story_id, media_asset_id, story_role),
    CHECK (story_role IN ('hero', 'supporting', 'thumbnail')),
    CHECK (
        match_reason IN (
            'source_article',
            'exact_event',
            'entity_match',
            'race_match',
            'team_match',
            'fallback',
            'manual'
        )
    )
);

CREATE INDEX IF NOT EXISTS story_media_candidates_story_rank_idx
    ON story_media_candidates(story_id, story_role, selected DESC, confidence DESC);

CREATE INDEX IF NOT EXISTS story_media_candidates_asset_idx
    ON story_media_candidates(media_asset_id);
