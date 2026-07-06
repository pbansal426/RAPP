.PHONY: install dev test lint type-check docker-up docker-down clean backup-db

# ── Setup ─────────────────────────────────────────────────────────────────────
install:
	@echo "→ Installing Python deps via uv..."
	uv sync --all-groups
	@echo "→ Installing Node deps..."
	cd frontend && pnpm install
	@echo "→ Installing Playwright browsers..."
	npx playwright install --with-deps
	@echo "✅ All deps installed."

# ── Development ───────────────────────────────────────────────────────────────
dev-backend:
	uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend:
	cd frontend && pnpm dev

# Run both in parallel (requires 'make -j2 dev' or run separately)
dev:
	@echo "→ Start backend:  make dev-backend"
	@echo "→ Start frontend: make dev-frontend"
	@echo "→ Or use Docker:  make docker-up"

# ── Code Quality ──────────────────────────────────────────────────────────────
lint:
	@echo "→ Running Ruff..."
	uv run ruff check backend/
	@echo "→ Running Black (check only)..."
	uv run black --check backend/
	@echo "✅ Lint passed."

lint-fix:
	uv run ruff check --fix backend/
	uv run black backend/

type-check:
	@echo "→ Running mypy..."
	uv run mypy backend/
	@echo "✅ Type check passed."

# ── Tests ─────────────────────────────────────────────────────────────────────
test-unit:
	uv run pytest tests/unit/ -v

test-e2e:
	npx playwright test

test-e2e-ui:
	npx playwright test --ui

test-verify:
	chmod +x tests/verify_tests.sh && ./tests/verify_tests.sh

test: test-unit test-verify
	@echo "✅ All tests passed."

# ── Docker ────────────────────────────────────────────────────────────────────
docker-up:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

docker-up-prod:
	docker compose up --build -d

docker-down:
	docker compose down

docker-clean:
	docker compose down -v --rmi local

# ── Utilities ─────────────────────────────────────────────────────────────────
# Snapshot the irreplaceable rapp.db (accounts) to the external SSD. Safe to spam;
# no-ops cleanly when the SSD is unplugged. Also runs automatically on server startup.
backup-db:
	uv run python -m backend.core.backup

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache  -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache  -exec rm -rf {} + 2>/dev/null || true
	rm -f mock_app.log
	@echo "✅ Cleaned."
