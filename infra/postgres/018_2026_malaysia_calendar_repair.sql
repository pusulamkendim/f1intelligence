-- Repair the 2026 canonical race registry after the Bahrain Grand Prix was
-- rescheduled to Sepang, Malaysia for 2-4 October 2026.
--
-- The original registry snapshot contained 22 post-cancellation races. When
-- Jolpica later exposed the restored Bahrain round as round 16, the persisted
-- race rows kept the old canonical slugs/entity IDs from round 16 onward. This
-- migration adds the missing canonical race entity and realigns rounds 16-23
-- without changing race primary keys, so structured-data foreign keys remain
-- intact.
--
-- Official provenance:
-- https://www.fia.com/news/fia-and-fom-confirm-malaysia-will-join-2026-calendar-host-venue-bahrain-grand-prix
-- https://www.formula1.com/en/racing/2026/bahrain

INSERT INTO entities (
    entity_type, slug, display_name, active_from_season, active_to_season, metadata
)
VALUES (
    'race',
    '2026-bahrain-grand-prix-in-malaysia',
    '2026 Bahrain Grand Prix in Malaysia',
    2026,
    2026,
    '{"source":"fia.com","calendar_update":"2026-07-26","venue":"Sepang International Circuit"}'::jsonb
)
ON CONFLICT (entity_type, slug) DO UPDATE
SET display_name = EXCLUDED.display_name,
    active_from_season = EXCLUDED.active_from_season,
    active_to_season = EXCLUDED.active_to_season,
    metadata = entities.metadata || EXCLUDED.metadata,
    updated_at = now();

INSERT INTO entity_aliases (
    entity_id, alias, alias_type, confidence, valid_from_season, valid_to_season
)
SELECT e.id, seed.alias, seed.alias_type, seed.confidence, 2026, 2026
FROM entities e
JOIN (
    VALUES
        ('Bahrain Grand Prix in Malaysia', 'race_name', 100),
        ('Bahrain GP in Malaysia', 'race_name', 98),
        ('Bahrain Grand Prix', 'race_name', 94),
        ('Sepang', 'venue', 90),
        ('Sepang International Circuit', 'venue', 96)
) AS seed(alias, alias_type, confidence) ON true
WHERE e.entity_type = 'race'
  AND e.slug = '2026-bahrain-grand-prix-in-malaysia'
ON CONFLICT (entity_id, alias) DO UPDATE
SET alias_type = EXCLUDED.alias_type,
    confidence = EXCLUDED.confidence,
    valid_from_season = EXCLUDED.valid_from_season,
    valid_to_season = EXCLUDED.valid_to_season,
    enabled = true,
    updated_at = now();

-- Release the stale one-to-one entity assignments and season/slug values first;
-- otherwise correcting the shifted rows can collide with the row immediately
-- after it. Primary keys are deliberately retained.
UPDATE races
SET entity_id = NULL,
    slug = '__2026_calendar_repair_round_' || round,
    updated_at = now()
WHERE season = 2026
  AND round BETWEEN 16 AND 23;

WITH expected(round, slug, official_name, circuit, country, weekend_start, weekend_end) AS (
    VALUES
        (16, '2026-bahrain-grand-prix-in-malaysia', 'Bahrain Grand Prix in Malaysia', 'Sepang International Circuit', 'Malaysia', DATE '2026-10-02', DATE '2026-10-04'),
        (17, '2026-singapore-grand-prix', 'Singapore Grand Prix', 'Marina Bay Street Circuit', 'Singapore', DATE '2026-10-09', DATE '2026-10-11'),
        (18, '2026-united-states-grand-prix', 'United States Grand Prix', 'Circuit of the Americas', 'United States', DATE '2026-10-23', DATE '2026-10-25'),
        (19, '2026-mexico-grand-prix', 'Mexico City Grand Prix', 'Autodromo Hermanos Rodriguez', 'Mexico', DATE '2026-10-30', DATE '2026-11-01'),
        (20, '2026-sao-paulo-grand-prix', 'Brazilian Grand Prix', 'Interlagos', 'Brazil', DATE '2026-11-06', DATE '2026-11-08'),
        (21, '2026-las-vegas-grand-prix', 'Las Vegas Grand Prix', 'Las Vegas Strip Circuit', 'United States', DATE '2026-11-19', DATE '2026-11-21'),
        (22, '2026-qatar-grand-prix', 'Qatar Grand Prix', 'Lusail International Circuit', 'Qatar', DATE '2026-11-27', DATE '2026-11-29'),
        (23, '2026-abu-dhabi-grand-prix', 'Abu Dhabi Grand Prix', 'Yas Marina Circuit', 'United Arab Emirates', DATE '2026-12-04', DATE '2026-12-06')
), updated AS (
    UPDATE races r
    SET slug = x.slug,
        official_name = CASE WHEN r.provider IS NULL THEN x.official_name ELSE r.official_name END,
        circuit = CASE WHEN r.provider IS NULL THEN x.circuit ELSE r.circuit END,
        country = CASE WHEN r.provider IS NULL THEN x.country ELSE r.country END,
        weekend_start_date = x.weekend_start,
        weekend_end_date = x.weekend_end,
        entity_id = e.id,
        updated_at = now()
    FROM expected x
    JOIN entities e
      ON e.entity_type = 'race' AND e.slug = x.slug
    WHERE r.season = 2026 AND r.round = x.round
    RETURNING r.round
)
SELECT count(*) FROM updated;

-- A fresh database seeded from the pre-Malaysia snapshot has no round 23 row.
-- Add it without inventing provider identity or retrieval timestamps; a later
-- provider sync can enrich those fields idempotently via (season, round).
INSERT INTO races (
    season, round, slug, official_name, circuit, country,
    weekend_start_date, weekend_end_date, status, entity_id
)
SELECT
    2026, 23, '2026-abu-dhabi-grand-prix', 'Abu Dhabi Grand Prix',
    'Yas Marina Circuit', 'United Arab Emirates',
    DATE '2026-12-04', DATE '2026-12-06', 'upcoming', e.id
FROM entities e
WHERE e.entity_type = 'race' AND e.slug = '2026-abu-dhabi-grand-prix'
ON CONFLICT (season, round) DO UPDATE
SET slug = EXCLUDED.slug,
    entity_id = EXCLUDED.entity_id,
    weekend_start_date = EXCLUDED.weekend_start_date,
    weekend_end_date = EXCLUDED.weekend_end_date,
    updated_at = now();

-- Fail loudly if the registry can still produce a shifted or missing canonical
-- mapping. This keeps repeated migration runs idempotent and self-validating.
DO $$
DECLARE
    bad_count integer;
BEGIN
    SELECT count(*) INTO bad_count
    FROM races r
    LEFT JOIN entities e ON e.id = r.entity_id
    WHERE r.season = 2026
      AND r.round BETWEEN 16 AND 23
      AND (
          e.id IS NULL
          OR r.slug <> e.slug
          OR e.entity_type <> 'race'
      );

    IF bad_count <> 0 THEN
        RAISE EXCEPTION '2026 canonical calendar repair left % invalid race mappings', bad_count;
    END IF;
END
$$;