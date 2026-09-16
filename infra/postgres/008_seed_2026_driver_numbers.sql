-- 2026 driver numbers verified against Formula1.com's published 2026 grid.
-- Number aliases deliberately include the "Car" prefix to avoid false matches
-- on document numbers, dates, lap counts and other bare numerals.

UPDATE team_person_roles tpr
SET car_number = seed.car_number,
    updated_at = now()
FROM persons p
JOIN (
    VALUES
        ('lando-norris', 1),
        ('max-verstappen', 3),
        ('gabriel-bortoleto', 5),
        ('isack-hadjar', 6),
        ('pierre-gasly', 10),
        ('sergio-perez', 11),
        ('kimi-antonelli', 12),
        ('fernando-alonso', 14),
        ('charles-leclerc', 16),
        ('lance-stroll', 18),
        ('alexander-albon', 23),
        ('nico-hulkenberg', 27),
        ('liam-lawson', 30),
        ('esteban-ocon', 31),
        ('arvid-lindblad', 41),
        ('franco-colapinto', 43),
        ('lewis-hamilton', 44),
        ('carlos-sainz', 55),
        ('george-russell', 63),
        ('valtteri-bottas', 77),
        ('oscar-piastri', 81),
        ('oliver-bearman', 87)
) AS seed(person_slug, car_number) ON seed.person_slug = p.slug
WHERE tpr.person_id = p.id
  AND tpr.role = 'driver'
  AND tpr.season = 2026;

INSERT INTO entity_aliases (
    entity_id,
    alias,
    alias_type,
    confidence,
    valid_from_season,
    valid_to_season
)
SELECT
    p.entity_id,
    'Car ' || seed.car_number::text,
    'car_number',
    99,
    2026,
    2026
FROM persons p
JOIN (
    VALUES
        ('lando-norris', 1),
        ('max-verstappen', 3),
        ('gabriel-bortoleto', 5),
        ('isack-hadjar', 6),
        ('pierre-gasly', 10),
        ('sergio-perez', 11),
        ('kimi-antonelli', 12),
        ('fernando-alonso', 14),
        ('charles-leclerc', 16),
        ('lance-stroll', 18),
        ('alexander-albon', 23),
        ('nico-hulkenberg', 27),
        ('liam-lawson', 30),
        ('esteban-ocon', 31),
        ('arvid-lindblad', 41),
        ('franco-colapinto', 43),
        ('lewis-hamilton', 44),
        ('carlos-sainz', 55),
        ('george-russell', 63),
        ('valtteri-bottas', 77),
        ('oscar-piastri', 81),
        ('oliver-bearman', 87)
) AS seed(person_slug, car_number) ON seed.person_slug = p.slug
ON CONFLICT (entity_id, alias) DO UPDATE
SET alias_type = EXCLUDED.alias_type,
    confidence = EXCLUDED.confidence,
    valid_from_season = EXCLUDED.valid_from_season,
    valid_to_season = EXCLUDED.valid_to_season,
    enabled = true,
    updated_at = now();
