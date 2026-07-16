# Block 2.3 — Wire `/hub` and `/check-ai` into real navigation

> **Model**: Gemini Flash 3.5 · **Thinking**: Low · **Stage**: 2 (Measurement & Growth) · **Status**: ⬜ Not started
> **Parent**: [`../imp_part_2.md`](../imp_part_2.md) §2.3

---

## TL;DR

Both `/hub` (Knowledge Hub) and `/check-ai` ("Check My ChatGPT Answer" acquisition funnel) are **fully-built pages with zero inbound links** — reachable only by typing the URL. Add links: two persistent nav links in the global header widget, plus one contextual link on `/results`. Additive only — no frozen `data-testid` changes.

---

## Context you need

- `frontend/src/app/HeaderAuthLink.tsx` is the only persistent global UI (a fixed top-right widget). It currently holds a theme toggle + auth-gated Garage/Settings/Log-In links.
- `frontend/src/app/hub/page.tsx` and `frontend/src/app/check-ai/page.tsx` both exist and render real content.
- These are additive links; the E2E suite (`tests/e2e-mvp-flow.spec.ts`) must still pass.

---

## ⚠️ Corrections vs. `imp_part_2.md`

None. Verified accurate. `HeaderAuthLink.tsx`'s `linkStyle` object (line 9) and the `{configured && !loading && (...)}` auth-gated block (line 25) are exactly as described. The `/results` "Free Diagnosis & Mod Overview" card is around line 430.

---

## Change 1 — `frontend/src/app/HeaderAuthLink.tsx`: two always-visible nav links

The current return (lines 19-36):
```tsx
    <div style={{ position: 'fixed', top: 14, right: 16, zIndex: 500, display: 'flex', alignItems: 'center', gap: 8 }}>
      <ThemeToggle />
      {configured && !loading && (
        user ? (
          <>
            <a href="/garage" style={{ ...linkStyle, color: 'var(--text-secondary)' }}>My Garage</a>
            <a href="/settings" style={{ ...linkStyle, color: 'var(--text-secondary)' }}>Settings</a>
          </>
        ) : (
          <a href="/signin" style={{ ...linkStyle, color: 'var(--accent-orange)' }}>Log In</a>
        )
      )}
    </div>
```

Add the two links **between `<ThemeToggle />` and the `{configured && !loading && (...)}` block** so they show regardless of auth state:
```tsx
    <div style={{ position: 'fixed', top: 14, right: 16, zIndex: 500, display: 'flex', alignItems: 'center', gap: 8 }}>
      <ThemeToggle />
      <a href="/hub" style={{ ...linkStyle, color: 'var(--text-secondary)' }}>Guides</a>
      <a href="/check-ai" style={{ ...linkStyle, color: 'var(--text-secondary)' }}>Check My AI Answer</a>
      {configured && !loading && (
        user ? (
          <>
            <a href="/garage" style={{ ...linkStyle, color: 'var(--text-secondary)' }}>My Garage</a>
            <a href="/settings" style={{ ...linkStyle, color: 'var(--text-secondary)' }}>Settings</a>
          </>
        ) : (
          <a href="/signin" style={{ ...linkStyle, color: 'var(--accent-orange)' }}>Log In</a>
        )
      )}
    </div>
```
> Reuse the existing `linkStyle` object — don't invent new styling. Note: on very narrow screens this adds two chips to a fixed corner widget; that's acceptable per the parent plan (a real navbar replaces this widget in a later phase).

---

## Change 2 — `frontend/src/app/results/page.tsx`: contextual funnel link

Add a small text link near the free-diagnosis summary card. That card's header is around line 430-434:
```tsx
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <p className="card-label" style={{ margin: 0 }}>Free Diagnosis & Mod Overview</p>
          <span className="badge badge-free">Verified AI Analysis</span>
        </div>
        ...
```
> Note: that badge text may read `AI-Generated, RAG-Grounded Analysis` if **Block 1.3** ran first — either is fine; don't change it here.

Add the link **immediately after the closing `</div>` of the `data-testid="free-diagnosis-summary"` block** (the summary content ends around line 453-454, just before the card's closing `</div>`). Insert:
```tsx
          <a
            href="/check-ai"
            style={{ display: 'inline-block', marginTop: 12, fontSize: '0.85rem', color: 'var(--accent-orange)', fontWeight: 600, textDecoration: 'none' }}
          >
            Already asked ChatGPT about this? Verify its answer against real OEM data →
          </a>
```
This is the acquisition-funnel intercept point: a user comparing against another AI is exactly who should see `/check-ai`, at the moment they're evaluating RAPP's diagnosis.

---

## Do NOT touch

- Any `data-testid` (all frozen). These are new `<a>` elements with no testid.
- The `linkStyle` object shape, the `<body>` classes, or any existing links.
- The `/hub` and `/check-ai` pages themselves — they already work; you're only linking to them.

---

## Verification

1. **Reachable by click** — from a fresh load of `/`, confirm both `/hub` (via "Guides") and `/check-ai` (via "Check My AI Answer") open by clicking, not by typing a URL.
2. **Contextual link** — on `/results`, the "Already asked ChatGPT…" link appears under the free diagnosis summary and navigates to `/check-ai`.
3. **E2E still green** — the frozen suite must pass (these are additive links, no testid changes):
   ```bash
   cd frontend && ./node_modules/.bin/next build
   # then, against a running mock or real app:
   FRONTEND_URL=http://localhost:3000 npx playwright test --project=chromium
   ```

---

## Definition of Done

- [ ] `/hub` ("Guides") and `/check-ai` ("Check My AI Answer") links added to `HeaderAuthLink.tsx`, always visible
- [ ] Contextual `/check-ai` link added under the free-diagnosis summary on `/results`
- [ ] Both destinations reachable by click from a fresh page
- [ ] `next build` passes; E2E suite still green
- [ ] Committed: `feat(nav): Block 2.3 wire /hub and /check-ai into navigation`
- [ ] `imp_part_2.md` §1 tracker row 2.3 → `✅ Done`; session logged in §5
