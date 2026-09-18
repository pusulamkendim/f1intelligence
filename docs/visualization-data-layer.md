# Visualization data layer

The visualization API converts canonical F1 data into presentation-ready semantic contracts. Rendering remains a UI concern; the API specifies the meaning, ordering, formatting and F1-specific visual tokens needed to render consistently on web or mobile.

## Classic F1 presentation rules

- Dense, dark timing views are the preferred presentation mode.
- Driver acronym and car number are first-class display fields.
- Team colour comes from the session context and is never permanently assigned to a driver.
- Position axes are reversed so P1 is visually above lower positions.
- Timing status follows the familiar F1 convention: purple = session best, green = personal best, yellow = slower valid time.
- Tyre strategy uses semantic tokens for soft, medium, hard, intermediate and wet compounds.
- Race-control events carry semantic tokens for red/yellow/green/blue/chequered flags, Safety Car, VSC and DRS.
- Timing-table presets specify column order and formatters so the UI does not have to invent F1 display semantics.
- Mixed-unit weather data uses a multi-panel contract rather than placing incompatible units on one y-axis.

## Modern race/session views

- positions — lap-resolved position trace
- lap-times — lap duration with session/personal-best timing status
- stints — tyre compound, stint range and tyre age
- sectors — S1/S2/S3 with purple/green/yellow status
- speeds — I1/I2/speed-trap comparison
- intervals — gap-to-leader and car-to-car interval
- pit-stops — stationary and pit-lane duration
- weather — air/track temperature, humidity, pressure, wind and rainfall
- overtakes — event stream
- starting-grid — position, driver, team and qualifying time
- race-control annotations — flags, Safety Car/VSC, DRS and related messages

## Historical/classic views

- race-result — canonical race classification
- qualifying-result — Q1/Q2/Q3 classification
- driver-standings — round-by-round championship position, points and wins
- constructor-standings — round-by-round constructor position, points and wins
- driver season results — qualifying/grid/finish/points trend by round

These views use canonical Jolpica-backed result and standings tables, so classic result pages remain available even where OpenF1 granular telemetry is unavailable.

## API

Race/session and classification:

`GET /api/v1/visualizations/races/{race_key}/{chart}?session_code=race`

Season standings:

`GET /api/v1/visualizations/seasons/{season}/{driver-standings|constructor-standings}`

Driver season results:

`GET /api/v1/visualizations/seasons/{season}/drivers/{driver_key}/results`

## Data boundaries

Existing canonical/OpenF1 tables remain the source of truth. The visualization layer stores no duplicate telemetry and does not persist rendered charts.

Raw payloads, ingestion audit rows, aliases, documents and source/story metadata are provenance/content infrastructure and are intentionally not promoted to user-facing chart families.
