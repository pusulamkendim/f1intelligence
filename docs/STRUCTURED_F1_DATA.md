# Structured F1 data

The application keeps structured race and championship data in PostgreSQL. Public pages read the canonical database; they do not depend on a third-party API being available at render time.

## Source roles

### Jolpica

Jolpica is the baseline structured provider for the season calendar/circuits, race results, qualifying results, driver standings and constructor standings. The importer should use the stable Ergast-compatible endpoints first. Alpha endpoints must not become a production dependency until their contract is stable.

Every Jolpica request must use the configured application User-Agent, respect upstream rate limits, use bounded retries/backoff, and record its source URL and fetch time.

### OpenF1

OpenF1 is an enrichment source for session-level information such as laps, stints, positions, intervals and related timing data. It should be introduced as separate datasets after the baseline Jolpica vertical slice is operational. Failure of OpenF1 enrichment must not remove or invalidate canonical race/results/standings data.

### FIA

FIA remains the authoritative provenance layer for official classifications, steward decisions, penalties, sporting/regulatory decisions and event documents. Structured-provider values should not silently override a contradictory FIA decision. Reconciliation should preserve both the provider value and FIA evidence and surface discrepancies for review.

## Persistence rules

1. Imports are idempotent. Stable provider IDs form natural upsert keys for mutable records.
2. Store `provider`, provider identifiers, `source_url`, `fetched_at` and upstream timestamps when available.
3. Preserve provider payload fragments in `raw_metadata` when they are useful for audit/reprocessing, but expose normalized fields to application reads.
4. Standings are historical snapshots. Never overwrite the only copy of an earlier round's championship state.
5. A standings fetch is content-addressed: normalized rows are hashed. Re-fetching identical standings for the same season/round reuses the existing snapshot; a corrected upstream table creates a new snapshot while retaining the previous one.
6. Each ingestion execution creates a `data_sync_runs` row and records success/failure and record counts.
7. Public reads use the latest successful canonical snapshot for the requested round/season. Provider APIs are not queried from page rendering.

## Baseline Jolpica vertical slice

Implement in this order:

1. season calendar and circuit metadata -> `races`
2. race classifications -> `race_results`
3. qualifying classifications -> `qualifying_results`
4. driver standings -> `driver_standings_snapshots` + `driver_standing_rows`
5. constructor standings -> `constructor_standings_snapshots` + `constructor_standing_rows`

The stable Jolpica endpoints used by this slice are under `/ergast/f1/`, including season/round result, qualifying, driver standings and constructor standings routes. Pagination must be explicit because Jolpica limits result counts.

## Update policy

For the current season, calendar data can be refreshed daily. Results and qualifying should be refreshed after sessions and then periodically for a bounded reconciliation window because classifications can be corrected. Championship standings should be refreshed after points-scoring sessions and retained by round/content hash. Completed historical seasons need only infrequent reconciliation.

Scheduling belongs outside request handling. The ingestion commands should remain independently runnable so the same code can be invoked locally, from CI smoke tests with fixtures, or later from a scheduler/worker.

## Next implementation slice

Add a typed Jolpica client/parser plus fixture-based tests, then a transaction-safe importer for calendar + standings. Only after that importer is exercised against a local PostgreSQL instance should automatic scheduling be enabled.
