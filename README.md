# RAPP — Automotive AI Repair Engine

> Convert vehicle diagnostic input (VIN + symptoms / OBD-II codes) into tool-constrained, RAG-verified repair instructions in under 10 seconds.

---

## What is RAPP?
**RAPP (Automotive AI Repair Engine)** is a smart web application designed to be a "mechanic over your shoulder" for anyone who wants to repair their own car. It takes the guesswork out of DIY car maintenance by generating hyper-specific, step-by-step repair instructions tailored perfectly to your exact vehicle.

### Why does it exist?
Taking a car to the dealership or a mechanic is incredibly expensive, and many people want to save money by doing repairs themselves. However, finding the right information is tough—YouTube tutorials might be for a slightly different model year, and factory service manuals are dense, confusing, and hard to access. 

RAPP solves this by bridging the gap. It gives you dealership-level diagnostic insights and custom repair instructions that are actually easy to read, significantly lowering the barrier to entry for DIY mechanics and saving them hundreds of dollars.

### How does it work?
1. **Identify the Car:** You simply point your phone's camera at your car's VIN barcode (or upload a photo of the door jamb), and RAPP's AI instantly decodes the exact Year, Make, Model, and engine configuration.
2. **Input the Problem:** You type in the symptoms your car is experiencing (e.g., "rough idle when cold") or plug in any check-engine OBD-II codes you got from a scanner.
3. **Free AI Diagnosis:** RAPP's backend searches through official government databases (NHTSA) for recalls and scans a massive library of Technical Service Bulletins (TSBs). It then gives you a free root-cause diagnosis, a list of required parts, and a cost comparison showing how much you'd save doing it yourself vs. going to a dealer. It even flags high-risk safety warnings (like high-voltage EV batteries or explosive airbags).
4. **Custom Repair Guide:** If you want to do the repair, you pay a small one-time fee (or an annual subscription) to unlock the full guide. RAPP generates a custom, step-by-step walkthrough tailored specifically to your car and *the actual tools you own*. 
5. **Live Garage Assistant:** While you are under the hood with grease on your hands, you can use the built-in AI chat assistant to ask questions like *"What is the torque spec for this bolt?"* or *"How do I safely disconnect this specific connector?"* and it will answer instantly.

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
