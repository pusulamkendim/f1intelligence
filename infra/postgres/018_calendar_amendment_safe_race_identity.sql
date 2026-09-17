-- Repair the 2026 calendar after the Bahrain Grand Prix was added at Sepang.
-- Race identity must remain canonical even when ordinal round numbers change.
--
-- The original 2026 registry seed had 22 races, with Singapore at round 16.
-- The amended calendar has Bahrain Grand Prix in Malaysia at round 16 and moves
-- Singapore through Abu Dhabi one round later. Older Jolpica calendar ingestion
-- reconciled on (season, round), which could therefore shift canonical identity.

INSERT INTO entities (
    entity_type,
    slug,
    display_name,
    active_from_season,
    active_to_season,
    metadata
)
VALUES (
    'race',
    '2026-bahrain-grand-prix-in-malaysia',
    '2026 Bahrain Grand Prix in Malaysia',
    2026,
    2026,
    '{"source":"formula1.com/en/racing/2026/bahrain","calendar_amendment":true}'::jsonb
)
ON CONFLICT (entity_type, slug) DO UPDATE
SET display_name = EXCLUDED.display_name,
    active_from_season = EXCLUDED.active_from_season,
    active_to_season = EXCLUDED.active_to_season,
    metadata = entities.metadata || EXCLUDED.metadata,
    updated_at = now();

INSERT INTO entity_aliases (
    entity_id,
    alias,
    alias_type,
    confidence,
    valid_from_season,
    valid_to_season
)
SELECT e.id, seed.alias, seed.alias_type, seed.confidence, 2026, 2026
FROM entities e
JOIN (
    VALUES
        ('2026-bahrain-grand-prix-in-malaysia', '2026 Bahrain Grand Prix in Malaysia', 'canonical', 100),
        ('2026-bahrain-grand-prix-in-malaysia', 'Bahrain Grand Prix in Malaysia', 'race_name', 100),
        ('2026-bahrain-grand-prix-in-malaysia', 'Sepang International Circuit', 'venue', 95),
        ('2026-bahrain-grand-prix-in-malaysia', 'Sepang', 'venue', 90),
        ('2026-madrid-grand-prix', 'Spanish Grand Prix', 'race_name', 96)
) AS seed(slug, alias, alias_type, confidence) ON seed.slug = e.slug
WHERE e.entity_type = 'race'
ON CONFLICT (entity_id, alias) DO UPDATE
SET alias_type = EXCLUDED.alias_type,
    confidence = EXCLUDED.confidence,
    valid_from_season = EXCLUDED.valid_from_season,
    valid_to_season = EXCLUDED.valid_to_season,
    enabled = true,
    updated_at = now();

DO $$
DECLARE
    calendar_already_ingested boolean;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM races
        WHERE season = 2026
          AND official_name = 'Bahrain Grand Prix in Malaysia'
    ) INTO calendar_already_ingested;

    IF calendar_already_ingested THEN
        -- A Jolpica sync already wrote amended race names/dates by ordinal round.
        -- Release unique identity/round constraints, then reattach each current
        -- calendar row to the canonical race matching its actual event name.
        UPDATE races
        SET round = round + 100,
            slug = '__018_calendar_repair_' || id::text,
            entity_id = NULL,
            updated_at = now()
        WHERE season = 2026
          AND round BETWEEN 16 AND 23;

        WITH mapping(official_name, round, slug) AS (
            VALUES
                ('Bahrain Grand Prix in Malaysia', 16, '2026-bahrain-grand-prix-in-malaysia'),
                ('Singapore Grand Prix', 17, '2026-singapore-grand-prix'),
                ('United States Grand Prix', 18, '2026-united-states-grand-prix'),
                ('Mexico City Grand Prix', 19, '2026-mexico-grand-prix'),
                ('Brazilian Grand Prix', 20, '2026-sao-paulo-grand-prix'),
                ('Las Vegas Grand Prix', 21, '2026-las-vegas-grand-prix'),
                ('Qatar Grand Prix', 22, '2026-qatar-grand-prix'),
                ('Abu Dhabi Grand Prix', 23, '2026-abu-dhabi-grand-prix')
        )
        UPDATE races r
        SET round = mapping.round,
            slug = mapping.slug,
            entity_id = e.id,
            updated_at = now()
        FROM mapping
        JOIN entities e
          ON e.entity_type = 'race'
         AND e.slug = mapping.slug
        WHERE r.season = 2026
          AND r.official_name = mapping.official_name;
    ELSE
        -- Fresh databases still contain the original 22-race seed. Preserve the
        -- existing race/entity identities and only move their mutable round.
        UPDATE races
        SET round = round + 100,
            updated_at = now()
        WHERE season = 2026
          AND round BETWEEN 16 AND 22;

        WITH mapping(slug, round) AS (
            VALUES
                ('2026-singapore-grand-prix', 17),
                ('2026-united-states-grand-prix', 18),
                ('2026-mexico-grand-prix', 19),
                ('2026-sao-paulo-grand-prix', 20),
                ('2026-las-vegas-grand-prix', 21),
                ('2026-qatar-grand-prix', 22),
                ('2026-abu-dhabi-grand-prix', 23)
        )
        UPDATE races r
        SET round = mapping.round,
            updated_at = now()
        FROM mapping
        WHERE r.season = 2026
          AND r.slug = mapping.slug;

        INSERT INTO races (
            season,
            round,
            slug,
            official_name,
            circuit,
            country,
            start_at,
            weekend_start_date,
            weekend_end_date,
            status,
            entity_id,
            source_url
        )
        SELECT
            2026,
            16,
            e.slug,
            'Bahrain Grand Prix in Malaysia',
            'Sepang International Circuit',
            'Malaysia',
            '2026-10-04 07:00:00+00'::timestamptz,
            DATE '2026-10-02',
            DATE '2026-10-04',
            'upcoming',
            e.id,
            'https://www.formula1.com/en/racing/2026/bahrain'
        FROM entities e
        WHERE e.entity_type = 'race'
          AND e.slug = '2026-bahrain-grand-prix-in-malaysia'
        ON CONFLICT (season, slug) DO UPDATE
        SET round = EXCLUDED.round,
            official_name = EXCLUDED.official_name,
            circuit = EXCLUDED.circuit,
            country = EXCLUDED.country,
            start_at = EXCLUDED.start_at,
            weekend_start_date = EXCLUDED.weekend_start_date,
            weekend_end_date = EXCLUDED.weekend_end_date,
            entity_id = EXCLUDED.entity_id,
            source_url = EXCLUDED.source_url,
            updated_at = now();
    END IF;
END
$$;

-- Fail the migration instead of silently leaving a partially canonicalized season.
DO $$
DECLARE
    race_count integer;
    canonical_count integer;
    distinct_entity_count integer;
BEGIN
    SELECT COUNT(*), COUNT(entity_id), COUNT(DISTINCT entity_id)
    INTO race_count, canonical_count, distinct_entity_count
    FROM races
    WHERE season = 2026
      AND round BETWEEN 1 AND 23;

    IF race_count <> 23
       OR canonical_count <> 23
       OR distinct_entity_count <> 23 THEN
        RAISE EXCEPTION
            '2026 race identity repair failed: races=%, canonical=%, distinct_entities=%',
            race_count, canonical_count, distinct_entity_count;
    END IF;
END
$$;
