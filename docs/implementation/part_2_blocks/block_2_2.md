# Block 2.2 — Surface the referral program in the UI

> **Model**: Gemini Flash 3.5 · **Thinking**: Medium · **Stage**: 2 (Measurement & Growth) · **Status**: ⬜ Not started
> **Parent**: [`../imp_part_2.md`](../imp_part_2.md) §2.2

---

## TL;DR

The referral program is **fully real on the backend** (codes generated on signup, both parties credited, `referral_code`/`referral_credits` returned by `GET /api/auth/me`) but **completely invisible in the UI** — `grep referral frontend/src` returns nothing. This block surfaces it: type the fields into the auth layer, add a share card to `/settings`, capture `?ref=` codes into the signup flow, and add a post-purchase share prompt.

---

## ⚠️ Corrections vs. `imp_part_2.md` — READ THESE FIRST

The parent plan predates the migration to **magic-link auth**. Two of its four instructions target files that no longer work the way it assumes:

1. **There is no password "signup request body."** Auth is magic-link: account creation happens the first time an email hits `POST /api/auth/request-link` (via `requestMagicLink()` in `lib/auth.ts`). `frontend/src/app/signup/page.tsx` is now just a **redirect stub** that forwards to `/signin`. The real email-entry form is **`frontend/src/app/signin/page.tsx`**. So the `?ref=` code must flow through `requestMagicLink` → `/api/auth/request-link`'s already-existing `referral_code` field (`backend/schemas.py:179`). Corrected instructions in step 3 below.
2. **`repair/success/page.tsx` is a transient redirect** — it stores the unlock token and immediately `router.replace('/repair')`. A user never dwells on it, so a referral callout there is invisible. Place the post-purchase callout on **`/repair`** instead (exact anchor in step 4 below).

Everything else (backend fields, the settings card) is accurate.

---

## Backend facts you can rely on (no backend change in this block)

- `POST /api/auth/request-link` already accepts `referral_code: str | None` (`schemas.py:179`) and, on first-time signup, credits both referrer and new user by 1 (`routers/auth.py:128-157`).
- `GET /api/auth/me` (`UserResponse`) already returns `referral_code: str` and `referral_credits: int` (`schemas.py:203-204`; built in `routers/auth.py:101-102`).
- An invalid/typo'd code does **not** block signup — it's just ignored (`routers/auth.py:136-139`). So you never need to validate the code client-side.
- (Context only) credits are spendable via `POST /api/auth/redeem-referral-credit` for a free single-incident unlock. This block does **not** build redemption UI — just visibility.

---

## Step 1 — Type the referral fields into `frontend/src/lib/auth.ts`

Both interfaces currently omit these fields.

**`AuthUser` interface (lines 8-16)** — add camelCase fields:
```ts
export interface AuthUser {
  uid: string;
  email: string;
  displayName: string | null;
  subscriptionStatus: string;
  skillLevel: string;
  completedJobsCount: number;
  skillBadges: string[];
  referralCode: string;
  referralCredits: number;
}
```

**`UserResponse` interface (lines 18-26)** — add snake_case fields matching the raw API:
```ts
interface UserResponse {
  id: string;
  email: string;
  display_name: string | null;
  subscription_status: string;
  skill_level?: string;
  completed_jobs_count?: number;
  skill_badges?: string[];
  referral_code?: string;
  referral_credits?: number;
}
```

**`toAuthUser` mapping (lines 33-43)** — add the two mappings:
```ts
function toAuthUser(user: UserResponse): AuthUser {
  return {
    uid: user.id,
    email: user.email,
    displayName: user.display_name,
    subscriptionStatus: user.subscription_status || 'free',
    skillLevel: user.skill_level || 'Beginner',
    completedJobsCount: user.completed_jobs_count || 0,
    skillBadges: user.skill_badges || [],
    referralCode: user.referral_code || '',
    referralCredits: user.referral_credits || 0,
  };
}
```

---

## Step 2 — Add a referral share card to `frontend/src/app/settings/page.tsx`

The page already renders `.card` blocks (Account at line 71, the display-name form at line 78, Session at line 98). Add a new `.card` — insert it **between the display-name form (ends line 96) and the Session card (line 98)**. `user` is guaranteed non-null here (the component early-returns a spinner while `loading || !user`).

```tsx
      <div className="card">
        <p className="card-label">Invite Friends, Earn Credit</p>
        <p className="text-muted text-sm" style={{ marginBottom: 10 }}>
          Share your link. When a friend signs up with it, you both get 1 free single-guide credit.
        </p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <input
            className="input"
            type="text"
            readOnly
            value={`${typeof window !== 'undefined' ? window.location.origin : ''}/signup?ref=${user.referralCode}`}
            onFocus={(e) => e.currentTarget.select()}
            style={{ flex: '1 1 260px', minWidth: 0 }}
          />
          <button
            type="button"
            className="btn btn-secondary"
            style={{ width: 'auto', padding: '0 18px' }}
            onClick={() => {
              navigator.clipboard.writeText(
                `${window.location.origin}/signup?ref=${user.referralCode}`
              );
            }}
          >
            Copy Link
          </button>
        </div>
        <p className="text-muted text-sm" style={{ marginTop: 8 }}>
          You&apos;ve earned {user.referralCredits} credit{user.referralCredits === 1 ? '' : 's'} so far.
        </p>
      </div>
```

---

## Step 3 — Capture `?ref=` and forward it through signup (magic-link flow)

The share link is `/signup?ref=CODE`. `/signup` redirects to `/signin`, so the `ref` must survive that hop and then be passed to `requestMagicLink`.

### 3a — `requestMagicLink` gains a `referralCode` param — `frontend/src/lib/auth.ts` (lines 64-73)

**Current**:
```ts
export async function requestMagicLink(
  email: string,
  displayName?: string
): Promise<{ message: string; magicLink: string | null }> {
  const res = await api.post<{ message: string; magic_link: string | null }>(
    '/api/auth/request-link',
    { email, display_name: displayName ?? null }
  );
  return { message: res.message, magicLink: res.magic_link };
}
```
**Change**:
```ts
export async function requestMagicLink(
  email: string,
  displayName?: string,
  referralCode?: string
): Promise<{ message: string; magicLink: string | null }> {
  const res = await api.post<{ message: string; magic_link: string | null }>(
    '/api/auth/request-link',
    { email, display_name: displayName ?? null, referral_code: referralCode ?? null }
  );
  return { message: res.message, magicLink: res.magic_link };
}
```

### 3b — `/signup` redirect stub preserves `ref` — `frontend/src/app/signup/page.tsx` (lines 13-16)

**Current**:
```tsx
  useEffect(() => {
    const next = searchParams.get('next');
    router.replace(next ? `/signin?next=${encodeURIComponent(next)}` : '/signin');
  }, [router, searchParams]);
```
**Change** — carry `ref` through the redirect:
```tsx
  useEffect(() => {
    const next = searchParams.get('next');
    const ref = searchParams.get('ref');
    const params = new URLSearchParams();
    if (next) params.set('next', next);
    if (ref) params.set('ref', ref);
    const qs = params.toString();
    router.replace(qs ? `/signin?${qs}` : '/signin');
  }, [router, searchParams]);
```

### 3c — `/signin` reads `ref` and passes it — `frontend/src/app/signin/page.tsx`

In `SignInForm`, `searchParams` already exists (line 10). The `next` const is read at line 17 — add a sibling:
```tsx
  const next = searchParams.get('next');
  const ref = searchParams.get('ref');
```
Then in `handleSubmit` (line 25), pass `ref` as the third arg (email form has no name field, so pass `undefined` for displayName):
```tsx
      const res = await requestMagicLink(email.trim(), undefined, ref ?? undefined);
```

> The garage-save form on `/results` also calls `requestMagicLink` (`handleGarageSignUp`), but a referred *new* user arrives via `/signup?ref=` → `/signin`, not that form, so no change is needed there for this block.

---

## Step 4 — Post-purchase share prompt on `/repair` (corrected location)

Place a dismissible one-line callout at the top of the unlocked guide. `frontend/src/app/repair/page.tsx` returns `<main className="repair-shell">` (line 352) → `<div className="repair-main">` (line 353, the left content column) → back-button div → `<header className="page-header">` (line 377). Insert the callout **as the first child inside `.repair-main`, right after line 353's opening `<div className="repair-main">`**:

```tsx
      <div className="repair-main">
        <ReferralNudge />
        <div style={{ display: 'flex', width: '100%', justifyContent: 'flex-start', marginBottom: 12 }}>
          {/* existing back button ... */}
```

Add a tiny local dismissible component near the top of the file (below the imports, above the page component) — keeps it self-contained and avoids new files:
```tsx
function ReferralNudge() {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
      padding: '10px 14px', marginBottom: 12, borderRadius: 8,
      background: 'rgba(249,115,22,0.08)', border: '1px solid rgba(249,115,22,0.25)',
      fontSize: '0.85rem',
    }}>
      <span>Know someone who&apos;d find this useful? <a href="/settings" style={{ color: 'var(--accent-orange)', fontWeight: 700 }}>Share your referral link</a> and you&apos;ll both get credit.</span>
      <button type="button" onClick={() => setDismissed(true)} aria-label="Dismiss"
        style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '1.1rem', lineHeight: 1 }}>×</button>
    </div>
  );
}
```
> `useState` is already imported in `repair/page.tsx`. This routes to the settings card from Step 2 rather than duplicating the copy-link UI.

---

## Do NOT touch

- Any backend file — the backend already does everything needed.
- The garage-save form on `/results` (out of scope for this block).
- `data-testid`s or localStorage keys.

---

## Verification

1. **Build passes**: `cd frontend && ./node_modules/.bin/next build`.
2. **End-to-end referral credit** — with the app running:
   - Sign in as user A, open `/settings`, copy the link (`/signup?ref=<A's code>`).
   - In a fresh browser/incognito, open that link → it redirects to `/signin` **with `?ref=` preserved in the URL** → enter user B's email → complete magic-link sign-in.
   - Call `GET /api/auth/me` for both accounts (or reload `/settings`): both A and B should show `referral_credits` incremented by 1.
3. **Copy button** copies the full URL (not just the bare code) — paste-test it.
4. **`/repair` nudge** renders at the top of the unlocked guide and dismisses on ×.

---

## Definition of Done

- [ ] `AuthUser`/`UserResponse`/`toAuthUser` updated with referral fields
- [ ] Settings share card renders code/link + credit count; copy button works
- [ ] `requestMagicLink` forwards `referral_code`; `/signup` preserves `ref`; `/signin` reads and passes it
- [ ] Referred signup credits **both** parties (verified via `/api/auth/me`)
- [ ] `/repair` referral nudge added (dismissible, links to `/settings`)
- [ ] `next build` passes clean
- [ ] Committed: `feat(referral): Block 2.2 surface referral program in UI`
- [ ] `imp_part_2.md` §1 tracker row 2.2 → `✅ Done`; session logged in §5 (note the two magic-link corrections)
