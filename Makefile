.PHONY: up down migrate test lint

up:
	docker compose up -d

down:
	docker compose down

migrate:
	cd backend/orchestrator && alembic upgrade head

test-backend:
	cd backend/orchestrator && pytest

test-worker:
	cd worker && pytest

lint-backend:
	cd backend/orchestrator && ruff check .

dev-orchestrator:
	cd backend/orchestrator && uvicorn app.main:app --reload --port 8000

dev-seller:
	cd apps/web-seller && npm run dev

dev-admin:
	cd apps/web-admin && npm run dev

dev-mobile:
	cd apps/mobile && flutter run
