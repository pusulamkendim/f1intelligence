-- Rights-aware media registry and story media candidates.
-- Binary storage is optional: discovery/reference metadata can exist without R2.

CREATE TABLE IF NOT EXISTS media_assets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_type text NOT NULL DEFAULT 'photo',
    content_role text NOT NULL DEFAULT 'article_hero',
    source_role text NOT NULL DEFAULT 'discovery',
    source_provider text NOT NULL,
    source_asset_id text,
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

CREATE UNIQUE INDEX IF NOT EXISTS media_assets_provider_url_uq
    ON media_assets(source_provider, original_url);

CREATE UNIQUE INDEX IF NOT EXISTS media_assets_provider_asset_id_uq
    ON media_assets(source_provider, source_asset_id)
    WHERE source_asset_id IS NOT NULL;

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
