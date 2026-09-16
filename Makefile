SHELL := /bin/bash

.PHONY: setup infra-up infra-down seed-demo api-dev api-test web-dev web-build

setup:
	cp -n .env.example .env || true
	cd apps/api && uv sync
	cd apps/web && npm install

infra-up:
	docker compose --env-file .env up -d postgres redis

infra-down:
	docker compose --env-file .env down

seed-demo:
	docker compose --env-file .env exec -T postgres psql -U $${POSTGRES_USER:-f1} -d $${POSTGRES_DB:-f1intelligence} < infra/postgres/002_seed_demo_story.sql

api-dev:
	cd apps/api && uv run fastapi dev app/main.py --port 8000

api-test:
	cd apps/api && uv run pytest

web-dev:
	cd apps/web && npm run dev

web-build:
	cd apps/web && npm run build
