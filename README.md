# F1 Intelligence

F1 Intelligence is a Formula 1 intelligence and analysis platform focused on following stories over time rather than publishing isolated news rewrites.

> **Follow the story, not just the news.**

The platform combines race-weekend coverage, technical development tracking, regulation explainers, team and driver storylines, source evidence, and structured knowledge that can be reused across articles, race hubs, trackers and newsletters.

## Repository

```text
apps/web/     Next.js 16 public product
apps/api/     FastAPI research/content API
infra/        local infrastructure/bootstrap
docs/         product and technical specifications
```

The selected architecture is documented in [`docs/12_TECH_STACK_DATABASE_AND_REPO.md`](docs/12_TECH_STACK_DATABASE_AND_REPO.md).

## Local development

Requirements:

- Docker / Docker Compose
- Node.js 22+
- Python 3.12+
- `uv`

Bootstrap:

```bash
cp .env.example .env
make infra-up
make setup
```

On a fresh PostgreSQL volume, SQL files under `infra/postgres/` run automatically in filename order. If your database volume predates a newer bootstrap file, use the explicit setup target for that feature.

The synthetic Story fixture can be reapplied with:

```bash
make seed-demo
```

Then run the services in separate terminals:

```bash
make api-dev
make web-dev
```

Local endpoints:

- Web: `http://localhost:3000`
- Demo Story Page: `http://localhost:3000/stories/demo-rear-stability`
- FIA pilot Story Page: `http://localhost:3000/stories/fia-2026-sporting-decisions`
- API: `http://localhost:8000`
- Demo Story API: `http://localhost:8000/api/v1/stories/demo-rear-stability`
- API docs: `http://localhost:8000/docs`
- API health: `http://localhost:8000/health`

The demo Story is explicitly synthetic. It exists only to validate the vertical slice and must not be treated as Formula 1 reporting.

## Official FIA source ingestion

The first real ingestion adapter consumes the FIA's official press-release RSS feed. It stores the source headline, link, publication timestamp and matching metadata; it does not mirror FIA article bodies.

For an existing database, create the ingestion tables and pilot Story matching rules:

```bash
make ingestion-setup
```

Fetch the latest FIA RSS items, deduplicate them and attach qualifying official evidence to configured Stories:

```bash
make ingest-fia
```

The pilot rule intentionally requires a weighted match score. Generic press-conference transcripts should not attach merely because they contain `F1`; FIA decisions, calendar changes and regulation-related items can cross the threshold. Equal top scores are retained as `ambiguous` rather than silently attached.

## Checks

```bash
make api-test
make web-build
```

CI also runs API lint/tests and web lint/typecheck/build for pull requests.

## Documentation

The living specification is under [`docs/`](docs/README.md). Product decisions should be recorded there before they become hidden assumptions in code.

## Current implementation

The current vertical slice now reaches a real official source:

```text
FIA official RSS
  -> deterministic story matcher
  -> deduplicated Evidence row
  -> GET /api/v1/stories/{slug}
  -> Story Page evidence timeline
  -> direct source link back to FIA
```

The current media slice records source-article image URLs, rights-aware MediaAssets and Story media candidates, and adds metadata-only F1-Fansite discovery. Binary object storage remains deliberately deferred behind the R2-ready storage boundary.
