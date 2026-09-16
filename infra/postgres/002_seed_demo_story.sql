INSERT INTO stories (
    slug,
    title,
    summary,
    status,
    significance,
    confidence,
    what_changed,
    why_it_matters,
    what_to_watch_next,
    created_at,
    updated_at
)
VALUES (
    'demo-rear-stability',
    'Demo: Rear-stability development',
    'Synthetic editorial fixture used to validate the Story Page, API contract and evidence timeline. It does not describe a real Formula 1 event.',
    'developing',
    60,
    'strong',
    'A synthetic setup change and a later long-run observation changed the working interpretation.',
    'The fixture proves that one persistent story can separate documented change, source claim, observation and editorial analysis on a single timeline.',
    'Add a real ingestion source, then replace this fixture with verified race-weekend evidence.',
    '2026-09-16T12:00:00Z',
    '2026-09-16T18:00:00Z'
)
ON CONFLICT (slug) DO UPDATE SET
    title = EXCLUDED.title,
    summary = EXCLUDED.summary,
    status = EXCLUDED.status,
    significance = EXCLUDED.significance,
    confidence = EXCLUDED.confidence,
    what_changed = EXCLUDED.what_changed,
    why_it_matters = EXCLUDED.why_it_matters,
    what_to_watch_next = EXCLUDED.what_to_watch_next,
    updated_at = EXCLUDED.updated_at;

DELETE FROM evidence
WHERE story_id = (SELECT id FROM stories WHERE slug = 'demo-rear-stability');

INSERT INTO evidence (
    story_id,
    source_type,
    source_name,
    published_at,
    captured_at,
    normalized_claim,
    raw_excerpt_or_reference,
    reliability_class,
    directness,
    raw_metadata
)
SELECT
    id,
    'demo_fixture',
    'Synthetic fixture — documented change',
    '2026-09-16T13:15:00Z',
    '2026-09-16T13:16:00Z',
    'A synthetic floor-edge change was recorded for the demo car.',
    'Fixture only. No real-world technical claim is being made.',
    'fixture',
    'direct',
    '{"presentation_type":"documented_change","event":"Demo GP","session":"FP1","is_synthetic":true}'::jsonb
FROM stories
WHERE slug = 'demo-rear-stability';

INSERT INTO evidence (
    story_id,
    source_type,
    source_name,
    published_at,
    captured_at,
    author_or_speaker,
    normalized_claim,
    raw_excerpt_or_reference,
    reliability_class,
    directness,
    raw_metadata
)
SELECT
    id,
    'demo_fixture',
    'Synthetic fixture — source claim',
    '2026-09-16T14:05:00Z',
    '2026-09-16T14:06:00Z',
    'Demo driver',
    'The demo driver reported improved corner-entry confidence.',
    'Fixture only. No real driver said this.',
    'fixture',
    'attributed_claim',
    '{"presentation_type":"source_claim","event":"Demo GP","session":"FP1","is_synthetic":true}'::jsonb
FROM stories
WHERE slug = 'demo-rear-stability';

INSERT INTO evidence (
    story_id,
    source_type,
    source_name,
    published_at,
    captured_at,
    normalized_claim,
    raw_excerpt_or_reference,
    reliability_class,
    directness,
    raw_metadata
)
SELECT
    id,
    'demo_fixture',
    'Synthetic fixture — session observation',
    '2026-09-16T15:30:00Z',
    '2026-09-16T15:31:00Z',
    'The demo long run showed a more stable balance while tyre-life uncertainty remained.',
    'Fixture only. No real session data is represented.',
    'fixture',
    'observation',
    '{"presentation_type":"observation","event":"Demo GP","session":"FP2","is_synthetic":true}'::jsonb
FROM stories
WHERE slug = 'demo-rear-stability';

INSERT INTO evidence (
    story_id,
    source_type,
    source_name,
    published_at,
    captured_at,
    normalized_claim,
    raw_excerpt_or_reference,
    reliability_class,
    directness,
    raw_metadata
)
SELECT
    id,
    'internal_analysis',
    'F1 Intelligence demo analysis',
    '2026-09-16T17:00:00Z',
    '2026-09-16T17:00:00Z',
    'The synthetic evidence is consistent with an improved entry balance, but not enough to conclude that overall race performance improved.',
    'Editorial demo interpretation built from synthetic fixture evidence.',
    'fixture',
    'interpretation',
    '{"presentation_type":"analysis","event":"Demo GP","session":"FP2","is_synthetic":true}'::jsonb
FROM stories
WHERE slug = 'demo-rear-stability';
