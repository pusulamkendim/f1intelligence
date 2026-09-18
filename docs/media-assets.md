# Media assets and story imagery

This layer treats images as rights-aware structured data rather than decorative URLs.
A discovered image can be attached to a story without granting permission to download, cache, self-host or publish that image.

## Pipeline

```text
Source article / media discovery
        |
        v
image URL + caption + provenance
        |
        v
media_assets
        |
        +--> media_asset_entities (race / driver / team)
        |
        +--> source_item_media_assets
        |
        +--> story_media_candidates
                  |
                  +--> hero
                  +--> supporting
                  +--> thumbnail
```

Binary storage is optional. The registry works when every asset remains an external URL.

## Story image capture

Editorial and team article parsers retain JSON-LD, Open Graph, Twitter-card or RSS media image URLs in `source_items.raw_metadata.image_url`.

When a source item materializes into a canonical story, that image becomes:

- a `media_assets` row;
- a `source_item_media_assets` relation;
- a non-selected `story_media_candidates` hero candidate.

This records the image immediately while deferring the publication decision.

## F1-Fansite

F1-Fansite is a discovery/index source, not a binary asset origin for this system.

The media discovery adapter:

- discovers `/f1-wallpaper/` galleries;
- records gallery image URLs without downloading them;
- retains gallery title, caption and alt text;
- extracts photographer and agency where present;
- extracts origin provider / asset IDs such as Red Bull Content Pool identifiers;
- records explicit notes such as `editorial use only`;
- classifies driver, team and race entities from gallery title + caption;
- proposes matching story candidates based on shared canonical entities.

Default policy:

```text
source_role     = discovery
rights_status   = restricted
storage_policy  = metadata_only
```

F1-Fansite-discovered binaries must not be copied to R2 unless rights are independently resolved at the original provider.

## Content roles

Intrinsic asset roles describe what is visible in the image:

| Role | Meaning |
| --- | --- |
| `race_hero` | General race hero image |
| `podium` | Top three, trophies, champagne |
| `winner` | Winner at finish / parc ferme |
| `race_start` | Grid start, Turn 1, opening lap |
| `overtake` | Important pass or wheel-to-wheel battle |
| `incident` | Crash, contact, spin or other incident |
| `pit_stop` | Important pit stop / pit lane moment |
| `strategy` | Image supporting tyre or pit strategy |
| `driver_action` | A specific driver on track |
| `team_action` | Multiple cars, pit wall, team action |
| `technical_detail` | Wing, floor, brake, upgrade detail |
| `celebration` | Parc ferme / team celebration |
| `reaction` | Driver or team-principal reaction |
| `driver_portrait` | Driver portrait/headshot |
| `car_profile` | Car studio/profile image |
| `launch` | Launch/livery reveal |
| `garage` | Garage/mechanics |
| `circuit` | Circuit imagery |
| `article_hero` | Hero image supplied by a source article |
| `generic` | Photo with no stronger deterministic role |

Story roles are separate: `hero`, `supporting`, and `thumbnail`.

The same media asset can therefore be a `podium` image intrinsically while acting as the `hero` image for one story and a `supporting` image for another.

## Story matching

Source-article images are high-confidence candidates because the source article already belongs to the story.

Discovery assets use canonical entity overlap:

- shared race + driver + event-shaped role -> `exact_event`;
- shared race -> `race_match`;
- shared driver/team -> `entity_match`;
- explicit editorial selection can later use `manual`.

Candidates remain `selected=false` by default. No automatic publication policy is introduced in this PR.

Typical fallback intent:

```text
exact event photo
  -> involved drivers / teams in the same race
  -> primary driver action photo
  -> team action
  -> race hero
  -> portrait / generic fallback
```

## Source strategy

### Origin / licence-capable sources

- Wikimedia Commons: asset-level licence + attribution required.
- Team media centres: terms vary by team and asset.
- Red Bull Content Pool: editorial rights must be attached to each asset.
- Audi MediaCenter: verify the asset's editorial-use notice.
- Getty Images / LAT Images / Sutton Images / DPPI: licence resolution required.

### Discovery/reference sources

- F1-Fansite: race/gallery discovery, captions, photographer/agency and provider IDs.
- Formula1.com: article image reference only unless separately licensed.
- OpenF1 headshot URLs: reference only; the URL does not grant image reuse rights.

## Rights model

Each `media_assets` row records source role/provider lineage, photographer/agency, licence/usage data, rights status, storage policy, and verification evidence.

Rights and storage are independent:

```text
DISCOVERED
    |
    v
RIGHTS_UNKNOWN / RESTRICTED
    |
    v
ORIGIN_RESOLVED
    |
    v
STORAGE_ALLOWED
    |
    +--> REMOTE_REFERENCE
    +--> CACHE_ALLOWED
    +--> SELF_HOST_ALLOWED
```

Only rights-cleared states are candidates for future binary storage.

## R2 readiness

No binary upload happens in this PR.

The schema already has `r2_bucket`, `r2_key`, `content_hash`, MIME type, dimensions and aspect-ratio fields. Optional environment variables are reserved for Cloudflare R2, and `app.media.storage` defines the storage interface plus deterministic object keys.

Planned layout:

```text
{season}/{race-slug}/assets/{media-asset-uuid}/original.jpg
{season}/{race-slug}/assets/{media-asset-uuid}/1600.webp
{season}/{race-slug}/assets/{media-asset-uuid}/1200.webp
{season}/{race-slug}/assets/{media-asset-uuid}/800.webp
{season}/{race-slug}/assets/{media-asset-uuid}/thumb.webp
```

A future worker may use separate private/public R2 buckets. Discovery ingestion must never implicitly promote an asset into public storage.

## Commands

Run discovery independently from story materialization:

```bash
make ingest-media
```

Tune the initial F1-Fansite scan:

```bash
GALLERY_LIMIT=5 ASSET_LIMIT=120 make ingest-media
```

## Story API

Story list responses expose the highest-ranked current hero candidate as `hero_image_url` and `hero_media_asset_id`.

Story detail responses expose all candidates with URL, intrinsic content role, story role, source/origin provider, photographer/agency, rights status, storage policy, match reason/confidence, and selected state.

This allows the product layer to adopt a stricter publication rule later without changing ingestion or losing previously discovered imagery.
