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

On a fresh PostgreSQL volume, both `001_init.sql` and the synthetic `002_seed_demo_story.sql` fixture run automatically. If the database volume already existed before the demo fixture was added, apply it explicitly:

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
- API: `http://localhost:8000`
- Demo Story API: `http://localhost:8000/api/v1/stories/demo-rear-stability`
- API docs: `http://localhost:8000/docs`
- API health: `http://localhost:8000/health`

The demo Story is explicitly synthetic. It exists only to validate the vertical slice and must not be treated as Formula 1 reporting.

## Checks

```bash
make api-test
make web-build
```

CI also runs API lint/tests and web lint/typecheck/build for pull requests.

## Documentation

The living specification is under [`docs/`](docs/README.md). Product decisions should be recorded there before they become hidden assumptions in code.

## Current implementation

The first read-only vertical slice now works end to end:

```text
Story Page
  -> GET /api/v1/stories/{slug}
  -> PostgreSQL Story + Evidence data
  -> evidence timeline
```

The next implementation slice is to connect real, verified ingestion evidence and then attach approved MediaAssets from the Wikimedia discovery pipeline.
