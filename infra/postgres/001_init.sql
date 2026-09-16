CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE teams (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text NOT NULL UNIQUE,
    name text NOT NULL,
    active_season integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE races (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    season integer NOT NULL,
    round integer,
    slug text NOT NULL,
    official_name text NOT NULL,
    circuit text,
    country text,
    start_at timestamptz,
    status text NOT NULL DEFAULT 'upcoming',
    synthesis text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (season, slug)
);

CREATE TABLE stories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text NOT NULL UNIQUE,
    title text NOT NULL,
    summary text,
    status text NOT NULL DEFAULT 'emerging',
    significance smallint NOT NULL DEFAULT 50 CHECK (significance BETWEEN 0 AND 100),
    confidence text NOT NULL DEFAULT 'tentative',
    what_changed text,
    why_it_matters text,
    what_to_watch_next text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE evidence (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id uuid REFERENCES stories(id) ON DELETE SET NULL,
    source_type text NOT NULL,
    source_name text NOT NULL,
    source_url text,
    published_at timestamptz,
    captured_at timestamptz NOT NULL DEFAULT now(),
    author_or_speaker text,
    normalized_claim text,
    raw_excerpt_or_reference text,
    reliability_class text,
    directness text,
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE publications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text NOT NULL UNIQUE,
    type text NOT NULL,
    headline text NOT NULL,
    standfirst text,
    body text,
    status text NOT NULL DEFAULT 'draft',
    published_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE publication_stories (
    publication_id uuid NOT NULL REFERENCES publications(id) ON DELETE CASCADE,
    story_id uuid NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    PRIMARY KEY (publication_id, story_id)
);

CREATE TABLE media_candidates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL,
    provider_asset_id text,
    source_page_url text NOT NULL,
    preview_url text,
    original_file_url text,
    title text,
    creator_name text,
    licence_name text,
    licence_version text,
    licence_url text,
    rights_status text NOT NULL DEFAULT 'pending_review',
    commercial_use_allowed boolean,
    derivatives_allowed boolean,
    share_alike_required boolean,
    attribution_required boolean,
    attribution_text text,
    score numeric(5,2),
    width integer,
    height integer,
    raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    discovered_at timestamptz NOT NULL DEFAULT now(),
    rights_checked_at timestamptz,
    UNIQUE (provider, provider_asset_id)
);

CREATE TABLE media_assets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_type text NOT NULL DEFAULT 'photo',
    title text,
    description text,
    source_provider text NOT NULL,
    source_page_url text NOT NULL,
    original_file_url text,
    local_storage_key text,
    creator_name text,
    rights_holder text,
    licence_name text,
    licence_version text,
    licence_url text,
    rights_status text NOT NULL,
    commercial_use_allowed boolean NOT NULL DEFAULT false,
    derivatives_allowed boolean NOT NULL DEFAULT false,
    share_alike_required boolean NOT NULL DEFAULT false,
    attribution_required boolean NOT NULL DEFAULT true,
    attribution_text text,
    attribution_url text,
    permission_reference text,
    rights_checked_at timestamptz NOT NULL,
    rights_expires_at timestamptz,
    original_filename text,
    mime_type text,
    width integer,
    height integer,
    file_size bigint,
    checksum text,
    perceptual_hash text,
    alt_text text,
    editorial_notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE media_asset_usages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    media_asset_id uuid NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    object_type text NOT NULL,
    object_id uuid NOT NULL,
    placement text NOT NULL,
    crop_variant text,
    published_at timestamptz,
    removed_at timestamptz,
    notes text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX stories_status_idx ON stories(status);
CREATE INDEX stories_updated_at_idx ON stories(updated_at DESC);
CREATE INDEX stories_title_trgm_idx ON stories USING gin (title gin_trgm_ops);
CREATE INDEX evidence_story_idx ON evidence(story_id);
CREATE INDEX races_season_round_idx ON races(season, round);
CREATE INDEX media_candidates_rights_idx ON media_candidates(rights_status);
CREATE INDEX media_assets_rights_idx ON media_assets(rights_status);
CREATE INDEX media_asset_usages_asset_idx ON media_asset_usages(media_asset_id);
