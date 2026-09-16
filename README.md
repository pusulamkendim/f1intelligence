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

Then run the services in separate terminals:

```bash
make api-dev
make web-dev
```

Local endpoints:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- API health: `http://localhost:8000/health`

`docker-compose.yml` starts PostgreSQL and Redis. On a fresh PostgreSQL volume, `infra/postgres/001_init.sql` creates the initial Story/Evidence/Publication/Media schema.

## Checks

```bash
make api-test
make web-build
```

CI also runs API lint/tests and web lint/typecheck/build for pull requests.

## Documentation

The living specification is under [`docs/`](docs/README.md). Product decisions should be recorded there before they become hidden assumptions in code.

## Current implementation target

The first vertical slice is intentionally narrow:

```text
Story Page
  -> Story API
  -> PostgreSQL Story + Evidence data
  -> evidence timeline
  -> approved MediaAsset
```

The next major implementation step after bootstrap is a real read-only Story API and a Story Page backed by database fixtures, followed by Wikimedia candidate discovery.
