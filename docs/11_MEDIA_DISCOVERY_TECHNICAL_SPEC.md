# Media Discovery Technical Specification

## Purpose

This document turns `10_MEDIA_ASSET_AND_IMAGE_PIPELINE.md` into an implementation-ready MVP for automated image candidate discovery, rights metadata extraction, candidate ranking and editor approval.

The first provider is **Wikimedia Commons**. The architecture must remain provider-agnostic so photographer feeds, agencies and paid stock providers can be added without changing the editorial workflow.

The core rule is:

> Discovery may be automated. Publication may not bypass rights validation.

A search result is a `MediaCandidate`, not a publishable `MediaAsset`.

---

# 1. MVP scope

## In scope

- generate image-search intents from Story/Race/Team/Article context,
- search Wikimedia Commons,
- fetch file metadata and thumbnails,
- normalize licence/creator/source metadata,
- apply an explicit licence allowlist,
- flag ambiguous metadata for manual review,
- rank eligible candidates,
- show 3–10 candidates in an editorial review UI,
- approve/reject a candidate,
- download an approved original to controlled storage,
- create the canonical `MediaAsset`,
- generate attribution from stored metadata,
- track usages and variants.

## Out of scope for first implementation

- fully automated publishing,
- reverse-image search across the public web,
- scraping Google Images,
- automatically licensing agency photography,
- automated legal interpretation of unusual licences,
- face recognition,
- AI generation of factual race photography,
- automatic annotation of CC BY-SA assets without manual rights review.

---

# 2. Service boundaries

Recommended logical modules:

```text
Editorial Object
     │
     ▼
MediaDiscoveryService
     │
     ├── QueryBuilder
     ├── ProviderAdapter
     │      └── WikimediaCommonsAdapter
     ├── MetadataNormalizer
     ├── RightsEvaluator
     ├── DuplicateDetector
     ├── CandidateRanker
     └── PreviewCache
             │
             ▼
       MediaCandidate[]
             │
             ▼
        Editorial Review
             │ approve
             ▼
       MediaAssetService
             │
             ├── OriginalDownloader
             ├── ObjectStorage
             ├── AttributionRenderer
             └── VariantService
```

Provider-specific behaviour stays inside the adapter. The rest of the application works with normalized candidate objects.

---

# 3. Wikimedia Commons API strategy

Use the server-side MediaWiki Action API endpoint:

```text
https://commons.wikimedia.org/w/api.php
```

The application must identify itself with a descriptive HTTP `User-Agent`, for example:

```text
F1Intelligence/0.1 (https://example.com/about; contact@example.com)
```

Wikimedia's API access policy requires client identification. Browser clients should not call Commons directly for this feature; our backend performs provider calls and controls caching, retries and request volume.

## 3.1 Search

Use MediaWiki search as a generator so file results can be enriched in the same query.

Conceptual request:

```http
GET /w/api.php
?action=query
&format=json
&formatversion=2
&generator=search
&gsrsearch=McLaren Singapore 2026
&gsrnamespace=6
&gsrlimit=20
&prop=imageinfo
&iiprop=url|size|mime
&iiurlwidth=640
```

Namespace `6` is the File namespace.

The search API supports generator usage. Search relevance is provider relevance only; it must not become our final editorial ranking.

## 3.2 Metadata enrichment

For a shortlist of candidates, fetch extended metadata using `imageinfo` with `iiprop=extmetadata`.

Do not request expensive extended metadata for hundreds of search results. Wikimedia documents `extmetadata` as relatively expensive and recommends limiting its use.

Request only fields we need through `iiextmetadatafilter` where practical:

```text
ImageDescription
Artist
Credit
DateTimeOriginal
ObjectName
Permission
LicenseShortName
LicenseUrl
UsageTerms
Copyrighted
Attribution
AttributionRequired
NonFree
Categories
Restrictions
DeletionReason
```

Also request:

```text
url
size
mime
timestamp
```

Important: `extmetadata` values can contain parsed HTML and human-formatted text. They must be normalized and sanitized before display. They are not guaranteed to be clean plain strings.

Wikimedia notes that licence fields for multi-licensed files can be unreliable. Multi-licensed or inconsistent results therefore go to manual review.

---

# 4. Query generation

The query builder receives structured editorial context rather than a free-form prompt.

Example input:

```json
{
  "object_type": "story",
  "title": "McLaren Singapore upgrade",
  "season": 2026,
  "race": "Singapore Grand Prix",
  "circuit": "Marina Bay Street Circuit",
  "teams": ["McLaren"],
  "drivers": ["Lando Norris", "Oscar Piastri"],
  "topics": ["floor", "bodywork"],
  "date_from": "2026-09-14",
  "date_to": "2026-09-24"
}
```

Generate a bounded set of intents, typically 4–8:

```text
McLaren Singapore 2026
McLaren Singapore Grand Prix 2026
Lando Norris Singapore 2026
Oscar Piastri Singapore 2026
McLaren Marina Bay 2026
McLaren MCL Singapore 2026
```

Do not over-specify component terms in every query. Commons descriptions may identify the race/team/car while not naming a technical component.

## Query priority

1. team + race + season,
2. driver + race + season,
3. team + circuit + season,
4. team + car/chassis + season where known,
5. broader race + season fallback.

Each discovery job stores generated queries for reproducibility and debugging.

---

# 5. Normalized MediaCandidate

```text
MediaCandidate
├── id
├── discovery_job_id
├── provider
├── provider_asset_id
├── provider_page_title
├── source_page_url
├── original_file_url
├── preview_url
├── mime_type
├── width
├── height
├── file_size
├── title
├── description_raw
├── description_text
├── creator_raw
├── creator_text
├── credit_raw
├── credit_text
├── captured_at_raw
├── captured_at
├── licence_short_name
├── licence_url
├── usage_terms
├── attribution_raw
├── attribution_required
├── copyrighted
├── non_free
├── restrictions[]
├── categories[]
├── deletion_reason
├── rights_evaluation
├── rights_reasons[]
├── entity_matches[]
├── temporal_match
├── duplicate_match
├── score
├── rank
├── review_state
├── metadata_snapshot
├── discovered_at
└── metadata_fetched_at
```

`metadata_snapshot` stores the provider response relevant to the rights decision so a future audit can reconstruct what the system saw at approval time.

Do not use raw HTML fields directly in frontend rendering.

---

# 6. Rights evaluator

The evaluator is deterministic. No LLM may change an asset from unsafe/unclear to approved.

Initial output:

```text
auto_eligible
manual_review
rejected
```

## 6.1 Initial licence allowlist

Exact normalized values may vary, so map provider strings to internal licence IDs.

Initial automatic candidates:

```text
CC-BY-4.0
CC-BY-3.0
CC-BY-SA-4.0
CC-BY-SA-3.0
```

However:

- CC BY-SA candidates requiring annotation/compositing are manual-review for the derivative use,
- public-domain candidates are manual-review in MVP until the stated PD basis is checked,
- multi-licensed candidates are manual-review,
- missing licence metadata is rejected from auto-eligibility,
- `NonFree=true` is rejected,
- a populated `DeletionReason` is manual-review or rejected from new use,
- material `Restrictions` values trigger manual review,
- conflicting licence fields trigger manual review.

This allowlist is implementation policy, not a statement that other Commons licences are unusable.

## 6.2 Evaluation result

```json
{
  "decision": "auto_eligible",
  "licence_id": "CC-BY-4.0",
  "commercial_use_allowed": true,
  "derivatives_allowed": true,
  "share_alike_required": false,
  "attribution_required": true,
  "reasons": [
    "recognized_allowlisted_license",
    "non_free_false",
    "no_material_restrictions",
    "creator_present",
    "source_page_present"
  ]
}
```

The UI must expose reasons for manual-review states.

---

# 7. Metadata normalization

## HTML sanitization

Fields such as `Artist`, `Credit`, `Attribution`, `ImageDescription` and `Permission` can contain HTML.

Normalization pipeline:

```text
provider HTML
   ↓
strict HTML sanitizer
   ↓
allowed links only
   ↓
plain-text representation
   ↓
normalized structured fields
```

Never render provider HTML with unrestricted `dangerouslySetInnerHTML`.

## Creator selection

Priority:

1. explicit `Attribution` when Wikimedia indicates it should replace ordinary creator/credit handling,
2. `Artist`,
3. `Credit` only as a fallback/source field,
4. unresolved → manual review.

The uploader username must not automatically become photographer credit.

## Dates

`DateTimeOriginal` is best-effort. Wikimedia explicitly notes that human-formatted dates can be imprecise or non-machine-readable.

Store:

```text
captured_at_raw
captured_at nullable
```

Failure to parse a capture date must not cause the record to be discarded.

---

# 8. Duplicate detection

Perform duplicate checks before ranking.

Phase 1 keys:

- `provider + provider_asset_id`,
- canonical source page URL,
- normalized original file URL,
- SHA-256 after approved download.

Phase 2:

- perceptual hash (`pHash` or equivalent) for visually identical/near-identical local files.

A discovered candidate that already maps to an approved `MediaAsset` should return that asset as `existing_asset` rather than create another record.

Do not merge records solely by perceptual similarity when rights provenance differs.

---

# 9. Candidate scoring

Rights is a hard gate. Ranking runs only on `auto_eligible` and `manual_review` candidates, with manual-review candidates visually separated.

Initial score from 0–100:

```text
entity match                 0–30
race/circuit match           0–20
season/date match            0–15
search-provider relevance    0–10
image resolution             0–10
placement/aspect fit         0–5
metadata completeness        0–5
freshness                    0–5

repetition penalty           0 to -15
rights complexity penalty    0 to -20
```

Example entity matching:

```text
exact team + race        +20
named driver             +10
season                    +8
circuit/event category    +7
```

The score is an editorial prioritization mechanism, not a rights decision.

## Placement-aware reranking

A hero request and a card request may rank the same candidates differently.

```text
article_hero: favour >= 1600px width and landscape composition
mobile_card: favour clean center crop
team_page: favour identifiable team/car context
technical_evidence: favour visible component/detail over aesthetic composition
```

For MVP, composition may be approximated using dimensions/aspect ratio plus editor judgment. Computer-vision composition scoring is not required.

---

# 10. Discovery job lifecycle

```text
queued
running
provider_complete
rights_evaluated
ranked
ready_for_review
approved
completed
failed
```

Example flow:

```text
POST /internal/media/discovery-jobs
              ↓
         job queued
              ↓
     build search intents
              ↓
  Commons search requests
              ↓
   basic candidate merge
              ↓
 metadata fetch for shortlist
              ↓
      rights evaluation
              ↓
 duplicate detection + ranking
              ↓
       editor candidate tray
```

Jobs must be idempotent for the same object/context hash within a configurable freshness window.

---

# 11. Internal API contract

These are application APIs, not public endpoints.

## Create discovery job

```http
POST /api/admin/media/discovery
```

Request:

```json
{
  "object_type": "story",
  "object_id": "story_123",
  "placement": "story_hero",
  "max_candidates": 10
}
```

Response:

```json
{
  "job_id": "mdj_01...",
  "state": "queued"
}
```

## Read candidates

```http
GET /api/admin/media/discovery/{job_id}
```

Response includes:

- generated queries,
- provider status,
- ranked candidates,
- rights decision/reasons,
- existing MediaAsset match if any.

## Approve candidate

```http
POST /api/admin/media/candidates/{candidate_id}/approve
```

Request:

```json
{
  "object_type": "story",
  "object_id": "story_123",
  "placement": "story_hero",
  "editor_note": null
}
```

Approval performs a fresh rights metadata check before downloading the original. If material rights metadata changed since discovery, approval stops and returns `rights_changed`.

## Reject candidate

```http
POST /api/admin/media/candidates/{candidate_id}/reject
```

Store optional reason:

```text
irrelevant
poor_quality
wrong_event
rights_unclear
duplicate
not_editorially_useful
other
```

---

# 12. Approval transaction

Approval is not just a state toggle.

```text
Editor approves candidate
        ↓
Re-fetch canonical provider metadata
        ↓
Re-run rights evaluator
        ↓
Compare rights fingerprint with discovery snapshot
        ↓
Download original
        ↓
Validate MIME / dimensions / file limit
        ↓
Compute SHA-256 + perceptual hash
        ↓
Store original
        ↓
Create MediaAsset + RightsSnapshot
        ↓
Generate safe variants
        ↓
Create UsageRecord
        ↓
Return publishable asset
```

If any step fails, do not create a partially approved publishable asset.

Use a database transaction for database state and compensating cleanup for object-storage writes.

---

# 13. Rights fingerprint and snapshots

Store a deterministic fingerprint from the fields that materially affect permission:

```text
licence_short_name
licence_url
usage_terms
attribution_required
attribution
artist
credit
permission
non_free
restrictions
deletion_reason
```

```text
rights_fingerprint = SHA256(canonical_json(material_fields))
```

At approval time, compare the latest fingerprint with the candidate's discovery fingerprint.

Store immutable snapshots:

```text
MediaRightsSnapshot
├── id
├── media_asset_id / candidate_id
├── provider
├── provider_asset_id
├── rights_fingerprint
├── normalized_rights
├── raw_relevant_metadata
├── checked_at
└── evaluator_version
```

This gives us an audit trail when provider metadata changes later.

---

# 14. Storage strategy

Recommended buckets/prefixes:

```text
media/original/{media_asset_id}/source.ext
media/variants/{media_asset_id}/{variant_id}.webp
media/previews/{candidate_id}.webp
```

Do not expose object-storage write URLs to the browser.

## Candidate previews

Search-result thumbnails can be cached as short-lived review previews.

They are not production assets and must not bypass approval.

Recommended:

```text
preview cache TTL: 7 days
candidate DB retention: 30–90 days
approved MediaAsset: persistent
rights snapshots: persistent
```

Retention values are application policy and should be configurable.

---

# 15. Request control, caching and resilience

Wikimedia provider calls must be centralized in the backend.

Requirements:

- meaningful User-Agent on every request,
- connect/read timeouts,
- bounded concurrency,
- exponential backoff with jitter for transient failures,
- respect `Retry-After` when present,
- do not retry deterministic 4xx failures indefinitely,
- response caching,
- query-result cache,
- metadata cache keyed by provider asset ID + revision/timestamp where possible.

Start conservatively with an internal provider budget such as 2 requests/second per worker and tune from observation. This is our own safeguard, not a claim about Wikimedia's published maximum rate.

Because `extmetadata` is relatively expensive, fetch it only for a shortlist, for example the top 10–20 basic search candidates after query merging.

---

# 16. Database tables

Minimum persistence model:

```text
media_discovery_jobs
media_discovery_queries
media_candidates
media_candidate_entity_matches
media_assets
media_rights_snapshots
media_variants
media_usage_records
```

## `media_discovery_jobs`

Core fields:

```text
id
object_type
object_id
placement
context_hash
state
provider_status_json
created_by
created_at
started_at
completed_at
error_code
error_detail
```

## `media_candidates`

Core fields:

```text
id
discovery_job_id
provider
provider_asset_id
source_page_url
original_file_url
preview_url
normalized_metadata_json
rights_decision
rights_reasons_json
rights_fingerprint
score
rank
existing_media_asset_id
review_state
created_at
updated_at
```

Provider-specific raw metadata should be retained in a JSON field/snapshot rather than expanding every provider field into relational columns.

---

# 17. Admin candidate tray

The editor sees a visual shortlist, not raw API output.

Each candidate card displays:

```text
[preview]

McLaren · Singapore 2026
Creator: Jane Example
CC BY 4.0
✓ Commercial reuse candidate
✓ Cropping allowed by policy
Attribution required
1920 × 1280

Relevance 88
[Source] [Rights details]
[Approve]
```

Manual-review card:

```text
REVIEW REQUIRED
CC BY-SA 4.0
Requested placement creates an annotated derivative.

[Inspect rights]
[Reject]
```

The source page must always be one click away.

## Filters

MVP:

- Eligible,
- Needs review,
- Existing library,
- All.

Later:

- team,
- driver,
- race,
- orientation,
- provider,
- licence.

---

# 18. Security

External-media ingestion is an untrusted-input boundary.

Requirements:

- allowlist provider hosts for API and file download,
- prevent arbitrary URL fetching / SSRF,
- resolve redirects only to approved Wikimedia hosts/CDN hosts,
- enforce MIME/type allowlist,
- enforce maximum download size,
- inspect actual file signature rather than trusting extension,
- sanitize all provider HTML,
- never execute SVG/HTML directly from untrusted remote content in the admin UI,
- strip unsafe metadata from generated web variants,
- store originals outside the executable application path.

For MVP, limit production photography to standard raster image formats unless a format-specific review exists.

---

# 19. Observability

Metrics:

```text
media_discovery_jobs_total
media_discovery_job_duration_seconds
wikimedia_requests_total
wikimedia_request_errors_total
wikimedia_cache_hit_ratio
media_candidates_discovered_total
media_candidates_auto_eligible_total
media_candidates_manual_review_total
media_candidates_rejected_total
media_candidate_approval_rate
media_existing_asset_reuse_rate
media_rights_changed_on_approval_total
```

Structured logs must include:

```text
job_id
provider
query_hash
provider_asset_id
rights_decision
error_code
latency_ms
```

Do not log full sensitive provider-contract data for future paid providers.

---

# 20. Failure states

## Provider unavailable

- discovery job enters retryable failure,
- existing library results remain available,
- editor can retry later,
- page publishing must not be blocked if an image is optional.

## No eligible candidates

Return:

```text
No rights-safe external image found.
Recommended fallback: original diagram, chart or no hero image.
```

Never silently relax the licence policy.

## Missing creator

Manual review; no auto-approval.

## Rights metadata changes before approval

Stop approval, display diff, require fresh editor action.

## Original download fails

Do not mark MediaAsset publishable. Retry within bounded policy.

## Candidate deleted on Commons

Mark candidate unavailable. For already approved assets, flag the asset for rights/editorial review rather than automatically deleting local content without context.

---

# 21. Testing strategy

## Unit tests

- licence normalization,
- rights decisions,
- metadata HTML sanitization,
- date parsing,
- query generation,
- candidate score calculation,
- attribution renderer,
- rights fingerprint stability,
- duplicate key generation.

## Fixture tests

Keep recorded/sanitized API fixtures covering:

- CC BY 4.0,
- CC BY-SA 4.0,
- public-domain candidate,
- missing Artist,
- custom Attribution,
- Restrictions present,
- DeletionReason present,
- malformed date,
- multi-license ambiguity,
- duplicate provider asset.

Tests should not depend on live Commons responses.

## Integration tests

Against the real API in a low-frequency test suite:

- search returns File namespace candidates,
- metadata parser handles current response shape,
- thumbnail URL is usable,
- User-Agent is sent,
- continuation/pagination works,
- provider timeouts fail safely.

## Acceptance test

Given a Story containing team + race + season metadata:

1. editor requests media,
2. system generates queries,
3. Commons candidates appear,
4. unsafe/unclear licences cannot auto-approve,
5. eligible candidates show creator/licence/source,
6. editor opens canonical Commons source,
7. editor approves one asset,
8. system revalidates rights,
9. original is stored,
10. attribution renders automatically,
11. usage is linked to the Story,
12. future discovery can recognize and reuse the same asset.

---

# 22. Implementation sequence

## Phase 1 — provider proof of concept

- Wikimedia client,
- query builder,
- search endpoint,
- `imageinfo` metadata fetch,
- normalized candidate output,
- CLI/test fixture validation.

Exit criterion: one Story context reliably produces normalized candidates with source, creator and licence data.

## Phase 2 — rights and persistence

- licence normalizer,
- deterministic evaluator,
- discovery jobs/tables,
- rights snapshots,
- duplicate checks.

Exit criterion: no candidate can enter an approved state without an auditable rights decision.

## Phase 3 — admin review

- candidate tray,
- source/rights detail,
- approve/reject,
- existing-asset reuse.

Exit criterion: editor can select a safe image without reading raw API JSON.

## Phase 4 — ingestion and publishing

- original downloader,
- object storage,
- variants,
- attribution renderer,
- UsageRecord integration.

Exit criterion: approved asset can appear on Story/Article/Race pages with automated credit and provenance.

## Phase 5 — additional providers

Add `PhotographerAdapter` / `StockProviderAdapter` behind the same normalized candidate contract.

---

# 23. MVP acceptance criteria

The media-discovery MVP is complete when:

- Wikimedia Commons is queried through a server-side identified client,
- discovery starts from structured editorial context,
- search and metadata calls are cached and bounded,
- `extmetadata` is normalized safely,
- every candidate has an explicit rights decision,
- unsupported/ambiguous rights fail closed,
- candidate ranking cannot override rights rejection,
- editor sees 3–10 useful candidates when suitable Commons media exists,
- approval performs a fresh metadata/rights check,
- approved originals are stored under our control,
- every approved asset has a rights snapshot and attribution representation,
- duplicate/existing assets are reused where appropriate,
- external inputs are sanitized and downloads are host/type constrained,
- publishing still works gracefully when no suitable photo exists.

---

# References

Implementation should be checked against the current official documentation before provider code changes:

- MediaWiki Action API — Search: `https://www.mediawiki.org/wiki/API:Search`
- MediaWiki Action API — Imageinfo: `https://www.mediawiki.org/wiki/API:Imageinfo`
- CommonsMetadata / `extmetadata`: `https://www.mediawiki.org/wiki/Extension:CommonsMetadata`
- Wikimedia API access policy: `https://www.mediawiki.org/wiki/Wikimedia_APIs/Access_policy`
- Commons credit-line guidance: `https://commons.wikimedia.org/wiki/Commons:Credit_line`

The provider adapter should isolate API-shape changes so the rest of the product does not depend directly on Wikimedia-specific fields.


---

# 24. Additional discovery provider: F1-Fansite

The production discovery architecture is no longer Commons-only.

F1-Fansite is a metadata-only discovery adapter:

```text
F1-Fansite wallpaper index
        ↓
gallery discovery
        ↓
image URL + caption + alt text
        ↓
photographer / agency / origin asset ID extraction
        ↓
canonical entity classification
        ↓
story-media candidate matching
```

Hard rules:

- never treat F1-Fansite visibility as reuse permission;
- default to `rights_status=restricted` and `storage_policy=metadata_only`;
- do not download discovered binaries into R2 in this phase;
- preserve `discovery_page_url` and rights-evidence URL;
- resolve Getty/LAT/Sutton/DPPI/Red Bull Content Pool metadata as origin lineage, not as an automatic licence;
- candidate ranking may use race/driver/team overlap, but rights state remains an independent gate.

The same normalized media registry accepts source-article hero images captured during story ingestion. This means a Story can have useful image candidates before the richer Commons/stock approval workflow is implemented.

The command `make ingest-media` runs F1-Fansite discovery independently of Story materialization. Network discovery is intentionally not hidden inside the database materialization transaction.
