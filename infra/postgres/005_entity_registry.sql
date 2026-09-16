CREATE TABLE IF NOT EXISTS entities (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type text NOT NULL CHECK (entity_type IN ('team', 'person', 'race', 'regulation', 'topic')),
    slug text NOT NULL,
    display_name text NOT NULL,
    active_from_season integer,
    active_to_season integer,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (entity_type, slug)
);

CREATE INDEX IF NOT EXISTS entities_type_idx ON entities(entity_type);
CREATE INDEX IF NOT EXISTS entities_display_name_trgm_idx ON entities USING gin (display_name gin_trgm_ops);

ALTER TABLE teams
    ADD COLUMN IF NOT EXISTS entity_id uuid REFERENCES entities(id) ON DELETE SET NULL;

CREATE UNIQUE INDEX IF NOT EXISTS teams_entity_id_idx
    ON teams(entity_id)
    WHERE entity_id IS NOT NULL;

ALTER TABLE races
    ADD COLUMN IF NOT EXISTS entity_id uuid REFERENCES entities(id) ON DELETE SET NULL;
ALTER TABLE races
    ADD COLUMN IF NOT EXISTS weekend_start_date date;
ALTER TABLE races
    ADD COLUMN IF NOT EXISTS weekend_end_date date;

CREATE UNIQUE INDEX IF NOT EXISTS races_entity_id_idx
    ON races(entity_id)
    WHERE entity_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS persons (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id uuid NOT NULL UNIQUE REFERENCES entities(id) ON DELETE CASCADE,
    slug text NOT NULL UNIQUE,
    display_name text NOT NULL,
    nationality_code text,
    birth_date date,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS entity_aliases (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id uuid NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    alias text NOT NULL,
    alias_type text NOT NULL DEFAULT 'common',
    confidence smallint NOT NULL DEFAULT 90 CHECK (confidence BETWEEN 1 AND 100),
    valid_from_season integer,
    valid_to_season integer,
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (entity_id, alias)
);

CREATE INDEX IF NOT EXISTS entity_aliases_entity_idx ON entity_aliases(entity_id);
CREATE INDEX IF NOT EXISTS entity_aliases_lower_alias_idx ON entity_aliases(lower(alias));

CREATE TABLE IF NOT EXISTS team_person_roles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    person_id uuid NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    role text NOT NULL,
    season integer NOT NULL,
    car_number smallint,
    valid_from date,
    valid_to date,
    source_url text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (team_id, person_id, role, season)
);

CREATE INDEX IF NOT EXISTS team_person_roles_team_season_idx
    ON team_person_roles(team_id, season);
CREATE INDEX IF NOT EXISTS team_person_roles_person_season_idx
    ON team_person_roles(person_id, season);

CREATE TABLE IF NOT EXISTS story_entities (
    story_id uuid NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    entity_id uuid NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation_type text NOT NULL DEFAULT 'mentioned',
    confidence smallint NOT NULL DEFAULT 90 CHECK (confidence BETWEEN 1 AND 100),
    match_method text NOT NULL DEFAULT 'alias',
    matched_alias text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (story_id, entity_id)
);

CREATE INDEX IF NOT EXISTS story_entities_entity_idx ON story_entities(entity_id);
