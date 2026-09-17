SHELL := /bin/bash

.PHONY: setup infra-up infra-down seed-demo ingestion-setup ingest-fia ingest-fia-docs ingest-jolpica api-dev api-test web-dev web-build

setup:
	cp -n .env.example .env || true
	cd apps/api && uv sync
	cd apps/web && npm install

infra-up:
	docker compose --env-file .env up -d postgres redis

infra-down:
	docker compose --env-file .env down

seed-demo:
	docker compose --env-file .env exec -T postgres sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < infra/postgres/002_seed_demo_story.sql

ingestion-setup:
	docker compose --env-file .env exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < infra/postgres/003_official_ingestion.sql
	docker compose --env-file .env exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < infra/postgres/004_seed_fia_ingestion_story.sql
	docker compose --env-file .env exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < infra/postgres/005_entity_registry.sql
	docker compose --env-file .env exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < infra/postgres/006_seed_2026_entity_registry.sql
	docker compose --env-file .env exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < infra/postgres/007_ingestion_entity_links.sql
	docker compose --env-file .env exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < infra/postgres/008_seed_2026_driver_numbers.sql
	docker compose --env-file .env exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < infra/postgres/009_fia_event_documents.sql
	docker compose --env-file .env exec -T postgres sh -lc 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < infra/postgres/010_structured_f1_data.sql

ingest-fia: ingestion-setup
	cd apps/api && uv run python -m app.ingestion.run_fia --limit 50

ingest-fia-docs: ingestion-setup
	cd apps/api && uv run python -m app.ingestion.run_fia_documents --season 2026

ingest-jolpica: ingestion-setup
	cd apps/api && uv run python -m app.ingestion.run_jolpica --season $${SEASON:-2026} $${ROUND:+--round $$ROUND}

api-dev:
	cd apps/api && uv run uvicorn app.main:app --reload --port 8000

api-test:
	cd apps/api && uv run pytest

web-dev:
	cd apps/web && npm run dev

web-build:
	cd apps/web && npm run build
