-- Historical 2025 canonical roster/provider mappings for structured Jolpica imports.
-- Keep season validity explicit instead of bypassing entity-provider validity checks.

-- Drivers who participated in 2025 but were originally seeded from the 2026 snapshot
-- are the same canonical people, so extend their active range backwards.
UPDATE entities
SET active_from_season = LEAST(COALESCE(active_from_season, 2025), 2025),
    updated_at = now()
WHERE entity_type = 'person'
  AND slug IN (
      'alexander-albon',
      'fernando-alonso',
      'kimi-antonelli',
      'oliver-bearman',
      'gabriel-bortoleto',
      'franco-colapinto',
      'pierre-gasly',
      'isack-hadjar',
      'lewis-hamilton',
      'nico-hulkenberg',
      'liam-lawson',
      'charles-leclerc',
      'lando-norris',
      'esteban-ocon',
      'oscar-piastri',
      'george-russell',
      'carlos-sainz',
      'lance-stroll',
      'yuki-tsunoda',
      'max-verstappen'
  );

-- Jack Doohan is required for early-2025 Alpine race classifications.
INSERT INTO entities (
    entity_type,
    slug,
    display_name,
    active_from_season,
    active_to_season,
    metadata
)
VALUES (
    'person',
    'jack-doohan',
    'Jack Doohan',
    2025,
    2025,
    '{"kind":"driver","participation":"historical_2025"}'::jsonb
)
ON CONFLICT (entity_type, slug) DO UPDATE
SET display_name = EXCLUDED.display_name,
    active_from_season = LEAST(
        COALESCE(entities.active_from_season, EXCLUDED.active_from_season),
        EXCLUDED.active_from_season
    ),
    active_to_season = GREATEST(
        COALESCE(entities.active_to_season, EXCLUDED.active_to_season),
        EXCLUDED.active_to_season
    ),
    metadata = entities.metadata || EXCLUDED.metadata,
    updated_at = now();

INSERT INTO persons (
    entity_id,
    slug,
    display_name,
    nationality_code
)
SELECT id, slug, display_name, 'AUS'
FROM entities
WHERE entity_type = 'person'
  AND slug = 'jack-doohan'
ON CONFLICT (slug) DO UPDATE
SET entity_id = EXCLUDED.entity_id,
    display_name = EXCLUDED.display_name,
    nationality_code = EXCLUDED.nationality_code,
    updated_at = now();

INSERT INTO entity_aliases (
    entity_id,
    alias,
    alias_type,
    confidence,
    valid_from_season,
    valid_to_season
)
SELECT e.id, seed.alias, seed.alias_type, seed.confidence, 2025, 2025
FROM entities e
JOIN (
    VALUES
        ('Jack Doohan', 'canonical', 100),
        ('Doohan', 'surname', 92),
        ('DOO', 'driver_code', 86)
) AS seed(alias, alias_type, confidence) ON true
WHERE e.entity_type = 'person'
  AND e.slug = 'jack-doohan'
ON CONFLICT (entity_id, alias) DO UPDATE
SET alias_type = EXCLUDED.alias_type,
    confidence = EXCLUDED.confidence,
    valid_from_season = LEAST(
        COALESCE(entity_aliases.valid_from_season, EXCLUDED.valid_from_season),
        EXCLUDED.valid_from_season
    ),
    valid_to_season = GREATEST(
        COALESCE(entity_aliases.valid_to_season, EXCLUDED.valid_to_season),
        EXCLUDED.valid_to_season
    ),
    enabled = true,
    updated_at = now();

-- Existing 2026 driver provider IDs represent the same people in 2025.
UPDATE entity_provider_ids
SET valid_from_season = LEAST(
        COALESCE(valid_from_season, 2025),
        2025
    ),
    updated_at = now()
WHERE provider = 'jolpica'
  AND provider_entity_type = 'driver'
  AND provider_id IN (
      'albon',
      'alonso',
      'antonelli',
      'bearman',
      'bortoleto',
      'colapinto',
      'gasly',
      'hadjar',
      'hamilton',
      'hulkenberg',
      'lawson',
      'leclerc',
      'max_verstappen',
      'norris',
      'ocon',
      'piastri',
      'russell',
      'sainz',
      'stroll',
      'tsunoda'
  );

INSERT INTO entity_provider_ids (
    entity_id,
    provider,
    provider_entity_type,
    provider_id,
    valid_from_season,
    valid_to_season,
    source_url
)
SELECT e.id,
       'jolpica',
       'driver',
       'doohan',
       2025,
       2025,
       'https://api.jolpi.ca/ergast/f1/2025/driverstandings.json'
FROM entities e
WHERE e.entity_type = 'person'
  AND e.slug = 'jack-doohan'
ON CONFLICT (provider, provider_entity_type, provider_id) DO UPDATE
SET entity_id = EXCLUDED.entity_id,
    valid_from_season = LEAST(
        COALESCE(entity_provider_ids.valid_from_season, EXCLUDED.valid_from_season),
        EXCLUDED.valid_from_season
    ),
    valid_to_season = GREATEST(
        COALESCE(entity_provider_ids.valid_to_season, EXCLUDED.valid_to_season),
        EXCLUDED.valid_to_season
    ),
    source_url = EXCLUDED.source_url,
    updated_at = now();

-- Most 2025 constructors continue as the same canonical team identity in 2026.
UPDATE entities
SET active_from_season = LEAST(COALESCE(active_from_season, 2025), 2025),
    updated_at = now()
WHERE entity_type = 'team'
  AND slug IN (
      'mclaren',
      'mercedes',
      'red-bull-racing',
      'ferrari',
      'williams',
      'racing-bulls',
      'aston-martin',
      'haas',
      'alpine'
  );

UPDATE entity_provider_ids
SET valid_from_season = LEAST(
        COALESCE(valid_from_season, 2025),
        2025
    ),
    updated_at = now()
WHERE provider = 'jolpica'
  AND provider_entity_type = 'constructor'
  AND provider_id IN (
      'mclaren',
      'mercedes',
      'red_bull',
      'ferrari',
      'williams',
      'rb',
      'aston_martin',
      'haas',
      'alpine'
  );

-- Sauber is a distinct 2025 constructor identity; do not silently rewrite it as Audi.
INSERT INTO entities (
    entity_type,
    slug,
    display_name,
    active_from_season,
    active_to_season,
    metadata
)
VALUES (
    'team',
    'sauber',
    'Sauber',
    2025,
    2025,
    '{"kind":"constructor","participation":"historical_2025"}'::jsonb
)
ON CONFLICT (entity_type, slug) DO UPDATE
SET display_name = EXCLUDED.display_name,
    active_from_season = LEAST(
        COALESCE(entities.active_from_season, EXCLUDED.active_from_season),
        EXCLUDED.active_from_season
    ),
    active_to_season = GREATEST(
        COALESCE(entities.active_to_season, EXCLUDED.active_to_season),
        EXCLUDED.active_to_season
    ),
    metadata = entities.metadata || EXCLUDED.metadata,
    updated_at = now();

INSERT INTO teams (
    slug,
    name,
    active_season,
    entity_id
)
SELECT slug, display_name, 2025, id
FROM entities
WHERE entity_type = 'team'
  AND slug = 'sauber'
ON CONFLICT (slug) DO UPDATE
SET name = EXCLUDED.name,
    entity_id = EXCLUDED.entity_id,
    updated_at = now();

INSERT INTO entity_aliases (
    entity_id,
    alias,
    alias_type,
    confidence,
    valid_from_season,
    valid_to_season
)
SELECT e.id, seed.alias, seed.alias_type, seed.confidence, 2025, 2025
FROM entities e
JOIN (
    VALUES
        ('Sauber', 'canonical', 100),
        ('Kick Sauber', 'common', 96),
        ('Stake F1 Team Kick Sauber', 'common', 96)
) AS seed(alias, alias_type, confidence) ON true
WHERE e.entity_type = 'team'
  AND e.slug = 'sauber'
ON CONFLICT (entity_id, alias) DO UPDATE
SET alias_type = EXCLUDED.alias_type,
    confidence = EXCLUDED.confidence,
    valid_from_season = LEAST(
        COALESCE(entity_aliases.valid_from_season, EXCLUDED.valid_from_season),
        EXCLUDED.valid_from_season
    ),
    valid_to_season = GREATEST(
        COALESCE(entity_aliases.valid_to_season, EXCLUDED.valid_to_season),
        EXCLUDED.valid_to_season
    ),
    enabled = true,
    updated_at = now();

INSERT INTO entity_provider_ids (
    entity_id,
    provider,
    provider_entity_type,
    provider_id,
    valid_from_season,
    valid_to_season,
    source_url
)
SELECT e.id,
       'jolpica',
       'constructor',
       'sauber',
       2025,
       2025,
       'https://api.jolpi.ca/ergast/f1/2025/constructorstandings.json'
FROM entities e
WHERE e.entity_type = 'team'
  AND e.slug = 'sauber'
ON CONFLICT (provider, provider_entity_type, provider_id) DO UPDATE
SET entity_id = EXCLUDED.entity_id,
    valid_from_season = LEAST(
        COALESCE(
            entity_provider_ids.valid_from_season,
            EXCLUDED.valid_from_season
        ),
        EXCLUDED.valid_from_season
    ),
    valid_to_season = GREATEST(
        COALESCE(
            entity_provider_ids.valid_to_season,
            EXCLUDED.valid_to_season
        ),
        EXCLUDED.valid_to_season
    ),
    source_url = COALESCE(
        entity_provider_ids.source_url,
        EXCLUDED.source_url
    ),
    updated_at = now();

-- Canonical 2025 driver-team roster.
INSERT INTO team_person_roles (
    team_id,
    person_id,
    role,
    season,
    source_url
)
SELECT t.id,
       p.id,
       'driver',
       2025,
       'https://api.jolpi.ca/ergast/f1/2025/driverstandings.json'
FROM teams t
JOIN (
    VALUES
        ('mclaren', 'lando-norris'),
        ('mclaren', 'oscar-piastri'),
        ('ferrari', 'charles-leclerc'),
        ('ferrari', 'lewis-hamilton'),
        ('red-bull-racing', 'max-verstappen'),
        ('red-bull-racing', 'liam-lawson'),
        ('red-bull-racing', 'yuki-tsunoda'),
        ('mercedes', 'george-russell'),
        ('mercedes', 'kimi-antonelli'),
        ('aston-martin', 'fernando-alonso'),
        ('aston-martin', 'lance-stroll'),
        ('alpine', 'pierre-gasly'),
        ('alpine', 'jack-doohan'),
        ('alpine', 'franco-colapinto'),
        ('haas', 'esteban-ocon'),
        ('haas', 'oliver-bearman'),
        ('racing-bulls', 'yuki-tsunoda'),
        ('racing-bulls', 'liam-lawson'),
        ('racing-bulls', 'isack-hadjar'),
        ('sauber', 'nico-hulkenberg'),
        ('sauber', 'gabriel-bortoleto'),
        ('williams', 'carlos-sainz'),
        ('williams', 'alexander-albon')
) AS roster(team_slug, person_slug)
  ON roster.team_slug = t.slug
JOIN persons p
  ON p.slug = roster.person_slug
ON CONFLICT (team_id, person_id, role, season) DO UPDATE
SET source_url = EXCLUDED.source_url,
    updated_at = now();

-- Fail loudly if the 2025 provider map is still incomplete.
DO $$
DECLARE
    missing_drivers text;
    missing_teams text;
BEGIN
    SELECT string_agg(provider_id, ', ' ORDER BY provider_id)
    INTO missing_drivers
    FROM (
        SELECT unnest(ARRAY[
            'albon','alonso','antonelli','bearman','bortoleto','colapinto',
            'doohan','gasly','hadjar','hamilton','hulkenberg','lawson',
            'leclerc','max_verstappen','norris','ocon','piastri','russell',
            'sainz','stroll','tsunoda'
        ]) AS provider_id
    ) expected
    WHERE NOT EXISTS (
        SELECT 1
        FROM entity_provider_ids epi
        WHERE epi.provider = 'jolpica'
          AND epi.provider_entity_type = 'driver'
          AND epi.provider_id = expected.provider_id
          AND (epi.valid_from_season IS NULL OR epi.valid_from_season <= 2025)
          AND (epi.valid_to_season IS NULL OR epi.valid_to_season >= 2025)
    );

    SELECT string_agg(provider_id, ', ' ORDER BY provider_id)
    INTO missing_teams
    FROM (
        SELECT unnest(ARRAY[
            'mclaren','ferrari','red_bull','mercedes','aston_martin',
            'alpine','haas','rb','williams','sauber'
        ]) AS provider_id
    ) expected
    WHERE NOT EXISTS (
        SELECT 1
        FROM entity_provider_ids epi
        WHERE epi.provider = 'jolpica'
          AND epi.provider_entity_type = 'constructor'
          AND epi.provider_id = expected.provider_id
          AND (epi.valid_from_season IS NULL OR epi.valid_from_season <= 2025)
          AND (epi.valid_to_season IS NULL OR epi.valid_to_season >= 2025)
    );

    IF missing_drivers IS NOT NULL OR missing_teams IS NOT NULL THEN
        RAISE EXCEPTION
            '2025 Jolpica registry incomplete: drivers=%, constructors=%',
            COALESCE(missing_drivers, '<none>'),
            COALESCE(missing_teams, '<none>');
    END IF;
END
$$;
