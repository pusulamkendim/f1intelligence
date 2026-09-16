# Media Asset and Image Pipeline

## Purpose

F1 Intelligence needs a repeatable way to discover, verify, store and reuse visual assets without turning image selection into a manual copyright-risk bottleneck.

The goal is not to fill every page with photography. The visual system should deliberately combine:

- properly licensed editorial photography,
- open-license photography,
- original charts,
- original technical diagrams,
- original maps/timelines/annotated visuals,
- restrained generic illustration only where it does not imply a factual depiction of a real event.

The media pipeline must answer four questions before an external image is published:

1. **Where did this asset come from?**
2. **What exact licence or permission allows our intended use?**
3. **What attribution or downstream obligations apply?**
4. **Where has this asset already been used inside the product?**

The system should make a rights-safe choice easy and an unclear-rights choice difficult.

---

# 1. Editorial principles

## 1.1 Photography is evidence, not decoration

Use photography when it adds real editorial value:

- identifying a car specification or visible technical change,
- showing an event, driver, circuit or team context,
- supporting a race-weekend story,
- anchoring a Team, Driver or Race entity,
- strengthening a feature or long-form analysis.

Do not add a car image to every card simply because motorsport is visual.

## 1.2 Prefer original information graphics where they explain more

For technical analysis, original diagrams and charts will often be more useful than photography.

Examples:

- floor-edge change diagram,
- old/new component comparison,
- tyre-degradation chart,
- race strategy timeline,
- upgrade chronology,
- circuit-sector illustration,
- story evidence timeline.

This is strategically important because it improves editorial differentiation while reducing dependence on expensive or restricted photography.

## 1.3 No rights assumption from visibility

The following are **not** evidence of permission to reuse an image:

- appearing in Google Images,
- being publicly accessible on a website,
- being posted on a team or driver social account,
- being called a press image,
- being embedded in another publication,
- being downloadable without authentication,
- having no visible copyright notice.

The pipeline needs an affirmative rights basis, not the absence of an obvious restriction.

## 1.4 No silent provenance loss

If an image enters our storage, its source and rights metadata must enter with it. We should never end up with an orphaned `image_4837.jpg` whose licence can no longer be reconstructed.

---

# 2. Source hierarchy

The initial source priority should be:

## Tier A — original F1 Intelligence assets

Preferred whenever practical.

Includes:

- charts generated from permitted data,
- technical diagrams drawn in-house,
- original illustrations,
- screenshots of our own product UI,
- maps and timelines created by us,
- photography commissioned directly by us.

Rights confidence: highest when source inputs are themselves permitted.

## Tier B — explicitly reusable open-license assets

Primary external discovery source for MVP.

Typical source:

- Wikimedia Commons.

Every file must be evaluated individually from its file-description page. A platform-level assumption such as “Wikimedia images are free” is insufficient because licence terms differ by asset.

Common useful licence classes include:

- `CC BY` — commercial reuse generally permitted with required attribution and licence notice/link,
- `CC BY-SA` — commercial reuse generally permitted with attribution and ShareAlike obligations for adaptations,
- public domain — usable subject to verification of the stated public-domain basis and possible non-copyright restrictions.

The system should store the exact licence/version for each asset rather than collapsing everything into `creative_commons`.

## Tier C — direct photographer / agency agreement

Useful for current race photography that open-license sources cannot provide quickly enough.

Possible commercial models:

- per-image licence,
- event package,
- monthly subscription,
- season licence,
- contributor partnership,
- commissioned assignment.

Every agreement should map to a machine-readable rights profile where possible.

## Tier D — licensed editorial stock

Use selectively when coverage or immediacy justifies the cost.

The asset must remain tied to the supplier's permitted-use terms, licence identifier, territory/time limitations where applicable, and proof of purchase or subscription entitlement.

## Restricted by default — official F1/team/driver assets

Do not ingest Formula 1, team, driver or broadcaster photography merely because it is available online.

Formula 1's current IP guidance states that its rights include still images and other protected assets, and that third-party commercial use generally requires the appropriate rights/licence. Permitted editorial use of certain word marks does not automatically grant rights to photographs, artwork, video, timing data or other protected materials.

Team media-centre or press assets should also be treated as restricted unless their published terms clearly authorise the intended web/commercial use or we have direct permission.

---

# 3. Rights decision model

Every external asset receives a `rights_status` before it can become publishable.

Suggested values:

```text
pending_review
approved_open_license
approved_direct_license
approved_stock_license
approved_public_domain
restricted
expired
revoked
unclear
```

Only an `approved_*` state may be used in production.

## Required rights checks

For every candidate:

```text
Is the source page canonical?
        ↓
Is the creator / rights holder identified?
        ↓
Is an explicit licence or permission present?
        ↓
Does it allow commercial web use?
        ↓
Are derivatives/crops permitted?
        ↓
Are attribution terms known?
        ↓
Are ShareAlike or other downstream obligations understood?
        ↓
Are there material non-copyright restrictions?
        ↓
APPROVE / REJECT / MANUAL REVIEW
```

If any material step is unresolved, the pipeline should fail closed.

---

# 4. MediaAsset canonical object

`MediaAsset` should be a persistent entity in the content model, not a URL string attached directly to an article.

Conceptual schema:

```text
MediaAsset
├── id
├── asset_type
├── title
├── description
├── source_provider
├── source_page_url
├── original_file_url
├── local_storage_key
├── creator_name
├── rights_holder
├── licence_name
├── licence_version
├── licence_url
├── rights_status
├── commercial_use_allowed
├── derivatives_allowed
├── share_alike_required
├── attribution_required
├── attribution_text
├── attribution_url
├── permission_reference
├── acquired_at
├── rights_checked_at
├── rights_checked_by
├── rights_expires_at
├── original_filename
├── mime_type
├── width
├── height
├── file_size
├── perceptual_hash
├── checksum
├── dominant_entities[]
├── teams[]
├── drivers[]
├── races[]
├── seasons[]
├── circuits[]
├── components[]
├── topics[]
├── captured_at
├── usage_records[]
├── crop_variants[]
├── alt_text
├── editorial_notes
└── state
```

## `asset_type`

Initial values:

```text
photo
technical_diagram
chart
illustration
map
timeline_visual
logo_or_mark
screenshot
```

`logo_or_mark` should be restricted by default and require explicit rights review.

---

# 5. UsageRecord

The same asset may be reused across Story, Race, Team and Article surfaces. Usage should be tracked explicitly.

```text
UsageRecord
├── id
├── media_asset_id
├── object_type
├── object_id
├── placement
├── crop_variant
├── published_at
├── removed_at
└── notes
```

Example placements:

```text
article_hero
story_hero
race_hero
team_card
article_inline
technical_evidence
social_preview
newsletter
```

This enables us to answer:

- where is a particular licensed asset currently live?
- what must be removed if a licence expires?
- are we overusing the same image?
- which crop is associated with a particular placement?

---

# 6. Discovery pipeline

The media pipeline starts from structured editorial context rather than generic image search.

Example Story input:

```text
Story: McLaren Singapore upgrade
Race: Singapore GP
Season: 2026
Team: McLaren
Drivers: Lando Norris, Oscar Piastri
Topics: floor, bodywork, tyre degradation
Date window: race week ± 7 days
```

Generate source-specific search intents:

```text
McLaren Singapore 2026
McLaren MCL 2026 Singapore
Lando Norris Singapore 2026 McLaren
Singapore GP 2026 McLaren floor
```

The discovery layer returns candidate assets, not publishable assets.

```text
Editorial object
      ↓
Entity/date extraction
      ↓
Source-specific queries
      ↓
Candidate results
      ↓
Metadata fetch
      ↓
Rights validation
      ↓
Deduplication
      ↓
Editorial ranking
      ↓
Approved MediaAsset
```

---

# 7. Wikimedia Commons workflow

Wikimedia Commons is useful because its file pages expose source, author and licence metadata, but every file still requires asset-level verification.

## Candidate discovery

Search using combinations of:

- season,
- race/circuit,
- team,
- driver,
- car/chassis,
- event date,
- component/topic where relevant.

## Metadata to capture

For every candidate, capture at least:

- Commons file page URL,
- original file URL,
- original creator/author,
- source if different from uploader,
- exact licence and version,
- licence URL,
- attribution requirement,
- whether modification is allowed,
- ShareAlike requirement,
- image dimensions,
- upload date,
- stated creation/capture date where available,
- file description/categories.

Do not credit the uploader automatically when the file page identifies another creator.

## Approval rules

MVP safe allowlist can initially include only clearly understood classes such as:

```text
CC BY 4.0
CC BY-SA 4.0
CC BY 3.0
CC BY-SA 3.0
Public Domain — after manual confirmation of basis
```

Other licence families go to manual review rather than being automatically rejected forever.

## CC BY handling

Store and render:

- creator credit,
- source/file-page link,
- licence name/link,
- indication of modifications when required.

## CC BY-SA handling

In addition to attribution, adapted versions must be handled consistently with the applicable ShareAlike terms. Because cropping, annotations and compositing may create licence questions depending on the use, modified CC BY-SA assets should default to manual review until the implementation policy is legally validated.

## Storage policy

Prefer downloading an approved original into our own controlled media storage rather than depending on permanent hotlinking. Preserve the source page and original URL in metadata.

---

# 8. Direct photographer workflow

For a photographer or small agency partnership, define a reusable rights profile.

Example:

```text
ProviderRightsProfile
├── provider_id
├── agreement_reference
├── start_at
├── end_at
├── web_editorial_use
├── commercial_site_use
├── social_use
├── newsletter_use
├── modification_allowed
├── cropping_allowed
├── attribution_format
├── territory
├── usage_limit
├── exclusivity
└── notes
```

This avoids interpreting the contract from scratch for every image.

Potential workflow:

```text
Photographer feed/upload
        ↓
Metadata + event tagging
        ↓
Provider rights profile applied
        ↓
Asset-specific exceptions checked
        ↓
Media library
        ↓
Editorial selection
```

The system must still allow asset-level overrides because a provider may submit an image whose rights differ from the general agreement.

---

# 9. Licensed stock workflow

For paid editorial stock, capture evidence of entitlement.

Additional fields may include:

```text
supplier_asset_id
purchase_or_subscription_reference
invoice_reference
licence_snapshot
territory
allowed_channels[]
usage_limit
rights_expires_at
```

If supplier terms prohibit local long-term storage or require use through their delivery system, the provider adapter must honour those conditions rather than applying our default storage rule.

---

# 10. Candidate ranking

Rights validity is a hard gate; ranking happens only after eligibility.

Suggested editorial ranking signals:

1. direct relevance to current Story/Race/Team,
2. correct season/event/date,
3. clearly identified subject,
4. image quality/resolution,
5. composition suitable for intended placement,
6. freshness for current news,
7. uniqueness versus already used assets,
8. rights simplicity,
9. attribution burden,
10. source reliability.

Example scoring concept:

```text
eligible = rights_status starts with approved_

score =
    relevance
  + temporal_match
  + entity_match
  + visual_quality
  + placement_fit
  + freshness
  - repetition_penalty
  - rights_complexity_penalty
```

Never let visual relevance override an invalid or unclear licence.

---

# 11. Editorial review UI

The editor should not need to inspect raw rights metadata every time.

Candidate card:

```text
┌─────────────────────────────────────────────┐
│ [thumbnail]                                 │
│                                             │
│ McLaren · Singapore GP · 2026              │
│ Photographer: Jane Example                  │
│ Licence: CC BY 4.0                          │
│ Commercial use: ✓                           │
│ Crop/edit: ✓                                │
│ Attribution: required                       │
│                                             │
│ [Preview source] [Approve] [Reject]         │
└─────────────────────────────────────────────┘
```

Warning state:

```text
RIGHTS REVIEW REQUIRED
CC BY-SA 4.0 · requested use includes annotated derivative
[Review before use]
```

The UI should make the rights state more visually prominent than image popularity or aesthetic score.

---

# 12. Attribution rendering

Attribution is generated from stored rights metadata, not written manually on each page.

Possible display pattern beneath image:

```text
Photo: Jane Example / Wikimedia Commons · CC BY 4.0
```

The rendered credit should link to the source and licence where required.

Longer or provider-specific terms can be exposed through a media-credit detail view.

The attribution renderer should support:

- creator,
- provider,
- source link,
- licence name,
- licence link,
- modification note,
- custom contractual credit line.

Do not shorten a credit line if the licence/agreement requires a specific form.

---

# 13. Derivatives, crops and annotations

Every generated visual variant must retain a relationship to the source asset.

```text
MediaVariant
├── id
├── parent_media_asset_id
├── operation
├── dimensions
├── crop_coordinates
├── overlay_metadata
├── storage_key
├── generated_at
└── rights_review_status
```

Operations:

```text
resize
crop
format_conversion
compression
annotation
composite
colour_adjustment
```

Simple technical operations such as resizing or lossless format conversion are still recorded for provenance.

For licences with derivative obligations, annotation/compositing should trigger the required rights policy rather than silently producing a new asset.

---

# 14. Duplicate detection

Duplicate and near-duplicate detection prevents both clutter and licensing confusion.

Use:

- exact file checksum for identical binaries,
- perceptual hash for resized/cropped versions,
- source-provider asset ID,
- original source URL,
- creator + capture date + event metadata.

When a new candidate matches an existing asset:

```text
existing approved MediaAsset
        ↓
compare provenance / rights
        ↓
reuse existing canonical record
or
create separate rights-source record if legally distinct
```

Do not automatically merge two copies when their rights provenance differs.

---

# 15. Original diagrams and charts

Original analytical visuals should become first-class MediaAssets.

## Technical diagram input

Each diagram should record:

- Story/TechnicalConcept association,
- factual source references used to create it,
- author/editor,
- version,
- created_at,
- explanatory caption,
- whether the visual contains interpretive elements.

Example:

```text
TechnicalDiagram
McLaren floor edge — Singapore 2026

Sources:
- documented component submission
- trackside image observation

Solid line = documented geometry
Blue arrows = editorial airflow explanation
```

The diagram itself must not visually convert an inference into a documented fact.

## Charts

Charts should retain:

- source dataset,
- transformation/query definition,
- metric definition,
- filters,
- generated_at,
- chart version.

This allows data visuals to be reproduced when a Story is updated.

---

# 16. AI-generated imagery policy

AI-generated imagery is **not** the default substitute for missing race photography.

Do not use generated imagery to depict as factual:

- a real crash,
- a specific upgrade fitted to a real car,
- a driver quote/event,
- a race result,
- an alleged incident,
- a technical component presented as observed evidence.

Acceptable lower-risk uses may include:

- abstract editorial illustration,
- generic aerodynamic concept illustration,
- non-factual decorative backgrounds,
- conceptual educational imagery that is clearly not presented as documentary evidence.

Generated visuals should be labelled internally with:

```text
generation_method = ai_generated
model_or_provider
created_at
prompt_reference
editorial_purpose
```

If an AI-generated image could reasonably be interpreted as documentary photography, do not publish it as the visual for a factual current-event story.

Use of protected logos, liveries, branded assets or other third-party IP inside generated imagery must still follow the underlying rights policy; generation does not erase IP constraints.

---

# 17. Storage and delivery

## Canonical storage

Approved downloadable assets should be stored in controlled object storage with immutable originals.

Suggested layout:

```text
media/
  originals/{media_asset_id}/source.ext
  variants/{media_asset_id}/{variant_id}.webp
  diagrams/{media_asset_id}/...
  charts/{media_asset_id}/...
```

Never overwrite the original file with an optimized derivative.

## Delivery formats

Web delivery can produce:

- AVIF where supported,
- WebP fallback,
- JPEG/PNG where source or transparency requires it.

Generate responsive widths appropriate to the layout.

## Metadata durability

Database rights metadata is canonical. Object-storage EXIF/IPTC metadata may be preserved, but it is not sufficient as the only rights record.

---

# 18. Lifecycle and rights revalidation

Rights are not always permanent.

Revalidation triggers:

- approaching `rights_expires_at`,
- provider agreement change,
- takedown/request from rights holder,
- licence metadata changed at source,
- legal/editorial review,
- planned reuse in a new channel not covered by current permission.

Suggested state transition:

```text
approved_direct_license
        ↓ expiry warning
pending_review
        ↓
approved_direct_license / expired
```

If an asset becomes invalid, `UsageRecord`s allow all live placements to be located quickly.

---

# 19. Failure states

## No eligible image found

Do not lower the rights threshold.

Fallback order:

1. original chart/diagram,
2. neutral Race/Team contextual visual already approved,
3. text-forward layout,
4. intentionally image-free card/article.

Image absence is preferable to questionable rights.

## Licence unclear

State: `unclear`.

Action:

- do not publish,
- queue manual rights review,
- keep source metadata for future resolution.

## Attribution metadata incomplete

Reject automated approval when the selected licence requires attribution.

## Source page disappears

Keep our provenance snapshot/reference and revalidate before future reuse. Existing continued use depends on the licence/permission basis and should be reviewed when necessary.

## Takedown request

Immediately identify all `UsageRecord`s, unpublish/replace the asset while the request is reviewed, preserve internal evidence of prior permission/licence, and record the resolution.

## Rights profile expires

Block new usage automatically and flag existing placements for review.

---

# 20. Proposed service boundaries

The implementation can start as modules inside the main application rather than independent microservices.

Suggested components:

```text
MediaDiscovery
  └── source adapters and search intents

MediaMetadataFetcher
  └── source page + licence metadata

RightsValidator
  └── allowlist/rules/manual-review routing

MediaDeduplicator
  └── checksum + perceptual hash

MediaIngestor
  └── download, original preservation, metadata persistence

MediaProcessor
  └── resize/crop/format variants

AttributionRenderer
  └── placement-safe credit strings

MediaLibrary
  └── editorial browse/search/reuse
```

Keep source adapters isolated. Wikimedia Commons, a photographer feed and a future stock provider should not leak provider-specific fields throughout the domain model.

---

# 21. Search and reuse inside the CMS

Editors should be able to search the internal library before external discovery.

Search facets:

- team,
- driver,
- race,
- season,
- circuit,
- component/topic,
- creator,
- licence,
- asset type,
- date range,
- previous usage count.

Default flow:

```text
Need hero image
      ↓
Search existing approved assets
      ↓
Found good asset? ── yes → reuse
      │
      no
      ↓
External discovery pipeline
```

This reduces cost and rights-review repetition.

---

# 22. Media relationship to content objects

Media is attached to canonical content entities, not only publications.

```text
MediaAsset <-> Story
MediaAsset <-> Race
MediaAsset <-> Team
MediaAsset <-> Driver
MediaAsset <-> UpgradeEntry
MediaAsset <-> Publication
MediaAsset <-> TechnicalConcept
```

This enables a Story Page to accumulate visual evidence across multiple articles and races.

Example:

```text
Story: Red Bull rear stability
├── technical diagram
├── Azerbaijan trackside photo
├── driver portrait
├── degradation chart
└── upgrade comparison
```

An Article can select a subset of those assets without duplicating them.

---

# 23. MVP scope

The first implementation does **not** need a universal media-rights engine.

MVP should support:

1. internal MediaAsset library,
2. Wikimedia Commons candidate discovery,
3. exact licence metadata capture,
4. conservative CC BY / CC BY-SA / public-domain review path,
5. manual approval before first use,
6. local storage of permitted downloaded originals,
7. responsive image variants,
8. attribution generation,
9. checksum/perceptual-hash duplicate detection,
10. UsageRecord tracking,
11. original chart/diagram ingestion,
12. fallback to image-free layouts.

Direct photographer and paid-stock adapters can follow after publication volume proves the need.

---

# 24. MVP acceptance criteria

The media pipeline is ready for public MVP when:

- no external image can be published without a `MediaAsset` record,
- every published external MediaAsset has an approved rights state,
- creator/source/licence data is retained for every open-license asset,
- required attribution can be rendered automatically,
- source page and licence URL remain accessible from internal metadata,
- each asset's live usages can be enumerated,
- original files are preserved separately from derivatives,
- duplicate/near-duplicate candidates are detected,
- an editor can search existing assets by at least team, race, driver and season,
- a rights-expired/revoked asset can be blocked from new use,
- articles and cards render correctly with no image when no eligible asset exists,
- original diagrams/charts can be stored and reused as MediaAssets,
- generated imagery cannot be mistaken in the CMS for documentary photography.

---

# 25. Initial implementation sequence

### Phase 1 — domain model

Implement:

- `MediaAsset`,
- `MediaVariant`,
- `UsageRecord`,
- rights-status state machine.

### Phase 2 — Commons discovery

Implement:

- entity-aware search query generation,
- result metadata fetch,
- licence extraction,
- conservative allowlist/manual-review routing.

### Phase 3 — media library

Implement:

- internal search,
- candidate preview,
- rights summary,
- approve/reject,
- usage history.

### Phase 4 — delivery

Implement:

- object storage,
- image optimization,
- responsive variants,
- attribution renderer,
- frontend media component.

### Phase 5 — original intelligence visuals

Implement:

- chart registry,
- diagram versioning,
- source/evidence linkage,
- reusable technical visual components.

### Phase 6 — commercial providers

Only when needed:

- photographer partnership adapter,
- paid editorial-stock adapter,
- contract/profile expiry handling.

---

# 26. Rights references

Rights rules are time-sensitive and must be rechecked during implementation and when providers change their terms.

Primary references at the time this document was created:

- Formula 1 — Guidelines for use of trade marks and intellectual property rights: `https://www.formula1.com/en/information/guidelines.4EOKE9RRqevL4niTK9kWyt`
- Wikimedia Commons — Reusing content outside Wikimedia / licences: `https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia/licenses`
- Wikimedia Commons — technical reuse guidance: `https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia/technical`

These references are operational guidance, not a substitute for legal advice. For unclear high-value or commercial uses, obtain qualified legal review rather than weakening the pipeline's validation rules.
