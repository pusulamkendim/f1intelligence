-- 2026 registry snapshot verified against official Formula 1 team/driver pages,
-- the Formula 1 team-principal overview dated 2026-08-27, and the FIA 2026
-- calendar amended by the WMSC on 2026-03-26.

-- Teams ---------------------------------------------------------------------
INSERT INTO entities (entity_type, slug, display_name, active_from_season, metadata)
VALUES
    ('team', 'mclaren', 'McLaren', 2026, '{"source":"formula1.com/en/teams"}'::jsonb),
    ('team', 'mercedes', 'Mercedes', 2026, '{"source":"formula1.com/en/teams"}'::jsonb),
    ('team', 'red-bull-racing', 'Red Bull Racing', 2026, '{"source":"formula1.com/en/teams"}'::jsonb),
    ('team', 'ferrari', 'Ferrari', 2026, '{"source":"formula1.com/en/teams"}'::jsonb),
    ('team', 'williams', 'Williams', 2026, '{"source":"formula1.com/en/teams"}'::jsonb),
    ('team', 'racing-bulls', 'Racing Bulls', 2026, '{"source":"formula1.com/en/teams"}'::jsonb),
    ('team', 'aston-martin', 'Aston Martin', 2026, '{"source":"formula1.com/en/teams"}'::jsonb),
    ('team', 'haas', 'Haas F1 Team', 2026, '{"source":"formula1.com/en/teams"}'::jsonb),
    ('team', 'audi', 'Audi', 2026, '{"source":"formula1.com/en/teams"}'::jsonb),
    ('team', 'alpine', 'Alpine', 2026, '{"source":"formula1.com/en/teams"}'::jsonb),
    ('team', 'cadillac', 'Cadillac', 2026, '{"source":"formula1.com/en/teams"}'::jsonb)
ON CONFLICT (entity_type, slug) DO UPDATE
SET display_name = EXCLUDED.display_name,
    active_from_season = EXCLUDED.active_from_season,
    metadata = EXCLUDED.metadata,
    updated_at = now();

INSERT INTO teams (slug, name, active_season, entity_id)
SELECT slug, display_name, 2026, id
FROM entities
WHERE entity_type = 'team' AND active_from_season = 2026
ON CONFLICT (slug) DO UPDATE
SET name = EXCLUDED.name,
    active_season = EXCLUDED.active_season,
    entity_id = EXCLUDED.entity_id,
    updated_at = now();

-- People --------------------------------------------------------------------
INSERT INTO entities (entity_type, slug, display_name, active_from_season, metadata)
VALUES
    ('person', 'george-russell', 'George Russell', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'kimi-antonelli', 'Kimi Antonelli', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'charles-leclerc', 'Charles Leclerc', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'lewis-hamilton', 'Lewis Hamilton', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'lando-norris', 'Lando Norris', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'oscar-piastri', 'Oscar Piastri', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'max-verstappen', 'Max Verstappen', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'isack-hadjar', 'Isack Hadjar', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'liam-lawson', 'Liam Lawson', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'arvid-lindblad', 'Arvid Lindblad', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'pierre-gasly', 'Pierre Gasly', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'franco-colapinto', 'Franco Colapinto', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'esteban-ocon', 'Esteban Ocon', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'oliver-bearman', 'Oliver Bearman', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'nico-hulkenberg', 'Nico Hulkenberg', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'gabriel-bortoleto', 'Gabriel Bortoleto', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'carlos-sainz', 'Carlos Sainz', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'alexander-albon', 'Alexander Albon', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'fernando-alonso', 'Fernando Alonso', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'lance-stroll', 'Lance Stroll', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'sergio-perez', 'Sergio Perez', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'valtteri-bottas', 'Valtteri Bottas', 2026, '{"kind":"driver"}'::jsonb),
    ('person', 'andrea-stella', 'Andrea Stella', 2026, '{"kind":"team_leadership"}'::jsonb),
    ('person', 'toto-wolff', 'Toto Wolff', 2026, '{"kind":"team_leadership"}'::jsonb),
    ('person', 'laurent-mekies', 'Laurent Mekies', 2026, '{"kind":"team_leadership"}'::jsonb),
    ('person', 'frederic-vasseur', 'Frederic Vasseur', 2026, '{"kind":"team_leadership"}'::jsonb),
    ('person', 'james-vowles', 'James Vowles', 2026, '{"kind":"team_leadership"}'::jsonb),
    ('person', 'alan-permane', 'Alan Permane', 2026, '{"kind":"team_leadership"}'::jsonb),
    ('person', 'adrian-newey', 'Adrian Newey', 2026, '{"kind":"team_leadership"}'::jsonb),
    ('person', 'ayao-komatsu', 'Ayao Komatsu', 2026, '{"kind":"team_leadership"}'::jsonb),
    ('person', 'mattia-binotto', 'Mattia Binotto', 2026, '{"kind":"team_leadership"}'::jsonb),
    ('person', 'allan-mcnish', 'Allan McNish', 2026, '{"kind":"team_leadership"}'::jsonb),
    ('person', 'steve-nielsen', 'Steve Nielsen', 2026, '{"kind":"team_leadership"}'::jsonb),
    ('person', 'flavio-briatore', 'Flavio Briatore', 2026, '{"kind":"team_leadership"}'::jsonb),
    ('person', 'marcin-budkowski', 'Marcin Budkowski', 2026, '{"kind":"team_leadership"}'::jsonb)
ON CONFLICT (entity_type, slug) DO UPDATE
SET display_name = EXCLUDED.display_name,
    active_from_season = EXCLUDED.active_from_season,
    metadata = EXCLUDED.metadata,
    updated_at = now();

INSERT INTO persons (entity_id, slug, display_name, nationality_code)
SELECT e.id, e.slug, e.display_name, seed.nationality_code
FROM entities e
JOIN (
    VALUES
        ('george-russell', 'GBR'), ('kimi-antonelli', 'ITA'), ('charles-leclerc', 'MON'),
        ('lewis-hamilton', 'GBR'), ('lando-norris', 'GBR'), ('oscar-piastri', 'AUS'),
        ('max-verstappen', 'NED'), ('isack-hadjar', 'FRA'), ('liam-lawson', 'NZL'),
        ('arvid-lindblad', 'GBR'), ('pierre-gasly', 'FRA'), ('franco-colapinto', 'ARG'),
        ('esteban-ocon', 'FRA'), ('oliver-bearman', 'GBR'), ('nico-hulkenberg', 'GER'),
        ('gabriel-bortoleto', 'BRA'), ('carlos-sainz', 'ESP'), ('alexander-albon', 'THA'),
        ('fernando-alonso', 'ESP'), ('lance-stroll', 'CAN'), ('sergio-perez', 'MEX'),
        ('valtteri-bottas', 'FIN'), ('andrea-stella', 'ITA'), ('toto-wolff', 'AUT'),
        ('laurent-mekies', 'FRA'), ('frederic-vasseur', 'FRA'), ('james-vowles', 'GBR'),
        ('alan-permane', 'GBR'), ('adrian-newey', 'GBR'), ('ayao-komatsu', 'JPN'),
        ('mattia-binotto', 'ITA'), ('allan-mcnish', 'GBR'), ('steve-nielsen', 'GBR'),
        ('flavio-briatore', 'ITA'), ('marcin-budkowski', 'POL')
) AS seed(slug, nationality_code) ON seed.slug = e.slug
WHERE e.entity_type = 'person'
ON CONFLICT (slug) DO UPDATE
SET entity_id = EXCLUDED.entity_id,
    display_name = EXCLUDED.display_name,
    nationality_code = EXCLUDED.nationality_code,
    updated_at = now();

-- Canonical aliases for every seeded team/person.
INSERT INTO entity_aliases (entity_id, alias, alias_type, confidence, valid_from_season)
SELECT id, display_name, 'canonical', 100, 2026
FROM entities
WHERE entity_type IN ('team', 'person') AND active_from_season = 2026
ON CONFLICT (entity_id, alias) DO UPDATE
SET confidence = EXCLUDED.confidence,
    enabled = true,
    updated_at = now();

-- Common team names and abbreviations.
INSERT INTO entity_aliases (entity_id, alias, alias_type, confidence, valid_from_season)
SELECT e.id, seed.alias, seed.alias_type, seed.confidence, 2026
FROM entities e
JOIN (
    VALUES
        ('mclaren', 'McLaren F1', 'common', 95),
        ('mclaren', 'McLaren Racing', 'common', 95),
        ('mercedes', 'Mercedes-AMG', 'common', 95),
        ('mercedes', 'Mercedes AMG Petronas', 'common', 95),
        ('red-bull-racing', 'Red Bull', 'common', 95),
        ('red-bull-racing', 'Oracle Red Bull Racing', 'common', 98),
        ('red-bull-racing', 'RBR', 'acronym', 90),
        ('ferrari', 'Scuderia Ferrari', 'common', 98),
        ('williams', 'Williams Racing', 'common', 98),
        ('racing-bulls', 'Visa Cash App Racing Bulls', 'common', 98),
        ('racing-bulls', 'VCARB', 'acronym', 88),
        ('aston-martin', 'Aston Martin F1', 'common', 95),
        ('haas', 'Haas', 'common', 95),
        ('audi', 'Audi F1', 'common', 95),
        ('audi', 'Audi F1 Team', 'common', 98),
        ('alpine', 'Alpine F1', 'common', 95),
        ('cadillac', 'Cadillac F1', 'common', 95),
        ('cadillac', 'Cadillac F1 Team', 'common', 98)
) AS seed(slug, alias, alias_type, confidence) ON seed.slug = e.slug
WHERE e.entity_type = 'team'
ON CONFLICT (entity_id, alias) DO UPDATE
SET alias_type = EXCLUDED.alias_type,
    confidence = EXCLUDED.confidence,
    enabled = true,
    updated_at = now();

-- Driver surnames and official three-letter timing codes.
INSERT INTO entity_aliases (entity_id, alias, alias_type, confidence, valid_from_season, valid_to_season)
SELECT e.id, seed.alias, seed.alias_type, seed.confidence, 2026, 2026
FROM entities e
JOIN (
    VALUES
        ('george-russell', 'Russell', 'surname', 92), ('george-russell', 'RUS', 'driver_code', 86),
        ('kimi-antonelli', 'Antonelli', 'surname', 92), ('kimi-antonelli', 'ANT', 'driver_code', 86),
        ('charles-leclerc', 'Leclerc', 'surname', 92), ('charles-leclerc', 'LEC', 'driver_code', 86),
        ('lewis-hamilton', 'Hamilton', 'surname', 92), ('lewis-hamilton', 'HAM', 'driver_code', 86),
        ('lando-norris', 'Norris', 'surname', 92), ('lando-norris', 'NOR', 'driver_code', 86),
        ('oscar-piastri', 'Piastri', 'surname', 92), ('oscar-piastri', 'PIA', 'driver_code', 86),
        ('max-verstappen', 'Verstappen', 'surname', 92), ('max-verstappen', 'VER', 'driver_code', 86),
        ('isack-hadjar', 'Hadjar', 'surname', 92), ('isack-hadjar', 'HAD', 'driver_code', 86),
        ('liam-lawson', 'Lawson', 'surname', 92), ('liam-lawson', 'LAW', 'driver_code', 86),
        ('arvid-lindblad', 'Lindblad', 'surname', 92), ('arvid-lindblad', 'LIN', 'driver_code', 86),
        ('pierre-gasly', 'Gasly', 'surname', 92), ('pierre-gasly', 'GAS', 'driver_code', 86),
        ('franco-colapinto', 'Colapinto', 'surname', 92), ('franco-colapinto', 'COL', 'driver_code', 86),
        ('esteban-ocon', 'Ocon', 'surname', 92), ('esteban-ocon', 'OCO', 'driver_code', 86),
        ('oliver-bearman', 'Bearman', 'surname', 92), ('oliver-bearman', 'BEA', 'driver_code', 86),
        ('nico-hulkenberg', 'Hulkenberg', 'surname', 92), ('nico-hulkenberg', 'Hülkenberg', 'surname', 92),
        ('nico-hulkenberg', 'HUL', 'driver_code', 86),
        ('gabriel-bortoleto', 'Bortoleto', 'surname', 92), ('gabriel-bortoleto', 'BOR', 'driver_code', 86),
        ('carlos-sainz', 'Sainz', 'surname', 92), ('carlos-sainz', 'SAI', 'driver_code', 86),
        ('alexander-albon', 'Albon', 'surname', 92), ('alexander-albon', 'Alex Albon', 'common', 96),
        ('alexander-albon', 'ALB', 'driver_code', 86),
        ('fernando-alonso', 'Alonso', 'surname', 92), ('fernando-alonso', 'ALO', 'driver_code', 86),
        ('lance-stroll', 'Stroll', 'surname', 92), ('lance-stroll', 'STR', 'driver_code', 86),
        ('sergio-perez', 'Perez', 'surname', 92), ('sergio-perez', 'Pérez', 'surname', 92),
        ('sergio-perez', 'PER', 'driver_code', 86),
        ('valtteri-bottas', 'Bottas', 'surname', 92), ('valtteri-bottas', 'BOT', 'driver_code', 86)
) AS seed(slug, alias, alias_type, confidence) ON seed.slug = e.slug
WHERE e.entity_type = 'person'
ON CONFLICT (entity_id, alias) DO UPDATE
SET alias_type = EXCLUDED.alias_type,
    confidence = EXCLUDED.confidence,
    enabled = true,
    updated_at = now();

-- Leadership surnames are useful high-signal editorial aliases.
INSERT INTO entity_aliases (entity_id, alias, alias_type, confidence, valid_from_season, valid_to_season)
SELECT e.id, seed.alias, 'surname', 90, 2026, 2026
FROM entities e
JOIN (
    VALUES
        ('andrea-stella', 'Stella'), ('toto-wolff', 'Wolff'), ('laurent-mekies', 'Mekies'),
        ('frederic-vasseur', 'Vasseur'), ('james-vowles', 'Vowles'), ('alan-permane', 'Permane'),
        ('adrian-newey', 'Newey'), ('ayao-komatsu', 'Komatsu'), ('mattia-binotto', 'Binotto'),
        ('allan-mcnish', 'McNish'), ('steve-nielsen', 'Nielsen'), ('flavio-briatore', 'Briatore'),
        ('marcin-budkowski', 'Budkowski')
) AS seed(slug, alias) ON seed.slug = e.slug
WHERE e.entity_type = 'person'
ON CONFLICT (entity_id, alias) DO UPDATE
SET confidence = EXCLUDED.confidence,
    enabled = true,
    updated_at = now();

-- Current 2026 driver-team relationships.
INSERT INTO team_person_roles (team_id, person_id, role, season, source_url)
SELECT t.id, p.id, 'driver', 2026, 'https://www.formula1.com/en/drivers'
FROM teams t
JOIN (
    VALUES
        ('mercedes', 'george-russell'), ('mercedes', 'kimi-antonelli'),
        ('ferrari', 'charles-leclerc'), ('ferrari', 'lewis-hamilton'),
        ('mclaren', 'lando-norris'), ('mclaren', 'oscar-piastri'),
        ('red-bull-racing', 'max-verstappen'), ('red-bull-racing', 'isack-hadjar'),
        ('racing-bulls', 'liam-lawson'), ('racing-bulls', 'arvid-lindblad'),
        ('alpine', 'pierre-gasly'), ('alpine', 'franco-colapinto'),
        ('haas', 'esteban-ocon'), ('haas', 'oliver-bearman'),
        ('audi', 'nico-hulkenberg'), ('audi', 'gabriel-bortoleto'),
        ('williams', 'carlos-sainz'), ('williams', 'alexander-albon'),
        ('aston-martin', 'fernando-alonso'), ('aston-martin', 'lance-stroll'),
        ('cadillac', 'sergio-perez'), ('cadillac', 'valtteri-bottas')
) AS roster(team_slug, person_slug) ON roster.team_slug = t.slug
JOIN persons p ON p.slug = roster.person_slug
ON CONFLICT (team_id, person_id, role, season) DO UPDATE
SET source_url = EXCLUDED.source_url,
    updated_at = now();

-- Current team leadership snapshot. Audi and Alpine use split leadership roles.
INSERT INTO team_person_roles (team_id, person_id, role, season, source_url)
SELECT t.id, p.id, leadership.role, 2026,
       'https://www.formula1.com/en/latest/article/who-are-the-2026-team-principals.2Jrw5LEJbEoX2gM5OtFL8K.2Jrw5LEJbEoX2gM5OtFL8K'
FROM teams t
JOIN (
    VALUES
        ('mclaren', 'andrea-stella', 'team_principal'),
        ('mercedes', 'toto-wolff', 'team_principal'),
        ('red-bull-racing', 'laurent-mekies', 'team_principal'),
        ('ferrari', 'frederic-vasseur', 'team_principal'),
        ('williams', 'james-vowles', 'team_principal'),
        ('racing-bulls', 'alan-permane', 'team_principal'),
        ('aston-martin', 'adrian-newey', 'team_principal'),
        ('haas', 'ayao-komatsu', 'team_principal'),
        ('audi', 'mattia-binotto', 'team_principal'),
        ('audi', 'allan-mcnish', 'racing_director'),
        ('alpine', 'steve-nielsen', 'managing_director'),
        ('alpine', 'flavio-briatore', 'executive_advisor'),
        ('cadillac', 'marcin-budkowski', 'team_principal')
) AS leadership(team_slug, person_slug, role) ON leadership.team_slug = t.slug
JOIN persons p ON p.slug = leadership.person_slug
ON CONFLICT (team_id, person_id, role, season) DO UPDATE
SET source_url = EXCLUDED.source_url,
    updated_at = now();

-- Races ---------------------------------------------------------------------
INSERT INTO entities (entity_type, slug, display_name, active_from_season, active_to_season, metadata)
VALUES
    ('race', '2026-australian-grand-prix', '2026 Australian Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-chinese-grand-prix', '2026 Chinese Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-japanese-grand-prix', '2026 Japanese Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-miami-grand-prix', '2026 Miami Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-canadian-grand-prix', '2026 Canadian Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-monaco-grand-prix', '2026 Monaco Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-barcelona-catalunya-grand-prix', '2026 Barcelona-Catalunya Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-austrian-grand-prix', '2026 Austrian Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-british-grand-prix', '2026 British Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-belgian-grand-prix', '2026 Belgian Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-hungarian-grand-prix', '2026 Hungarian Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-dutch-grand-prix', '2026 Dutch Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-italian-grand-prix', '2026 Italian Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-madrid-grand-prix', '2026 Madrid Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-azerbaijan-grand-prix', '2026 Azerbaijan Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-singapore-grand-prix', '2026 Singapore Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-united-states-grand-prix', '2026 United States Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-mexico-grand-prix', '2026 Mexico Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-sao-paulo-grand-prix', '2026 Sao Paulo Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-las-vegas-grand-prix', '2026 Las Vegas Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-qatar-grand-prix', '2026 Qatar Grand Prix', 2026, 2026, '{}'::jsonb),
    ('race', '2026-abu-dhabi-grand-prix', '2026 Abu Dhabi Grand Prix', 2026, 2026, '{}'::jsonb)
ON CONFLICT (entity_type, slug) DO UPDATE
SET display_name = EXCLUDED.display_name,
    active_from_season = EXCLUDED.active_from_season,
    active_to_season = EXCLUDED.active_to_season,
    updated_at = now();

INSERT INTO races (
    season, round, slug, official_name, circuit, country,
    weekend_start_date, weekend_end_date, status, entity_id
)
SELECT 2026, seed.round, seed.slug, seed.official_name, seed.circuit, seed.country,
       seed.start_date::date, seed.end_date::date,
       CASE WHEN seed.end_date::date < DATE '2026-09-17' THEN 'completed' ELSE 'upcoming' END,
       e.id
FROM (
    VALUES
        (1, '2026-australian-grand-prix', 'Grand Prix of Australia', 'Melbourne', 'Australia', '2026-03-06', '2026-03-08'),
        (2, '2026-chinese-grand-prix', 'Grand Prix of China', 'Shanghai', 'China', '2026-03-13', '2026-03-15'),
        (3, '2026-japanese-grand-prix', 'Grand Prix of Japan', 'Suzuka', 'Japan', '2026-03-27', '2026-03-29'),
        (4, '2026-miami-grand-prix', 'Grand Prix of Miami', 'Miami', 'United States', '2026-05-01', '2026-05-03'),
        (5, '2026-canadian-grand-prix', 'Grand Prix of Canada', 'Montreal', 'Canada', '2026-05-22', '2026-05-24'),
        (6, '2026-monaco-grand-prix', 'Grand Prix of Monaco', 'Monaco', 'Monaco', '2026-06-05', '2026-06-07'),
        (7, '2026-barcelona-catalunya-grand-prix', 'Grand Prix of Barcelona-Catalunya', 'Barcelona-Catalunya', 'Spain', '2026-06-12', '2026-06-14'),
        (8, '2026-austrian-grand-prix', 'Grand Prix of Austria', 'Spielberg', 'Austria', '2026-06-26', '2026-06-28'),
        (9, '2026-british-grand-prix', 'Grand Prix of United Kingdom', 'Silverstone', 'United Kingdom', '2026-07-03', '2026-07-05'),
        (10, '2026-belgian-grand-prix', 'Grand Prix of Belgium', 'Spa-Francorchamps', 'Belgium', '2026-07-17', '2026-07-19'),
        (11, '2026-hungarian-grand-prix', 'Grand Prix of Hungary', 'Budapest', 'Hungary', '2026-07-24', '2026-07-26'),
        (12, '2026-dutch-grand-prix', 'Grand Prix of Netherlands', 'Zandvoort', 'Netherlands', '2026-08-21', '2026-08-23'),
        (13, '2026-italian-grand-prix', 'Grand Prix of Italy', 'Monza', 'Italy', '2026-09-04', '2026-09-06'),
        (14, '2026-madrid-grand-prix', 'Grand Prix of Madrid', 'Madrid', 'Spain', '2026-09-11', '2026-09-13'),
        (15, '2026-azerbaijan-grand-prix', 'Grand Prix of Azerbaijan', 'Baku', 'Azerbaijan', '2026-09-24', '2026-09-26'),
        (16, '2026-singapore-grand-prix', 'Grand Prix of Singapore', 'Singapore', 'Singapore', '2026-10-09', '2026-10-11'),
        (17, '2026-united-states-grand-prix', 'Grand Prix of the USA (Austin)', 'Austin', 'United States', '2026-10-23', '2026-10-25'),
        (18, '2026-mexico-grand-prix', 'Grand Prix of Mexico', 'Mexico City', 'Mexico', '2026-10-30', '2026-11-01'),
        (19, '2026-sao-paulo-grand-prix', 'Grand Prix of Brazil', 'Sao Paulo', 'Brazil', '2026-11-06', '2026-11-08'),
        (20, '2026-las-vegas-grand-prix', 'Grand Prix of Las Vegas', 'Las Vegas', 'United States', '2026-11-19', '2026-11-21'),
        (21, '2026-qatar-grand-prix', 'Grand Prix of Qatar', 'Lusail', 'Qatar', '2026-11-27', '2026-11-29'),
        (22, '2026-abu-dhabi-grand-prix', 'Grand Prix of Abu Dhabi', 'Yas Marina', 'United Arab Emirates', '2026-12-04', '2026-12-06')
) AS seed(round, slug, official_name, circuit, country, start_date, end_date)
JOIN entities e ON e.entity_type = 'race' AND e.slug = seed.slug
ON CONFLICT (season, slug) DO UPDATE
SET round = EXCLUDED.round,
    official_name = EXCLUDED.official_name,
    circuit = EXCLUDED.circuit,
    country = EXCLUDED.country,
    weekend_start_date = EXCLUDED.weekend_start_date,
    weekend_end_date = EXCLUDED.weekend_end_date,
    status = EXCLUDED.status,
    entity_id = EXCLUDED.entity_id,
    updated_at = now();

INSERT INTO entity_aliases (entity_id, alias, alias_type, confidence, valid_from_season, valid_to_season)
SELECT id, display_name, 'canonical', 100, 2026, 2026
FROM entities
WHERE entity_type = 'race' AND active_from_season = 2026
ON CONFLICT (entity_id, alias) DO UPDATE
SET confidence = EXCLUDED.confidence,
    enabled = true,
    updated_at = now();

INSERT INTO entity_aliases (entity_id, alias, alias_type, confidence, valid_from_season, valid_to_season)
SELECT e.id, seed.alias, seed.alias_type, seed.confidence, 2026, 2026
FROM entities e
JOIN (
    VALUES
        ('2026-australian-grand-prix', 'Australian Grand Prix', 'race_name', 98),
        ('2026-australian-grand-prix', 'Australian GP', 'race_name', 96),
        ('2026-australian-grand-prix', 'Melbourne', 'venue', 78),
        ('2026-chinese-grand-prix', 'Chinese Grand Prix', 'race_name', 98),
        ('2026-chinese-grand-prix', 'Chinese GP', 'race_name', 96),
        ('2026-chinese-grand-prix', 'Shanghai', 'venue', 78),
        ('2026-japanese-grand-prix', 'Japanese Grand Prix', 'race_name', 98),
        ('2026-japanese-grand-prix', 'Japanese GP', 'race_name', 96),
        ('2026-japanese-grand-prix', 'Suzuka', 'venue', 82),
        ('2026-miami-grand-prix', 'Miami Grand Prix', 'race_name', 98),
        ('2026-miami-grand-prix', 'Miami GP', 'race_name', 96),
        ('2026-canadian-grand-prix', 'Canadian Grand Prix', 'race_name', 98),
        ('2026-canadian-grand-prix', 'Canadian GP', 'race_name', 96),
        ('2026-canadian-grand-prix', 'Montreal', 'venue', 78),
        ('2026-monaco-grand-prix', 'Monaco Grand Prix', 'race_name', 98),
        ('2026-monaco-grand-prix', 'Monaco GP', 'race_name', 96),
        ('2026-barcelona-catalunya-grand-prix', 'Barcelona-Catalunya Grand Prix', 'race_name', 98),
        ('2026-barcelona-catalunya-grand-prix', 'Barcelona GP', 'race_name', 93),
        ('2026-barcelona-catalunya-grand-prix', 'Circuit de Barcelona-Catalunya', 'venue', 85),
        ('2026-austrian-grand-prix', 'Austrian Grand Prix', 'race_name', 98),
        ('2026-austrian-grand-prix', 'Austrian GP', 'race_name', 96),
        ('2026-austrian-grand-prix', 'Spielberg', 'venue', 82),
        ('2026-british-grand-prix', 'British Grand Prix', 'race_name', 98),
        ('2026-british-grand-prix', 'British GP', 'race_name', 96),
        ('2026-british-grand-prix', 'Silverstone', 'venue', 85),
        ('2026-belgian-grand-prix', 'Belgian Grand Prix', 'race_name', 98),
        ('2026-belgian-grand-prix', 'Belgian GP', 'race_name', 96),
        ('2026-belgian-grand-prix', 'Spa-Francorchamps', 'venue', 85),
        ('2026-hungarian-grand-prix', 'Hungarian Grand Prix', 'race_name', 98),
        ('2026-hungarian-grand-prix', 'Hungarian GP', 'race_name', 96),
        ('2026-hungarian-grand-prix', 'Hungaroring', 'venue', 85),
        ('2026-dutch-grand-prix', 'Dutch Grand Prix', 'race_name', 98),
        ('2026-dutch-grand-prix', 'Dutch GP', 'race_name', 96),
        ('2026-dutch-grand-prix', 'Zandvoort', 'venue', 85),
        ('2026-italian-grand-prix', 'Italian Grand Prix', 'race_name', 98),
        ('2026-italian-grand-prix', 'Italian GP', 'race_name', 96),
        ('2026-italian-grand-prix', 'Monza', 'venue', 85),
        ('2026-madrid-grand-prix', 'Madrid Grand Prix', 'race_name', 98),
        ('2026-madrid-grand-prix', 'Madrid GP', 'race_name', 96),
        ('2026-madrid-grand-prix', 'Madring', 'venue', 85),
        ('2026-azerbaijan-grand-prix', 'Azerbaijan Grand Prix', 'race_name', 98),
        ('2026-azerbaijan-grand-prix', 'Azerbaijan GP', 'race_name', 96),
        ('2026-azerbaijan-grand-prix', 'Baku', 'venue', 85),
        ('2026-singapore-grand-prix', 'Singapore Grand Prix', 'race_name', 98),
        ('2026-singapore-grand-prix', 'Singapore GP', 'race_name', 96),
        ('2026-united-states-grand-prix', 'United States Grand Prix', 'race_name', 98),
        ('2026-united-states-grand-prix', 'United States GP', 'race_name', 96),
        ('2026-united-states-grand-prix', 'Austin Grand Prix', 'race_name', 96),
        ('2026-united-states-grand-prix', 'Austin GP', 'race_name', 94),
        ('2026-mexico-grand-prix', 'Mexico Grand Prix', 'race_name', 98),
        ('2026-mexico-grand-prix', 'Mexico GP', 'race_name', 96),
        ('2026-mexico-grand-prix', 'Mexico City Grand Prix', 'race_name', 96),
        ('2026-sao-paulo-grand-prix', 'Sao Paulo Grand Prix', 'race_name', 98),
        ('2026-sao-paulo-grand-prix', 'São Paulo Grand Prix', 'race_name', 98),
        ('2026-sao-paulo-grand-prix', 'Brazilian Grand Prix', 'race_name', 94),
        ('2026-sao-paulo-grand-prix', 'Brazilian GP', 'race_name', 92),
        ('2026-las-vegas-grand-prix', 'Las Vegas Grand Prix', 'race_name', 98),
        ('2026-las-vegas-grand-prix', 'Las Vegas GP', 'race_name', 96),
        ('2026-qatar-grand-prix', 'Qatar Grand Prix', 'race_name', 98),
        ('2026-qatar-grand-prix', 'Qatar GP', 'race_name', 96),
        ('2026-qatar-grand-prix', 'Lusail', 'venue', 82),
        ('2026-abu-dhabi-grand-prix', 'Abu Dhabi Grand Prix', 'race_name', 98),
        ('2026-abu-dhabi-grand-prix', 'Abu Dhabi GP', 'race_name', 96),
        ('2026-abu-dhabi-grand-prix', 'Yas Marina', 'venue', 85)
) AS seed(slug, alias, alias_type, confidence) ON seed.slug = e.slug
WHERE e.entity_type = 'race'
ON CONFLICT (entity_id, alias) DO UPDATE
SET alias_type = EXCLUDED.alias_type,
    confidence = EXCLUDED.confidence,
    enabled = true,
    updated_at = now();
