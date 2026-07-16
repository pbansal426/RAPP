# Deferred Human Tasks — RAPP

> **What this is:** a running checklist of setup steps that **only a human can do** (buy a
> domain, create a third-party account, paste a real secret into a deployed environment).
> AI agents have written the code so each of these **fails safe / no-ops until the key exists**
> — nothing here is blocking local development. Come back to this list when you're getting
> ready to deploy for real users, or hand it to an AI and work through it together.
>
> **Last updated:** 2026-07-16 (added Block 2.1 / PostHog).
> **Convention:** each item lists the exact env var(s) to set and what stays broken/mocked until you do.

---

## How to use this file

- ⬜ = not done yet · ✅ = done (set the date + who).
- Env vars go in the **deployed** environment's config (not committed `.env`). Local dev needs none of these.
- When you complete one, flip its box and note the date so the next session knows.

---

## 1. ⬜ Email deliverability — Resend  *(from Block 1.4)*

**Why deferred:** waiting until the app's final name/domain is decided before buying a domain.
(See memory note `block-1-4-email-deferred`.)

**Human steps:**
1. Decide the final app name → **buy a domain** for it.
2. Create a **Resend** account (or Postmark/SendGrid — Resend is what the code assumes).
3. In Resend, **verify the domain** (add the DNS TXT/CNAME records Resend gives you — requires DNS control).
4. Set these in the deployed env:
   - `RESEND_API_KEY` = your Resend API key
   - `EMAIL_FROM` = an address on the **verified** domain, e.g. `"RAPP <hello@yourdomain.com>"` (NOT `onboarding@resend.dev`)

**Until done:** magic-link sign-in emails don't actually send. In `development` they're returned in the
API response (dev convenience). In `staging`/`production` the backend **refuses to boot** with the sandbox
sender (`backend/core/config.py` validator, Block 1.4) — this is intentional: loud failure, not silent broken auth.

---

## 2. ⬜ Product analytics — PostHog  *(from Block 2.1)*

**Why deferred:** analytics code is wired and no-op-safe; just needs a real project key to start flowing events.

**Human steps:**
1. Create a **free-tier PostHog** account + project (https://posthog.com).
2. Grab the **Project API Key** (starts `phc_...`) from Project Settings.
3. Set in the deployed env (and in `frontend/.env.local` if testing locally):
   - `NEXT_PUBLIC_POSTHOG_KEY` = the `phc_...` project key  *(frontend)*
   - `NEXT_PUBLIC_POSTHOG_HOST` = `https://us.i.posthog.com` (or EU host) — *optional, defaults to US*
   - `POSTHOG_API_KEY` = same `phc_...` key  *(backend, for the server-side `checkout_completed` event)*
   - `POSTHOG_HOST` = matching host — *optional, defaults to US*

**Until done:** both the frontend (`lib/analytics.ts`) and backend (`services/analytics.py`) **no-op entirely** —
zero network calls to PostHog, app behaves identically. The 5 funnel events (`vin_submitted`, `diagnose_completed`,
`results_viewed`, `checkout_started`, `checkout_completed`) simply don't fire.
Verify live by walking VIN → diagnose → results → Unlock and watching PostHog's live event stream.

---

## 3. ⬜ Payments go-live — Polar (Merchant of Record)

**Why deferred:** the app runs on a free **mock checkout** by default; real money needs a Polar account + products.

**Human steps:**
1. Create a **Polar** account and set up your products/prices (single-incident + annual pass).
2. Set in the deployed env:
   - `POLAR_ACCESS_TOKEN` = your Polar API token
   - `POLAR_WEBHOOK_SECRET` = the webhook signing secret (for `POST /api/webhooks/payments`)
   - `POLAR_PRODUCT_ID_TIER_1` / `_TIER_2` / `_TIER_3` / `_ANNUAL` = your real Polar product IDs
3. (Optional revenue) `AMAZON_ASSOCIATE_TAG` = your Amazon Associates tag (e.g. `rapp-20`) to earn on parts links.

**Until done:** checkout uses the mock stub (`mode: "mock"`) — it 303s straight back and unlocks the guide with
no real payment. The `checkout_completed` analytics event only fires on a **real confirmed Polar payment**, so it
won't appear in mock mode (expected).

> Note: legacy `STRIPE_*` env vars still exist in config but Polar is the active path; the old `/api/webhooks/stripe`
> route is a deprecated 410-Gone stub. Don't wire up Stripe.

---

## 4. ⬜ Production secrets & config (before any deploy)

These must be real in `staging`/`production` — the dev defaults are for local only.

- `JWT_SECRET_KEY` = a strong random secret, **≥32 bytes** (dev default `supersecretkeyforlocaldev` must NOT ship;
  PyJWT warns on keys shorter than 32 bytes). This signs all auth/reset/verify tokens.
- `DATABASE_URL` = a **Postgres** URL for production (local dev defaults to `sqlite:///./data/rapp.db`).
- `ENVIRONMENT` = `staging` or `production` (unlocks the email-must-be-real guard in item 1).
- `ALLOWED_ORIGINS` = comma-separated real frontend origin(s).
- `FRONTEND_URL` / `BACKEND_URL` = real deployed URLs.

**Until done:** app runs on local SQLite + dev secrets — fine for development, **not safe for real users**.

---

## 5. ⬜ Gemini API — quota & the usage-warning decision

**Current state:** your live `GEMINI_API_KEY` is hooked to the app. Per your standing instruction, agents treat
Gemini calls as **blocked by default** and ask before running anything that spends the key (see memory
`gemini-key-usage-blocked`). Operations that spend it: `/repair` guide generation, repair ChatPanel messages,
`/api/vin/ocr` photo/scan, and live-LLM `/api/diagnose`.

**Human decisions / steps to revisit later:**
- ⬜ **Quota:** Gemini free tier is only **20 requests/day per model** — a live VIN-scan session or a few repair
  generations can exhaust it. Move to a **paid Gemini tier** before real users.
- ⬜ **Open product question:** do you want an **in-app warning/confirmation gate** before Gemini-spending actions
  (e.g. "This will use an AI credit — continue?" before the `/repair` page generates, or before sending a chat)?
  This is a *new feature*, out of scope for Block 2.1, and not yet built. If you want it, it should be scoped as
  its own block. Flagged here so it isn't forgotten.

---

## Quick reference — every env var mentioned above

| Env var | Item | Optional? |
|---|---|---|
| `RESEND_API_KEY` | 1 Email | required in staging/prod |
| `EMAIL_FROM` | 1 Email | required in staging/prod |
| `NEXT_PUBLIC_POSTHOG_KEY` | 2 Analytics | optional (no-op if unset) |
| `NEXT_PUBLIC_POSTHOG_HOST` | 2 Analytics | optional (defaults US) |
| `POSTHOG_API_KEY` | 2 Analytics | optional (no-op if unset) |
| `POSTHOG_HOST` | 2 Analytics | optional (defaults US) |
| `POLAR_ACCESS_TOKEN` | 3 Payments | needed for live payments |
| `POLAR_WEBHOOK_SECRET` | 3 Payments | needed for live payments |
| `POLAR_PRODUCT_ID_TIER_1/2/3/ANNUAL` | 3 Payments | needed for live payments |
| `AMAZON_ASSOCIATE_TAG` | 3 Payments | optional (extra revenue) |
| `JWT_SECRET_KEY` | 4 Prod config | required in staging/prod |
| `DATABASE_URL` | 4 Prod config | required in staging/prod |
| `ENVIRONMENT` | 4 Prod config | required in staging/prod |
| `ALLOWED_ORIGINS` | 4 Prod config | required in staging/prod |
| `FRONTEND_URL` / `BACKEND_URL` | 4 Prod config | required in staging/prod |
| `GEMINI_API_KEY` | 5 Gemini | already set (live) |
