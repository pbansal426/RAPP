# Block 2.1 — Baseline funnel analytics (PostHog)

> **Model**: Sonnet 5 · **Thinking**: Medium · **Stage**: 2 (Measurement & Growth) · **Status**: ⬜ Not started
> **Parent**: [`../imp_part_2.md`](../imp_part_2.md) §2.1

---

## TL;DR

Wire PostHog into both frontend and backend, firing **exactly 5 events** (no more) at defined funnel points. Everything must **no-op safely when the PostHog key is unset** (the default), matching how `GEMINI_API_KEY`/`RESEND_API_KEY`/payment keys already behave — never crash or block core functionality on a missing third-party key.

**Human prerequisite (flag, don't block on it)**: a free-tier PostHog account + Project API Key must exist before events flow live. Write the no-op-safe code now; the key gets added to env vars later by a human.

---

## ⚠️ Corrections vs. `imp_part_2.md` — READ THESE FIRST

The parent plan's event table has three location errors caused by since-changed code. Use the corrected locations below.

1. **`diagnose_completed` does NOT fire in `diagnose/page.tsx`.** The `POST /api/diagnose` call actually lives in **`frontend/src/app/results/page.tsx`** (in the mount `useEffect`, the `api.post<DiagnosisResponse>('/api/diagnose', …).then((res) => …)` at ~line 189). Fire `diagnose_completed` in that `.then`. The `/diagnose` page only collects symptoms/tools and navigates; it never calls the API.
2. **`checkout_completed` fires in the POLAR webhook, not a Stripe one.** Payments migrated Stripe → Polar (Merchant of Record). The confirmed-payment branch is in `backend/routers/payments.py::polar_webhook` (route `POST /api/webhooks/payments`), inside the `elif event_type in ("checkout.created", "checkout.updated", "order.created"):` handler, specifically the `if payment_confirmed and …:` block that calls `_record_guide_unlock(...)` (~lines 228-240). Fire the event right after that `_record_guide_unlock` call. The old `/api/webhooks/stripe` route is now a 410-Gone deprecation stub — **do not touch it.**
3. **`layout.tsx` is a Next.js *server* component** (no `'use client'` directive). You **cannot** call `posthog.init()` or any browser API directly in it. Create a small **client** component (`'use client'`) that does the init inside a `useEffect`, and render that component from `layout.tsx`. Details below.

---

## Event taxonomy (implement EXACTLY these 5 — invent no others)

| Event | Where | Properties |
|---|---|---|
| `vin_submitted` | `frontend/src/app/page.tsx`, at each of the 4 VIN-entry paths (manual / YMM / photo / scan) once a VIN resolves | `method: "manual" \| "ymm" \| "photo" \| "scan"` |
| `diagnose_completed` | **`results/page.tsx`** (see correction #1), in the diagnose `.then` | `is_high_risk: boolean`, `has_recommended_parts: boolean` |
| `results_viewed` | `results/page.tsx`, on mount once `diagnosis` has loaded | `guide_fee: number`, `has_recalls: boolean` |
| `checkout_started` | `results/page.tsx`, inside `handlePay`, right before the `api.post('/api/payments/create-checkout', …)` call | `price_type: "single" \| "annual"` |
| `checkout_completed` | **backend `polar_webhook`** (see correction #2), after `_record_guide_unlock` in the confirmed-payment branch | `price_type`, `vin` (no symptoms/PII) |

---

## Implementation

### Frontend

#### 1. Add the dependency

`frontend/package.json` — add `posthog-js` to `dependencies` (pick the current stable major, e.g. `"posthog-js": "^1.160.0"`). Then install with the repo's pinned toolchain:
```bash
cd frontend && ./node_modules/.bin/... # use the same package manager the repo uses (pnpm). If `pnpm install` hits ERR_PNPM_IGNORED_BUILDS, that's the known pnpm quirk — the dependency still resolves; see CLAUDE.md.
```
> Per `CLAUDE.md`: `pnpm install` may emit `ERR_PNPM_IGNORED_BUILDS`; that's expected and doesn't block. Do not edit `pnpm-workspace.yaml`.

#### 2. Single analytics wrapper — `frontend/src/lib/analytics.ts` (NEW)

Match the existing single-wrapper pattern (`lib/api.ts`, `lib/auth.ts`). Do **not** scatter raw `posthog.capture()` calls through components.

```ts
'use client';

import posthog from 'posthog-js';

const KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? 'https://us.i.posthog.com';

let initialized = false;

/** Idempotent init. No-ops entirely if NEXT_PUBLIC_POSTHOG_KEY is unset. */
export function initAnalytics(): void {
  if (initialized || !KEY || typeof window === 'undefined') return;
  posthog.init(KEY, { api_host: HOST, capture_pageview: false });
  initialized = true;
}

/** Fire an event. No-ops if PostHog was never initialized (key unset). */
export function track(event: string, properties?: Record<string, unknown>): void {
  if (!initialized) return;
  posthog.capture(event, properties);
}
```

#### 3. Client init component — `frontend/src/app/PostHogInit.tsx` (NEW)

Because `layout.tsx` is a server component, initialization goes in a tiny client component:
```tsx
'use client';

import { useEffect } from 'react';
import { initAnalytics } from '@/lib/analytics';

export default function PostHogInit() {
  useEffect(() => {
    initAnalytics();
  }, []);
  return null;
}
```

Render it in `frontend/src/app/layout.tsx` — add the import and drop `<PostHogInit />` inside `<body>`, next to `<HeaderAuthLink />`:
```tsx
import HeaderAuthLink from './HeaderAuthLink';
import PostHogInit from './PostHogInit';
// ...
      <body className="dark bg-slate-900">
        <PostHogInit />
        <HeaderAuthLink />
        {children}
      </body>
```
> Do **not** remove or alter the `className="dark bg-slate-900"` on `<body>` — it's a frozen E2E test hook.

#### 4. Fire the 4 frontend events

- **`page.tsx`** — `import { track } from '@/lib/analytics';`. Find each of the 4 points where a VIN successfully resolves (manual submit, YMM submit, photo OCR success, scan success) and add `track('vin_submitted', { method: 'manual' })` etc. with the matching `method`.
- **`results/page.tsx`** — `import { track } from '@/lib/analytics';`.
  - In the diagnose `.then((res) => { … })`, add:
    ```tsx
    track('diagnose_completed', {
      is_high_risk: res.is_high_risk,
      has_recommended_parts: (res.recommended_parts?.length ?? 0) > 0,
    });
    ```
  - Add a small `useEffect` that fires once `diagnosis` is loaded:
    ```tsx
    useEffect(() => {
      if (!diagnosis) return;
      track('results_viewed', {
        guide_fee: diagnosis.cost_breakdown?.guide_fee ?? 0,
        has_recalls: (recalls?.count ?? 0) > 0,
      });
    }, [diagnosis, recalls]);
    ```
  - In `handlePay(priceType)`, right before the `api.post('/api/payments/create-checkout', …)` call, add:
    ```tsx
    track('checkout_started', { price_type: priceType });
    ```

### Backend

#### 5. Add the dependency

`pyproject.toml` — `posthog` is already in `uv.lock` as a transitive dep but is **not** a listed direct dependency; relying on an unlisted transitive is fragile. Add it to the `[project].dependencies` list (line 7-24), e.g. `"posthog>=3.0.0,<4.0.0"`, then `uv sync --all-groups`.

#### 6. Settings field — `backend/core/config.py`

Add alongside the other optional keys (near `gemini_api_key`, line 47):
```python
    posthog_api_key: str | None = None
    posthog_host: str = "https://us.i.posthog.com"
```

#### 7. Backend wrapper — `backend/services/analytics.py` (NEW)

```python
"""Server-side PostHog event capture. No-ops entirely when POSTHOG_API_KEY
is unset (the default) -- matches gemini/resend/stripe: never crash or block
a request on a missing third-party key."""
from __future__ import annotations

import structlog

from backend.core.config import settings

logger = structlog.get_logger()

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not settings.posthog_api_key:
        return None
    try:
        from posthog import Posthog

        _client = Posthog(
            project_api_key=settings.posthog_api_key, host=settings.posthog_host
        )
    except Exception as exc:  # never let analytics init break a request
        logger.warning("posthog_init_failed", error=str(exc))
        _client = None
    return _client


def track(event: str, properties: dict | None = None, distinct_id: str = "server") -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.capture(distinct_id=distinct_id, event=event, properties=properties or {})
    except Exception as exc:  # analytics must never surface as a 5xx
        logger.warning("posthog_capture_failed", event=event, error=str(exc))
```

#### 8. Fire `checkout_completed` in `polar_webhook`

`backend/routers/payments.py` — `from backend.services import analytics` (or `from backend.services.analytics import track as track_analytics`). Inside the `if payment_confirmed and metadata.get("price_type") != "annual" and checkout_session_id and vin:` block, right after the `_record_guide_unlock(...)` call (~line 234-240), add:
```python
            analytics.track(
                "checkout_completed",
                properties={"price_type": metadata.get("price_type"), "vin": vin},
                distinct_id=user_id or (user.id if user else "anonymous"),
            )
```
> Only `vin` and `price_type` — **no symptoms, no email, no PII.**

---

## Do NOT touch

- `/api/webhooks/stripe` (the 410-Gone stub) — deprecated, unrelated.
- The `<body className="dark bg-slate-900">` class list.
- Any core request flow — every analytics call must be fire-and-forget and no-op when the key is unset.
- Do not add events beyond the 5 in the table.

---

## Verification

1. **No-op with no key (the default) — app behaves identically to before**:
   - `cd frontend && ./node_modules/.bin/next build` passes.
   - `uv run pytest tests/unit/ -v` + `ruff`/`black`/`mypy` pass.
   - Run the app end-to-end with **no** `POSTHOG_API_KEY`/`NEXT_PUBLIC_POSTHOG_KEY`: no errors, no network calls to PostHog (check the browser network tab shows no `posthog.com` requests).
2. **With a real free-tier key set**: walk VIN entry → diagnose → results → click Unlock, and confirm `vin_submitted`, `diagnose_completed`, `results_viewed`, `checkout_started` appear in the PostHog live event stream. (`checkout_completed` only fires on a real confirmed Polar payment, so it won't appear in mock-checkout mode — that's expected.)

---

## Definition of Done

- [ ] `posthog-js` added to `frontend/package.json`; `posthog` added to `pyproject.toml` `[project].dependencies`
- [ ] `lib/analytics.ts`, `app/PostHogInit.tsx` (client), `services/analytics.py` created; `PostHogInit` rendered in `layout.tsx`
- [ ] `posthog_api_key`/`posthog_host` added to `Settings`
- [ ] All 5 events fire at the corrected locations (diagnose in results/page.tsx; checkout_completed in polar_webhook) — no extra events
- [ ] Build/lint/type/tests pass; app runs cleanly with no key set (no PostHog network calls)
- [ ] Human task (create PostHog account + set keys) noted in §5 session log
- [ ] Committed: `feat(analytics): Block 2.1 PostHog funnel events (no-op safe)`
- [ ] `imp_part_2.md` §1 tracker row 2.1 → `✅ Done`; session logged in §5
