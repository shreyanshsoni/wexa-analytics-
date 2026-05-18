.PHONY: dev backend worker beat frontend migrate migration test lint typecheck install setup

# ── Dev (run each in a separate terminal) ────────────────────────────────────
backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	cd backend && .venv/bin/celery -A app.workers.celery_app worker --loglevel=info -Q ingestion,celery

beat:
	cd backend && .venv/bin/celery -A app.workers.celery_app beat --loglevel=info

frontend:
	cd frontend && npm run dev

# ── Database ─────────────────────────────────────────────────────────────────
migrate:
	cd backend && .venv/bin/alembic upgrade head

migration:
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(name)"

rollback:
	cd backend && .venv/bin/alembic downgrade -1

seed:
	cd backend && .venv/bin/python scripts/seed.py

# ── Quality ──────────────────────────────────────────────────────────────────
test:
	cd backend && .venv/bin/pytest tests/ -v --tb=short

lint:
	cd backend && .venv/bin/ruff check app/ tests/

lint-fix:
	cd backend && .venv/bin/ruff check --fix app/ tests/

typecheck:
	cd backend && .venv/bin/mypy app/

# ── Setup ────────────────────────────────────────────────────────────────────
install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install --upgrade pip && .venv/bin/pip install -e ".[dev]"
	cd frontend && npm install

setup: install migrate
	@echo "✅ Setup complete. Run 'make backend', 'make worker', 'make beat', 'make frontend' in separate terminals."
