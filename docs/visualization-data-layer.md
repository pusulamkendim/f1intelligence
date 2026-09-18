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
- segments — S1/S2/S3 mini-sector strips using OpenF1 segment codes
- timing-tower — position, gap, interval, last lap, tyre compound and tyre age in one dense view
- session-result — OpenF1 session classification for race, sprint, qualifying or practice
- track-map — time-addressable driver tracker using OpenF1 x/y/z locations, team colours, position, gap and lap context
- race-control annotations — flags, Safety Car/VSC, DRS and related messages

## Historical/classic views

- race-result — canonical race classification
- qualifying-result — Q1/Q2/Q3 classification
- driver-standings — round-by-round championship position, points and wins
- constructor-standings — round-by-round constructor position, points and wins
- driver season results — qualifying/grid/finish/points trend by round

These views use canonical Jolpica-backed result and standings tables, so classic result pages remain available even where OpenF1 granular telemetry is unavailable.

OpenF1 mini-sector segments are not available during races. Known codes are surfaced as yellow, green, purple, unavailable and pit-lane semantic tokens; unknown codes are preserved as neutral `segment-unknown` rather than guessed.

## API

Race/session and classification:

`GET /api/v1/visualizations/races/{race_key}/{chart}?session_code=race`

Driver tracker defaults to the latest available frame and accepts an historical timestamp:

`GET /api/v1/visualizations/races/{race_key}/track-map?session_code=race&at={iso_timestamp}`

Season standings:

`GET /api/v1/visualizations/seasons/{season}/{driver-standings|constructor-standings}`

Driver season results:

`GET /api/v1/visualizations/seasons/{season}/drivers/{driver_key}/results`

## Data boundaries

Existing canonical/OpenF1 tables remain the source of truth. The visualization layer stores no duplicate telemetry and does not persist rendered charts.

Raw payloads, ingestion audit rows, aliases, documents and source/story metadata are provenance/content infrastructure and are intentionally not promoted to user-facing chart families.

## Driver tracker semantics

OpenF1 location samples are canonicalized into `session_locations`. Historical ingestion is downsampled to approximately 1 Hz per driver to keep season-scale storage practical while remaining smooth enough for interpolated replay. The upstream location feed is more frequent; a future live transport can use the higher-rate stream without changing this contract.

The map returns provider-native Cartesian coordinates, session bounds and a `reference_path` derived from the fastest valid observed lap. That reference path is explicitly marked as derived driving data, not official circuit geometry. OpenF1 location is suitable for progress around the circuit but not precise left/right placement.

## Known source gaps before full live-timing parity

The current database does not ingest high-frequency OpenF1 `car_data`, so throttle/brake/gear/DRS telemetry traces are intentionally outside this PR.

Official circuit artwork/geometry and photography belong to the media layer; the driver tracker can render from the derived reference path until that asset exists.
