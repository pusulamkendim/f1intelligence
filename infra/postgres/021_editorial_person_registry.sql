-- Curated non-grid people observed in editorial coverage.
-- Keep this migration replay-safe: these are canonical identities, not article-derived
-- free-text guesses. Additional people should be added here (or by a future trusted
-- identity provider) before deterministic source classification links to them.

INSERT INTO entities (entity_type, slug, display_name, metadata)
VALUES
    ('person', 'mike-elliott', 'Mike Elliott', '{"kind":"technical_leadership","registry":"editorial_curated"}'::jsonb),
    ('person', 'nico-rosberg', 'Nico Rosberg', '{"kind":"former_driver","registry":"editorial_curated"}'::jsonb),
    ('person', 'robin-raikkonen', 'Robin Räikkönen', '{"kind":"junior_driver","registry":"editorial_curated"}'::jsonb)
ON CONFLICT (entity_type, slug) DO UPDATE
SET display_name = EXCLUDED.display_name,
    metadata = entities.metadata || EXCLUDED.metadata,
    updated_at = now();

INSERT INTO persons (entity_id, slug, display_name)
SELECT id, slug, display_name
FROM entities
WHERE entity_type = 'person'
  AND slug IN ('mike-elliott', 'nico-rosberg', 'robin-raikkonen')
ON CONFLICT (slug) DO UPDATE
SET entity_id = EXCLUDED.entity_id,
    display_name = EXCLUDED.display_name,
    updated_at = now();

INSERT INTO entity_aliases (entity_id, alias, alias_type, confidence)
SELECT e.id, seed.alias, seed.alias_type, seed.confidence
FROM entities e
JOIN (
    VALUES
        ('mike-elliott', 'Mike Elliott', 'canonical', 100),
        ('mike-elliott', 'Elliott', 'surname', 92),
        ('nico-rosberg', 'Nico Rosberg', 'canonical', 100),
        ('nico-rosberg', 'Rosberg', 'surname', 92),
        ('robin-raikkonen', 'Robin Räikkönen', 'canonical', 100),
        ('robin-raikkonen', 'Robin Raikkonen', 'common', 98)
) AS seed(slug, alias, alias_type, confidence)
  ON seed.slug = e.slug
WHERE e.entity_type = 'person'
ON CONFLICT (entity_id, alias) DO UPDATE
SET alias_type = EXCLUDED.alias_type,
    confidence = EXCLUDED.confidence,
    enabled = true,
    updated_at = now();
