-- Link provider-native structured data to the canonical entity registry.
-- Provider IDs remain on imported rows for provenance/debugging; canonical entity IDs
-- make Team/Driver/Race product reads independent of a particular upstream provider.

CREATE TABLE IF NOT EXISTS entity_provider_ids (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id uuid NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    provider text NOT NULL,
    provider_entity_type text NOT NULL CHECK (provider_entity_type IN ('driver', 'constructor')),
    provider_id text NOT NULL,
    valid_from_season integer,
    valid_to_season integer,
    source_url text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_entity_type, provider_id)
);

CREATE INDEX IF NOT EXISTS entity_provider_ids_entity_idx
    ON entity_provider_ids(entity_id);

-- Yuki Tsunoda participated in the 2026 season before leaving the current grid.
-- Keep historical participants in the registry even when they are no longer in the
-- current team-role snapshot, otherwise early-season classifications cannot resolve.
INSERT INTO entities (
    entity_type, slug, display_name, active_from_season, active_to_season, metadata
)
VALUES (
    'person',
    'yuki-tsunoda',
    'Yuki Tsunoda',
    2026,
    2026,
    '{"kind":"driver","participation":"historical_2026"}'::jsonb
)
ON CONFLICT (entity_type, slug) DO UPDATE
SET display_name = EXCLUDED.display_name,
    active_to_season = EXCLUDED.active_to_season,
    metadata = entities.metadata || EXCLUDED.metadata,
    updated_at = now();

INSERT INTO persons (entity_id, slug, display_name, nationality_code)
SELECT id, slug, display_name, 'JPN'
FROM entities
WHERE entity_type = 'person' AND slug = 'yuki-tsunoda'
ON CONFLICT (slug) DO UPDATE
SET entity_id = EXCLUDED.entity_id,
    display_name = EXCLUDED.display_name,
    nationality_code = EXCLUDED.nationality_code,
    updated_at = now();

INSERT INTO entity_aliases (
    entity_id, alias, alias_type, confidence, valid_from_season, valid_to_season
)
SELECT e.id, seed.alias, seed.alias_type, seed.confidence, 2026, 2026
FROM entities e
JOIN (
    VALUES
        ('Yuki Tsunoda', 'canonical', 100),
        ('Tsunoda', 'surname', 92),
        ('TSU', 'driver_code', 86),
        ('Car 22', 'car_number', 99)
) AS seed(alias, alias_type, confidence) ON true
WHERE e.entity_type = 'person' AND e.slug = 'yuki-tsunoda'
ON CONFLICT (entity_id, alias) DO UPDATE
SET alias_type = EXCLUDED.alias_type,
    confidence = EXCLUDED.confidence,
    valid_from_season = EXCLUDED.valid_from_season,
    valid_to_season = EXCLUDED.valid_to_season,
    enabled = true,
    updated_at = now();

-- Jolpica/Ergast-compatible IDs observed in the 2026 standings feed.
INSERT INTO entity_provider_ids (
    entity_id, provider, provider_entity_type, provider_id,
    valid_from_season, valid_to_season, source_url
)
SELECT e.id, 'jolpica', 'driver', seed.provider_id, 2026, 2026,
       'https://api.jolpi.ca/ergast/f1/2026/driverstandings.json'
FROM entities e
JOIN (
    VALUES
        ('george-russell', 'russell'),
        ('kimi-antonelli', 'antonelli'),
        ('charles-leclerc', 'leclerc'),
        ('lewis-hamilton', 'hamilton'),
        ('lando-norris', 'norris'),
        ('oscar-piastri', 'piastri'),
        ('max-verstappen', 'max_verstappen'),
        ('isack-hadjar', 'hadjar'),
        ('liam-lawson', 'lawson'),
        ('arvid-lindblad', 'arvid_lindblad'),
        ('pierre-gasly', 'gasly'),
        ('franco-colapinto', 'colapinto'),
        ('esteban-ocon', 'ocon'),
        ('oliver-bearman', 'bearman'),
        ('nico-hulkenberg', 'hulkenberg'),
        ('gabriel-bortoleto', 'bortoleto'),
        ('carlos-sainz', 'sainz'),
        ('alexander-albon', 'albon'),
        ('fernando-alonso', 'alonso'),
        ('yuki-tsunoda', 'tsunoda'),
        ('lance-stroll', 'stroll'),
        ('valtteri-bottas', 'bottas'),
        ('sergio-perez', 'perez')
) AS seed(slug, provider_id) ON seed.slug = e.slug
WHERE e.entity_type = 'person'
ON CONFLICT (provider, provider_entity_type, provider_id) DO UPDATE
SET entity_id = EXCLUDED.entity_id,
    valid_from_season = EXCLUDED.valid_from_season,
    valid_to_season = EXCLUDED.valid_to_season,
    source_url = EXCLUDED.source_url,
    updated_at = now();

INSERT INTO entity_provider_ids (
    entity_id, provider, provider_entity_type, provider_id,
    valid_from_season, valid_to_season, source_url
)
SELECT e.id, 'jolpica', 'constructor', seed.provider_id, 2026, 2026,
       'https://api.jolpi.ca/ergast/f1/2026/driverstandings.json'
FROM entities e
JOIN (
    VALUES
        ('mclaren', 'mclaren'),
        ('mercedes', 'mercedes'),
        ('red-bull-racing', 'red_bull'),
        ('ferrari', 'ferrari'),
        ('williams', 'williams'),
        ('racing-bulls', 'rb'),
        ('aston-martin', 'aston_martin'),
        ('haas', 'haas'),
        ('audi', 'audi'),
        ('alpine', 'alpine'),
        ('cadillac', 'cadillac')
) AS seed(slug, provider_id) ON seed.slug = e.slug
WHERE e.entity_type = 'team'
ON CONFLICT (provider, provider_entity_type, provider_id) DO UPDATE
SET entity_id = EXCLUDED.entity_id,
    valid_from_season = EXCLUDED.valid_from_season,
    valid_to_season = EXCLUDED.valid_to_season,
    source_url = EXCLUDED.source_url,
    updated_at = now();

ALTER TABLE race_results
    ADD COLUMN IF NOT EXISTS driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS team_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL;

ALTER TABLE qualifying_results
    ADD COLUMN IF NOT EXISTS driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS team_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL;

ALTER TABLE driver_standing_rows
    ADD COLUMN IF NOT EXISTS driver_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL;

ALTER TABLE constructor_standing_rows
    ADD COLUMN IF NOT EXISTS team_entity_id uuid REFERENCES entities(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS race_results_driver_entity_idx ON race_results(driver_entity_id);
CREATE INDEX IF NOT EXISTS race_results_team_entity_idx ON race_results(team_entity_id);
CREATE INDEX IF NOT EXISTS qualifying_results_driver_entity_idx ON qualifying_results(driver_entity_id);
CREATE INDEX IF NOT EXISTS qualifying_results_team_entity_idx ON qualifying_results(team_entity_id);
CREATE INDEX IF NOT EXISTS driver_standing_rows_driver_entity_idx ON driver_standing_rows(driver_entity_id);
CREATE INDEX IF NOT EXISTS constructor_standing_rows_team_entity_idx ON constructor_standing_rows(team_entity_id);

-- Backfill any structured rows imported before this migration.
UPDATE race_results rr
SET driver_entity_id = epi.entity_id
FROM entity_provider_ids epi
WHERE rr.driver_entity_id IS NULL
  AND epi.provider = rr.provider
  AND epi.provider_entity_type = 'driver'
  AND epi.provider_id = rr.driver_provider_id;

UPDATE race_results rr
SET team_entity_id = epi.entity_id
FROM entity_provider_ids epi
WHERE rr.team_entity_id IS NULL
  AND epi.provider = rr.provider
  AND epi.provider_entity_type = 'constructor'
  AND epi.provider_id = rr.constructor_provider_id;

UPDATE qualifying_results qr
SET driver_entity_id = epi.entity_id
FROM entity_provider_ids epi
WHERE qr.driver_entity_id IS NULL
  AND epi.provider = qr.provider
  AND epi.provider_entity_type = 'driver'
  AND epi.provider_id = qr.driver_provider_id;

UPDATE qualifying_results qr
SET team_entity_id = epi.entity_id
FROM entity_provider_ids epi
WHERE qr.team_entity_id IS NULL
  AND epi.provider = qr.provider
  AND epi.provider_entity_type = 'constructor'
  AND epi.provider_id = qr.constructor_provider_id;

UPDATE driver_standing_rows dsr
SET driver_entity_id = epi.entity_id
FROM driver_standings_snapshots dss, entity_provider_ids epi
WHERE dsr.snapshot_id = dss.id
  AND dsr.driver_entity_id IS NULL
  AND epi.provider = dss.provider
  AND epi.provider_entity_type = 'driver'
  AND epi.provider_id = dsr.driver_provider_id;

UPDATE constructor_standing_rows csr
SET team_entity_id = epi.entity_id
FROM constructor_standings_snapshots css, entity_provider_ids epi
WHERE csr.snapshot_id = css.id
  AND csr.team_entity_id IS NULL
  AND epi.provider = css.provider
  AND epi.provider_entity_type = 'constructor'
  AND epi.provider_id = csr.constructor_provider_id;
