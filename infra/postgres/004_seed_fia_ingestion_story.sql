INSERT INTO stories (
    slug,
    title,
    summary,
    status,
    significance,
    confidence,
    why_it_matters,
    what_to_watch_next
)
VALUES (
    'fia-2026-sporting-decisions',
    '2026 FIA Formula One sporting and regulatory decisions',
    'Official FIA decisions, calendar changes and regulatory developments affecting the 2026 Formula One World Championship.',
    'monitoring',
    65,
    'source-backed',
    'Sporting, regulatory and governance decisions can change results, event schedules and how teams operate during the season.',
    'New FIA decisions, World Motor Sport Council updates, appeals, calendar changes and regulation notices.'
)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO story_ingestion_rules (story_id, min_score, enabled)
SELECT id, 3, true
FROM stories
WHERE slug = 'fia-2026-sporting-decisions'
ON CONFLICT (story_id) DO UPDATE
SET min_score = EXCLUDED.min_score,
    enabled = EXCLUDED.enabled,
    updated_at = now();

INSERT INTO story_match_terms (story_id, term, weight)
SELECT s.id, term, weight
FROM stories s
CROSS JOIN (
    VALUES
        ('2026 FIA Formula One World Championship', 3),
        ('Formula One World Championship', 2),
        ('Formula 1', 1),
        ('F1 -', 1),
        ('decision', 2),
        ('calendar', 2),
        ('regulation', 2),
        ('regulations', 2),
        ('World Motor Sport Council', 2),
        ('appeal', 2),
        ('hearing', 2),
        ('stewards', 2)
) AS terms(term, weight)
WHERE s.slug = 'fia-2026-sporting-decisions'
ON CONFLICT (story_id, term) DO UPDATE
SET weight = EXCLUDED.weight,
    enabled = true;

INSERT INTO story_identifiers (story_id, identifier_type, value, enabled)
SELECT id, 'fia_ica_case', 'ICA-2026-06-07-08-09', true
FROM stories
WHERE slug = 'fia-2026-sporting-decisions'
ON CONFLICT (story_id, identifier_type, value) DO UPDATE
SET enabled = true;
