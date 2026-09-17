SHELL := /bin/bash

.PHONY: setup infra-up infra-down seed-demo ingestion-setup ingest-fia ingest-fia-docs ingest-formula1 ingest-sources list-sources ingest-jolpica ingest-openf1 api-dev api-test web-dev web-build

setup:
	cp -n .env.example .env || true

infra-up:
	docker compose --env-file .env up -d

infra-down:
	docker compose --env-file .env down

seed-demo:
	docker compose --env-file .env exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < infra/postgres/seed_demo.sql

ingestion-setup:
	@for migration in \
		infra/postgres/001_init.sql \
		infra/postgres/002_seed_demo_story.sql \
		infra/postgres/003_official_ingestion.sql \
		infra/postgres/004_seed_fia_ingestion_story.sql \
		infra/postgres/005_entity_registry.sql \
		infra/postgres/006_seed_2026_entity_registry.sql \
		infra/postgres/007_ingestion_entity_links.sql \
		infra/postgres/008_seed_2026_driver_numbers.sql \
		infra/postgres/009_fia_event_documents.sql \
		infra/postgres/010_structured_race_data.sql \
		infra/postgres/011_structured_entity_links.sql \
		infra/postgres/012_race_weekend_sessions.sql \
		infra/postgres/013_openf1_lap_stint_position.sql \
		infra/postgres/014_evidence_canonical_provenance.sql \
		infra/postgres/015_structured_race_context.sql \
		infra/postgres/016_session_starting_grid.sql \
		infra/postgres/017_session_overtakes.sql \
		infra/postgres/018_calendar_amendment_safe_race_identity.sql \
		infra/postgres/019_source_item_entities.sql; do \
			docker compose --env-file .env exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < "$$migration" || exit $$?; \
	done

ingest-fia: ingestion-setup
	cd apps/api && uv run python -m app.ingestion.run_fia --limit 50

ingest-fia-docs: ingestion-setup
	cd apps/api && uv run python -m app.ingestion.run_fia_documents --limit 50

ingest-formula1: ingestion-setup
	cd apps/api && uv run python -m app.ingestion.run_formula1 --limit $${LIMIT:-25} --pages $${PAGES:-3}

ingest-sources: ingestion-setup
	cd apps/api && uv run python -m app.ingestion.run_sources $${SOURCE:+--source $$SOURCE} --limit $${LIMIT:-20}

list-sources:
	cd apps/api && uv run python -m app.ingestion.run_sources --list-sources

ingest-jolpica: ingestion-setup
	cd apps/api && uv run python -m app.ingestion.run_jolpica --season $${SEASON:-2026} $${ROUND:+--round $$ROUND}

ingest-openf1: ingestion-setup
	cd apps/api && uv run python -m app.ingestion.run_openf1 --season $${SEASON:-2026}

api-dev:
	cd apps/api && uv run uvicorn app.main:app --reload --port 8000

api-test:
	cd apps/api && uv run pytest

web-dev:
	cd apps/web && npm run dev

web-build:
	cd apps/web && npm run build
