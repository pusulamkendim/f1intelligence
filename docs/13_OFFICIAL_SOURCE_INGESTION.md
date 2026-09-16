# Official Source Ingestion

## Purpose

This document defines the first real-source ingestion vertical slice for F1 Intelligence. The initial provider is the FIA's official press-release RSS feed.

The goal is not to reproduce source content. The goal is to discover a new official item, determine whether it materially belongs to an existing Story, persist a minimal evidence record, and expose the original source link in the Story evidence timeline.

```text
FIA official RSS
  -> parse source metadata
  -> deduplicate
  -> deterministic Story matching
  -> Evidence
  -> Story API
  -> Story Page
```

## Source policy

The first source is:

```text
Provider: FIA
Feed: https://www.fia.com/rss/press-release
Type: official_feed
```

Stored fields are deliberately narrow:

- source headline,
- canonical source URL,
- publication timestamp,
- feed categories when present,
- external feed identifier,
- matching metadata.

The ingestion service does not copy or republish FIA article bodies. The public evidence card links directly to the original source.

## Persistence model

### `ingestion_sources`

Tracks provider/feed configuration and the last successful check time.

### `story_ingestion_rules`

Enables automated matching for a Story and sets its minimum weighted match score.

### `story_match_terms`

Stores deterministic terms and their weights. Matching is explainable and editable without changing application code.

### `ingestion_items`

Provides the ingestion audit trail and deduplication boundary.

An item can have one of these MVP states:

- `attached`: a single Story exceeded its threshold and Evidence was created,
- `unmatched`: no configured Story exceeded its threshold,
- `ambiguous`: multiple Stories tied for the highest eligible score.

Unmatched and ambiguous items are retained rather than discarded so a future editorial review queue can revisit them.

## Matching rule

For the MVP, matching is intentionally deterministic rather than LLM-driven.

The matcher builds searchable text from the RSS item title and categories. Each configured Story term that appears contributes its weight. A Story becomes eligible when the sum reaches its configured `min_score`.

```text
score(story, item) = sum(weight of each matching enabled term)
```

The highest eligible Story wins. Equal top scores do not auto-attach; the item becomes `ambiguous`.

This rule prevents a broad token such as `F1` from being sufficient by itself.

## Pilot Story

The bootstrap rule creates:

```text
slug: fia-2026-sporting-decisions
```

It is a deliberately broad pilot Story for official sporting, governance, calendar and regulatory developments. Its purpose is to validate ingestion mechanics before narrower production Story rules are configured.

High-weight phrases include the 2026 FIA Formula One World Championship name plus decision/calendar/regulation terms. A generic press-conference transcript containing only `F1` should remain below threshold.

## Evidence contract

When a source item attaches, the ingestion service creates an `evidence` row with:

```text
source_type: official_feed
source_name: FIA
source_url: original FIA URL
normalized_claim: RSS headline
reliability_class: official_primary
directness: direct
presentation_type: source_claim
```

The reference note explicitly states that article content is not mirrored.

The existing Story Page already renders `source_url` as an external link, so ingestion evidence becomes visible without a separate publication step.

## Deduplication

The stable boundary is:

```text
UNIQUE(source_id, external_id)
```

The feed `guid` is preferred. The canonical link is the second fallback. If neither exists, the parser derives a SHA-256 identifier from stable item metadata.

Repeated runs therefore do not create duplicate Evidence rows.

## Running locally

For an existing database volume:

```bash
make ingestion-setup
```

Then ingest the latest feed items:

```bash
make ingest-fia
```

The command prints counters for fetched, attached, unmatched, ambiguous and duplicate items.

The pilot Story is available at:

```text
/stories/fia-2026-sporting-decisions
```

## Failure behaviour

- Network or non-success HTTP response: fail the run; do not mark the source check as successful.
- Invalid RSS XML: fail the run rather than accepting partial malformed data.
- Missing title: skip the malformed feed item during parsing.
- Duplicate external ID: count as duplicate and do not create Evidence.
- No Story above threshold: retain as `unmatched`.
- Equal best Story score: retain as `ambiguous`.
- Database error: roll back the ingestion transaction.

## Security and operational constraints

- No unauthenticated public ingestion endpoint is exposed.
- Ingestion is currently invoked as a CLI/Make target.
- The HTTP client uses a project User-Agent.
- Source URLs are displayed as external links; source HTML is not rendered inside the product.
- Matching rules are data, not hard-coded editorial conclusions.

## MVP acceptance criteria

The vertical slice is complete when:

1. `make ingest-fia` can retrieve the official FIA RSS feed.
2. A feed item is recorded only once across repeated runs.
3. A specific configured item can cross a weighted Story threshold.
4. Generic low-signal F1 items remain unmatched when below threshold.
5. Ambiguous equal-score items are not silently assigned.
6. Attached items create a Story Evidence record with the FIA source URL.
7. The existing Story API returns that Evidence.
8. The Story Page renders the evidence item and direct source link.
9. Parser and matcher behaviour is covered by automated tests.

## Next steps

The next production increments are:

1. add an editorial queue for `unmatched` and `ambiguous` items,
2. create narrower Story-specific rule management instead of relying on the broad pilot Story,
3. add source adapters for other permitted official feeds/documents,
4. add scheduled execution with observability and alerts,
5. connect approved MediaAssets to evidence and Story presentation.
