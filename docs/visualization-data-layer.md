# Visualization data layer

Chart-ready semantic data is derived from existing canonical/OpenF1 tables; rendering remains a UI concern.

Race/session chart families: positions, lap-times, tyre stints/compounds, sector times, intermediate/speed-trap speeds, gap-to-leader and intervals, pit-stop/pit-lane durations, weather (air/track temperature, humidity, pressure, wind, rainfall), overtakes, starting grid, plus race-control annotations.

Driver series retain session-specific team identity and team colour. Existing structured season/career data also supports points and championship-position progression, grid-vs-finish, positions gained, cumulative wins/podiums/poles, DNF trends, average grid/finish and win/podium rates; those belong to season/career coordinates rather than the race endpoint.

Raw payloads, ingestion audit rows, aliases, documents and source/story metadata are provenance/content infrastructure and are intentionally not promoted to user-facing chart families.
