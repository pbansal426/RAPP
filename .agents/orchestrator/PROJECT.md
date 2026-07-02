# Project: Automotive AI Repair Engine Product Evolution

## Architecture
The application consists of a FastAPI backend and a Next.js 14 frontend, now evolved to support Firebase user accounts and advanced ingestion.
- **Backend API**: FastAPI application in `backend/main.py`. Coordinates VIN decoding using NHTSA public API, stubs Stripe payments, and diagnosis/repair procedures.
- **RAG Engine**: Vector store interface in `backend/rag/` containing a ChromaDB backend for retrieving OEM-like repair instructions.
- **Frontend App**: Next.js 14 TypeScript app in `frontend/`. Communicates with backend via `src/lib/api.ts` and with Firebase (Auth/Firestore) directly on the client side.
- **Firebase Integration**: Client-side SDK in `src/lib/firebase.ts`. Uses Firebase Auth (email/password) and Cloud Firestore for storing user profiles and saved repairs.

## Milestones
| # | Name | Scope | Dependencies | Status | Conv ID |
|---|------|-------|-------------|--------|---------|
| 1 | Baseline Verification | Run existing unit/E2E tests and build checks | None | DONE | cc63ea38-72e0-440e-a1f6-42d13aa34d9d |
| 2 | Home Page & Navigation Evolution | Cascading Y/M/M selector, Tesseract.js OCR capture, back navigation | M1 | IN_PROGRESS | a01c66a7-b7d5-4651-a589-ef536715fd7f |
| 3 | Diagnose & Results Pages Evolution | Hero card, logo, searchable OBD-II picker, image upload preview, SVG tools, text reduction | M2 | PLANNED | |
| 4 | Premium Repair Page | Inline diagrams, 5-phase procedure, side-panel chatbot with contextual prompts | M3 | PLANNED | |
| 5 | Firebase Setup & Accounts | Client Firebase Auth & Firestore, optional sign-up, /garage route, Log In link | M4 | PLANNED | |
| 6 | Final E2E Verification & Hardening | Run all E2E verification scenarios, pytest, pnpm build checks | M5 | PLANNED | |

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
│       │   │   └── page.tsx
│       │   ├── results/
│       │   │   └── page.tsx
│       │   ├── repair/
│       │   │   ├── page.tsx
│       │   │   └── success/
│       │   │       └── page.tsx
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
