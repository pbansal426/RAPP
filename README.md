# RAPP — Automotive AI Repair Engine

> Convert vehicle diagnostic input (VIN + symptoms / OBD-II codes) into tool-constrained, RAG-verified repair instructions in under 10 seconds.

---

## Quick Start

### Option A — Local (Poetry + pnpm)

**Requirements:** Python 3.11+, Poetry, Node 20+, pnpm

```bash
# 1. Clone and install all deps
make install

# 2. Copy and fill in secrets
cp .env.example .env

# 3. Start backend (port 8000)
make dev-backend

# 4. Start frontend in a new terminal (port 3000)
make dev-frontend
```

Open [http://localhost:3000](http://localhost:3000).

---

### Option B — Docker (recommended for production)

**Requirements:** Docker 24+, Docker Compose v2

```bash
cp .env.example .env   # fill in secrets
make docker-up         # builds and starts both services
```

| Service  | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| Backend  | http://localhost:8000 |
| Health   | http://localhost:8000/health |

---

## Project Structure

```
RAPP/
├── backend/
│   ├── main.py          # FastAPI app — all routes, config, logging
│   └── rag/             # ChromaDB RAG abstraction layer
│       ├── __init__.py  # Thread-safe singleton factory
│       ├── vector_store.py  # Abstract + ChromaDB + Mock implementations
│       └── retriever.py     # retrieve(query, vin_meta, k) helper
├── frontend/            # Next.js 14 TypeScript app (pnpm)
│   └── src/app/
│       ├── page.tsx          # / — VIN input
│       ├── diagnose/         # /diagnose — symptoms + tools
│       ├── results/          # /results — free summary + paywall
│       ├── repair/           # /repair — unlocked steps + citations
│       └── repair/success/   # /repair/success — Stripe callback
├── tests/
│   ├── e2e-mvp-flow.spec.ts  # Playwright E2E tests
│   ├── mock_app.py           # FastAPI mock for test isolation
│   ├── verify_tests.sh       # Fault-injection verification harness
│   └── unit/
│       ├── test_rag.py       # 10 RAG unit tests
│       └── test_api.py       # FastAPI endpoint unit tests
├── pyproject.toml       # Poetry + ruff/black/mypy/pytest config
├── docker-compose.yml   # Production Compose
├── docker-compose.dev.yml  # Dev override (hot reload)
├── Makefile             # Developer shortcuts
└── .github/workflows/ci.yml  # GitHub Actions CI
```

---

## Available Commands

```bash
make install        # Install all Python + Node deps
make dev-backend    # Start FastAPI with hot reload
make dev-frontend   # Start Next.js dev server
make lint           # ruff + black check
make lint-fix       # ruff + black auto-fix
make type-check     # mypy strict
make test-unit      # pytest unit tests
make test-verify    # Playwright fault-injection harness
make test           # Run all tests
make docker-up      # Docker dev mode (hot reload)
make docker-up-prod # Docker production mode
make docker-down    # Stop containers
make clean          # Remove cache dirs
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check → `{"status": "ok"}` |
| GET | `/api/vin/{vin}` | Live NHTSA VIN decode → year/make/model/engine/drive |
| POST | `/api/diagnose` | Free diagnosis summary + safety flag |
| POST | `/api/repair` | RAG-verified repair steps (requires Stripe session) |
| POST | `/api/payments/create-checkout` | Create Stripe checkout session |
| POST | `/api/payments/webhook` | Stripe webhook receiver |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for LLM diagnosis |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `STRIPE_PRICE_SINGLE` | Stripe price ID for single repair unlock |
| `VECTOR_STORE` | `chromadb` (default) or `mock` |
| `FRONTEND_URL` | Frontend origin for CORS |

---

## Safety

High-risk system detection is built into both the API (`/api/diagnose`) and the frontend results page. The following trigger a non-dismissible warning banner:

- Airbag / SRS systems
- EV / hybrid high-voltage battery
- Pressurized fuel lines

These warnings cannot be dismissed by the user and are shown before any procedure content.
