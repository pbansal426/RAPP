# BRIEFING — 2026-07-02T04:50:40Z

## Mission
Evolve the existing RAPP Automotive AI Repair Engine with Firebase accounts, cascading selectors, OCR ingestion, smart OBD-II input, inline diagrams, persistent side chatbot, and back navigation.

## 🔒 My Identity
- Archetype: teamwork_preview_orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: /Users/prathambansal/Dev/RAPP/.agents/orchestrator
- Original parent: parent
- Original parent conversation ID: 4014231e-dcda-49bb-81c0-d82f5fbd5904

## 🔒 My Workflow
- **Pattern**: Project
- **Scope document**: /Users/prathambansal/Dev/RAPP/.agents/orchestrator/PROJECT.md
1. **Decompose**: Decompose the product evolution requirements into 6 testable milestones.
2. **Dispatch & Execute** (pick ONE):
   - **Delegate (sub-orchestrator)**: For each milestone, spawn a sub-orchestrator to run the iteration loop (Explorer -> Worker -> Reviewer -> Challenger -> Auditor) and verify correctness.
3. **On failure** (in this order):
   - Retry: nudge stuck agent or re-send task
   - Replace: spawn fresh agent with partial progress
   - Skip: proceed without (only if non-critical)
   - Redistribute: split stuck agent's remaining work
   - Redesign: re-partition decomposition
   - Escalate: report to parent (sub-orchestrators only, last resort)
4. **Succession**: Self-succeed at 16 spawns, write handoff.md, spawn successor, cancel timers.
- **Work items**:
  1. Baseline Verification [done]
  2. Home Page & Navigation Evolution [in-progress]
  3. Diagnose & Results Pages Evolution [pending]
  4. Premium Repair Page [pending]
  5. Firebase Setup & Accounts [pending]
  6. Final E2E Verification & Hardening [pending]
- **Current phase**: 1
- **Current focus**: Home Page & Navigation Evolution (Milestone 2)

## 🔒 Key Constraints
- Never place project code, tests, or data files under `.agents/`.
- No chromadb imports may exist outside the backend `rag/` module.
- No `auth.py`, login route, or `/login` page may exist in the codebase.
- Maintain premium grease-monkey UI contrast, large typography (read from 3 feet on cracked phone screen), and 48px tap targets.
- Ensure all frontend fetches are routed through `src/lib/api.ts`.
- Never reuse a subagent after it has delivered its handoff — always spawn fresh

## Current Parent
- Conversation ID: a6392d7e-78d9-4fac-a164-415e9d22ae0f
- Updated: 2026-07-02T04:50:40Z

## Key Decisions Made
- Decomposed the evolution task into 6 logical milestones.
- Will spawn a sub-orchestrator for Milestone 1 (Baseline Verification) to verify that the existing codebase and tests compile and pass.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| E2E Testing Orchestrator | self | Milestone 1 (E2E Test Suite) | completed | e97ab2e5-2c99-4ea1-ae2d-f5039763f217 |
| RAG Vector Store Orchestrator | self | Milestone 2 (RAG Vector Store) | completed | 2381f6d6-4c94-4a2d-a616-e88563aaf35c |
| Backend API Sub-orchestrator | self | Milestone 3 (Backend API Server) | completed | c5dfea8b-606d-42a1-b231-886bc21e1693 |
| Milestone 1 Sub-orchestrator | self | Baseline Verification | completed | cc63ea38-72e0-440e-a1f6-42d13aa34d9d |
| Milestone 2 Sub-orchestrator | self | Home Page & Navigation Evolution | interrupted | 2d642eba-c123-459f-80dd-7fc4f76e6498 |
| Build and Test Verifier | teamwork_preview_worker | Build & Test Audit | in-progress | db962540-e68a-410b-99d9-9b9b260e0bb1 |

## Succession Status
- Succession required: no
- Spawn count: 7 / 16
- Pending subagents: [db962540-e68a-410b-99d9-9b9b260e0bb1]
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: a6392d7e-78d9-4fac-a164-415e9d22ae0f/task-33
- Safety timer: none
- On succession: kill all timers before spawning successor
- On context truncation: run `manage_task(Action="list")` — re-create if missing

## Artifact Index
- /Users/prathambansal/Dev/RAPP/.agents/orchestrator/ORIGINAL_REQUEST.md — Verbatim user request
- /Users/prathambansal/Dev/RAPP/.agents/orchestrator/BRIEFING.md — Memory and state briefing
- /Users/prathambansal/Dev/RAPP/.agents/orchestrator/PROJECT.md — Project scope and layout
- /Users/prathambansal/Dev/RAPP/.agents/orchestrator/progress.md — Progress tracker
