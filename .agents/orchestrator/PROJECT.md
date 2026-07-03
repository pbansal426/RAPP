# Project: RAPP Phase 2 Redesign

## Architecture
The application consists of a FastAPI backend and a Next.js 14 frontend, now evolved to support Firebase user accounts and advanced ingestion.
- **Backend API**: FastAPI application in `backend/main.py`. Coordinates VIN decoding using NHTSA public API, stubs Stripe payments, and diagnosis/repair procedures.
- **RAG Engine**: Vector store interface in `backend/rag/` containing a ChromaDB backend for retrieving OEM-like repair instructions.
- **Frontend App**: Next.js 14 TypeScript app in `frontend/`. Communicates with backend via `src/lib/api.ts` and with Firebase (Auth/Firestore) directly on the client side.
- **Firebase Integration**: Client-side SDK in `src/lib/firebase.ts`. Uses Firebase Auth (email/password) and Cloud Firestore for storing user profiles and saved repairs.

## Milestones
| # | Name | Scope | Dependencies | Status | Conv ID |
|---|------|-------|-------------|--------|---------|
| 1 | Baseline Audit & Verification | Run existing unit/E2E tests and build checks | None | PLANNED | |
| 2 | Design System & 4-Step Selector | globals.css styling updates, 4-step cascading dropdown on homepage with spec locking | M1 | PLANNED | |
| 3 | Automotive Diagnostic Panel | Hero card, brand logo, isolated OBD-II tags/chips, HEIC preview, tool search & filter | M2 | PLANNED | |
| 4 | Affiliate Parts & Garage Sign-up | Curated affiliate cards, 3-column price comparison, post-repair Garage Vault sign-up | M3 | PLANNED | |
| 5 | Final Verification & Build Integrity | E2E test runs, pytest, frontend production build, forensic audit | M4 | PLANNED | |

## Code Layout
```
/Users/prathambansal/Dev/RAPP
├── backend/
│   ├── main.py
│   └── rag/
│       ├── __init__.py
│       ├── vector_store.py
│       └── retriever.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       ├── app/
│       │   ├── page.tsx
│       │   ├── diagnose/
│       │   │   ├── ObdCodePicker.tsx
│       │   │   ├── ToolSelector.tsx
│       │   │   ├── VehicleHeroCard.tsx
│       │   │   └── page.tsx
│       │   ├── results/
│       │   │   ├── PartsPurchasePlan.tsx
│       │   │   └── page.tsx
│       │   ├── repair/
│       │   │   ├── ChatPanel.tsx
│       │   │   ├── ConclusionPhase.tsx
│       │   │   ├── SaveGuidePrompt.tsx
│       │   │   └── page.tsx
│       │   ├── garage/
│       │   │   └── page.tsx
│       │   └── layout.tsx
│       └── lib/
│           ├── api.ts
│           └── firebase.ts
└── tests/
    ├── e2e-mvp-flow.spec.ts
    └── verify_tests.sh
```
