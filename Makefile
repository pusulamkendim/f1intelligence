SHELL := /bin/bash

.PHONY: setup infra-up infra-down api-dev api-test web-dev web-build

setup:
	cp -n .env.example .env || true
	cd apps/api && uv sync
	cd apps/web && npm install

infra-up:
	docker compose --env-file .env up -d postgres redis

infra-down:
	docker compose --env-file .env down

api-dev:
	cd apps/api && uv run fastapi dev app/main.py --port 8000

api-test:
	cd apps/api && uv run pytest

web-dev:
	cd apps/web && npm run dev

web-build:
	cd apps/web && npm run build
