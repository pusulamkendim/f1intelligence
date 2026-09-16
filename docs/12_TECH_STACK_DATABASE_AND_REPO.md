# Technical Stack, Database and Repository Architecture

## Decision

F1 Intelligence will start as a small polyglot monorepo with a public web application and a separate API/research service.

The initial stack is deliberately conservative:

- **Web:** Next.js 16 Active LTS, React 19, TypeScript, App Router.
- **API:** Python 3.12+, FastAPI 0.141.x, Pydantic v2.
- **Database:** PostgreSQL 17.
- **Cache / future jobs:** Redis 7.4.
- **Storage:** S3-compatible object storage in production; local filesystem adapter during MVP development.
- **HTTP clients:** `httpx` in Python.
- **Database access:** SQLAlchemy 2.x + asyncpg; Alembic is the migration path once schema evolution begins.
- **Search:** PostgreSQL full-text/trigram first. Do not add Elasticsearch/OpenSearch until actual search volume requires it.

Next.js 16 is used because it is the current Active LTS line. The web app should prefer Server Components and server-side data fetching by default. Client components are introduced only where interaction requires them.

## Why split web and API

The public product is primarily an editorial web experience, while ingestion, Wikimedia discovery, evidence normalization and future analysis pipelines are better suited to Python. Keeping those responsibilities separated avoids forcing research/media jobs into the web runtime.

```text
Browser
  |
  v
Next.js web
  |
  v
FastAPI API
  |---- PostgreSQL
  |---- Redis
  |---- object storage
  |---- Wikimedia / future source adapters
```

The split is logical, not organizational. Both applications live in the same repository and share one product roadmap.

## Repository layout

```text
f1intelligence/
├── apps/
│   ├── web/                 # Next.js public product
│   └── api/                 # FastAPI research/content API
├── infra/
│   └── postgres/            # local development database bootstrap
├── docs/                    # product and architecture specifications
├── docker-compose.yml       # local Postgres + Redis
├── .env.example
└── Makefile
```

Do not introduce a generic `packages/` directory until there is code that is genuinely shared.

## Runtime boundaries

### Web owns

- public routes and rendering,
- SEO metadata,
- Story/Race/Team/Article page composition,
- public search UI,
- responsive behavior,
- image rendering and attribution display,
- analytics events.

### API owns

- canonical content data,
- editorial/admin APIs,
- story/evidence persistence,
- media candidate discovery,
- rights validation,
- Wikimedia integration,
- future ingestion/normalization jobs,
- object-storage writes.

The web must not call Wikimedia directly from the browser.

## Database principles

1. Canonical editorial entities are relational tables, not opaque JSON documents.
2. JSONB is reserved for provider-specific/raw metadata and fields whose structure is genuinely variable.
3. Source evidence remains traceable after publication.
4. Articles/publications are outputs linked to Stories, not the source of truth.
5. Media rights metadata must remain queryable independently of presentation code.
6. Timestamps use `timestamptz`.
7. Primary keys use UUIDs.
8. Human-facing URLs use stable unique slugs.

## Initial schema

### `teams`

Canonical team entity.

Key fields:

- `id`
- `slug`
- `name`
- `active_season`
- timestamps

### `races`

Canonical race/event entity.

Key fields:

- `id`
- `season`
- `round`
- `slug`
- `official_name`
- `circuit`
- `country`
- `start_at`
- `status`
- `synthesis`

### `stories`

Persistent editorial story object.

Key fields:

- `id`
- `slug`
- `title`
- `summary`
- `status`
- `significance`
- `confidence`
- `what_changed`
- `why_it_matters`
- `what_to_watch_next`
- timestamps

### `evidence`

Traceable factual/source inputs.

Key fields:

- `id`
- `story_id`
- `source_type`
- `source_name`
- `source_url`
- `published_at`
- `author_or_speaker`
- `normalized_claim`
- `raw_excerpt_or_reference`
- `reliability_class`
- `directness`
- `raw_metadata` JSONB

### `publications`

Time-bound editorial outputs.

Key fields:

- `id`
- `slug`
- `type`
- `headline`
- `standfirst`
- `body`
- `status`
- publication/update timestamps

### `publication_stories`

Many-to-many link between publications and persistent Stories.

### `media_candidates`

Temporary discovery candidates. A candidate is not publishable merely because it exists.

Important fields include provider identifiers, source URLs, normalized rights metadata, rights state, score and raw provider metadata.

### `media_assets`

Approved canonical media asset.

Important fields include source provenance, creator, exact licence/version, attribution, commercial/derivative flags, checksums, storage key and rights-check timestamps.

### `media_asset_usages`

Tracks where every approved asset is used and which crop/placement is active.

## Relations deferred from the first bootstrap

The schema will later add explicit normalized relationships for:

- Story ↔ Team,
- Story ↔ Race,
- Story ↔ Driver,
- UpgradeEntry,
- TimelineEvent,
- Regulation,
- TechnicalConcept,
- richer evidence-to-claim relationships.

Do not add these tables speculatively before the first content ingestion path is implemented.

## API shape

Initial prefix:

```text
/api/v1
```

First endpoints to implement after bootstrap:

```text
GET  /health
GET  /api/v1/stories
GET  /api/v1/stories/{slug}
GET  /api/v1/races/{season}/{slug}
POST /api/v1/admin/media/discover
POST /api/v1/admin/media/candidates/{id}/approve
```

Public read endpoints should become cache-friendly. Admin write endpoints will require authentication before production use.

## Local development

Local infrastructure is intentionally minimal:

```text
PostgreSQL :5432
Redis      :6379
FastAPI    :8000
Next.js    :3000
```

The web and API run natively during development; Postgres and Redis run through Docker Compose.

## Production direction

The architecture should remain deployable in multiple ways:

- web on Vercel or a Node container,
- API on a container host/VM,
- managed or self-hosted PostgreSQL,
- S3/R2-compatible storage,
- managed/self-hosted Redis when background jobs are introduced.

Do not couple product code to one hosting vendor.

## Immediate implementation order

1. repository/dev environment bootstrap,
2. health checks and DB connectivity,
3. initial schema migration path,
4. seed one Race + Team + Story fixture,
5. read-only Story API,
6. Story Page wired to real API data,
7. Wikimedia candidate discovery,
8. editorial candidate approval,
9. Race Hub data path,
10. ingestion automation.

The MVP should become vertically usable before broad feature expansion.