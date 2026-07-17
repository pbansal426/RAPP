# Block 4.6 — Theme/Design Coherence Pass

**Parent plan**: [`../imp_part_2.md`](../imp_part_2.md) Section 5 Stage 4 Block 4.6
**Model specced**: Sonnet 5 | **Thinking specced**: Medium
**Status**: ⬜ Not started
**Verified against codebase**: 2026-07-16 (after Blocks 1.1–1.3, 3.2 landed; assumes 4.1–4.5 land first per this doc's sequential-execution convention)

---

## 1. Goal

A full page-by-page "trust vibes" audit (requested explicitly to make the app read as an authentic, trustable authority handling someone's vehicle, not a gimmicky sales funnel) found five categories of visual/copy issues on the app's two highest-stakes screens (`/results`, the paywall; `/repair`, the actual procedure) and their shared components. None of these are functional bugs in the sense of broken behavior — the app works — but each one reads as unfinished, informal, or leaking internals in a way that undercuts the "professional shop, not a hobby project" impression the app should give.

---

## 2. Exactly what to change

### Part A — Light-mode token pass (the main effort)

**Why this matters**: `frontend/src/app/globals.css` defines a complete theme-token system — `--text-primary`, `--text-secondary`, `--bg-surface`, `--bg-elevated`, `--overlay-04/05/08/12`, `--accent-orange/green/red/blue/yellow` — that resolves to different actual colors depending on `[data-theme="dark"]` vs `[data-theme="light"]` (see the token block at the top of `globals.css`, lines 9-92). `ThemeToggle.tsx` lets a signed-in user (or the OS "System" preference) switch to light mode. But `results/page.tsx`, `repair/page.tsx`, and `results/PartsPurchasePlan.tsx` bypass this system extensively with **inline hardcoded hex/rgba color values** instead of the `var(--...)` tokens. A direct count (2026-07-16) found:

- `results/page.tsx`: 15× `#fff`, 8× `#f1f5f9`, 8× `#4ade80`, 5× `#94a3b8`, plus 25+ distinct one-off `rgba(255,255,255,0.0X)` overlays.
- `repair/page.tsx`: 6× `#fff`, 4× `#4ade80`, plus a dozen distinct `rgba(...)` overlays.
- `PartsPurchasePlan.tsx`: smaller but same pattern (`rgba(255,255,255,0.08)`, `#4ade80`, `#60a5fa`, etc.).

Because these are hardcoded rather than theme-reactive, a user who switches to light mode sees large sections of these two pages still rendering **dark-mode-designed colors** (near-white text, dark translucent card fills) sitting on top of the now-light `--bg-primary` body — producing genuinely broken, hard-to-read contrast on exactly the two screens where the user is deciding whether to pay and then following safety-relevant repair steps.

**Decision rule — apply this to every inline color in the three files above**:

| Category | Rule |
|---|---|
| Text/heading/value color sitting on a `.card`/page surface | **Tokenize.** These surfaces flip color between themes; hardcoded text color on them breaks contrast in one theme or the other. |
| Background/border color of a card, panel, or hairline divider | **Tokenize.** Same reasoning. |
| Text or icon color on an element whose own background is a **fixed, theme-invariant color** (e.g. white text on the permanently-orange `.btn-primary` gradient button, or on a solid colored badge/pill that doesn't change with theme) | **Leave alone.** Tokenizing here would be wrong — the fixed background needs that specific contrast-safe color regardless of theme. |
| Colors already coming from `.border-red-500` / `.bg-red-950` / `.text-red-500` (the frozen safety-banner utility classes) | **Leave alone** — out of scope, these are class-based and already handled per `CLAUDE.md`'s frozen-contract note. |

**Token mapping table** (use for every value that the decision rule above says to tokenize):

| Hardcoded value found in these files | Replace with |
|---|---|
| `#fff`, `#ffffff` (as text color, not on a fixed-color button/badge) | `var(--text-primary)` |
| `#f1f5f9`, `#e2e8f0`, `#cbd5e1` (as text color) | `var(--text-primary)` for headings/values, `var(--text-secondary)` for secondary/meta text — judge by context |
| `#94a3b8` | `var(--text-secondary)` |
| `#4ade80` (green success text/icon on a surface) | `var(--accent-green)` |
| `#f87171`, `#ef4444`, `#EF4444`, `#dc2626` (red/danger text on a surface) | `var(--accent-red)` |
| `#3b82f6`, `#60a5fa` (blue info text on a surface) | `var(--accent-blue)` |
| `#fbbf24`, `#F59E0B` (yellow, on a surface) | `var(--accent-yellow)` |
| `rgba(255,255,255,0.0X)` used as a card/section background or hairline border | matching `var(--overlay-04\|05\|08\|12)` (pick the closest alpha already defined), or `var(--bg-elevated)`/`var(--bg-surface)` if it should read as a solid panel rather than a subtle overlay |
| `rgba(15, 23, 42, ...)`, `rgba(30, 41, 59, ...)` used as a background fill | `var(--bg-surface)` or `var(--bg-elevated)` (pick whichever the surrounding non-hardcoded cards in the same file already use for a visually equivalent panel) |

**Process**: go file-by-file (`results/page.tsx`, `repair/page.tsx`, `results/PartsPurchasePlan.tsx`). For each inline `style={{ ... }}` containing a hex or `rgba(...)` literal, apply the decision rule, then the mapping table. Where a value is genuinely ambiguous (e.g. it's unclear whether a given translucent panel should read as `--bg-surface` vs `--bg-elevated`), match whatever the nearest already-token-based `.card` in the same file uses, for visual consistency within the page.

**Do not touch in this pass** (explicitly out of scope, handled elsewhere):
- `results/page.tsx` line 609's `color: 'rgba(255, 255, 255, 0.85)'` — Block 4.5 changes the *text* of this exact `<span>`; tokenize its color here in this block, after confirming 4.5's text change is already in place (or coordinate if running before it — the token fix applies regardless of the text content).
- Anything inside `.border-red-500`/`.bg-red-950`/`.text-red-500` class usages (safety banners) — frozen contract, class-based, not inline.

---

### Part B — Remove emoji (3 spots)

**1. `frontend/src/app/repair/success/page.tsx`, line 26**

Current:
```tsx
<p style={{ fontSize: '3rem', marginBottom: 16 }}>✅</p>
```

Replace with (add `import { CheckCircleIcon } from '@/app/sharedIcons';` at the top of the file if not already imported — check first, this file currently has no `sharedIcons` import):
```tsx
<div style={{ marginBottom: 16, display: 'flex', justifyContent: 'center' }}>
  <CheckCircleIcon size={48} style={{ color: 'var(--accent-green)' }} />
</div>
```

**2. `frontend/src/app/results/page.tsx`, line 946**

Current:
```tsx
<h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff', marginBottom: 8 }}>⭐ Annual Pass</h3>
```

Replace with (this file already imports `StarIcon` from `@/app/sharedIcons` — confirm before assuming, it's used elsewhere on this page for the premium-paywall badge):
```tsx
<h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
  <StarIcon size={18} style={{ color: 'var(--accent-yellow)' }} /><span>Annual Pass</span>
</h3>
```
(This also folds in the Part A token fix for this line's `color: '#fff'` — don't double-handle it separately in Part A.)

**3. `frontend/src/app/repair/ChatPanel.tsx`, line 148**

Current:
```tsx
⚠️ <strong>Live AI quota reached for this job (5/5).</strong> Further questions are answered using local high-speed OEM torque, tool, and safety specification lookups.
```

Replace with (add `import { AlertTriangleIcon } from '@/app/sharedIcons';` — this file currently imports only `AssistantIcon` from `sharedIcons`):
```tsx
<span style={{ display: 'inline-flex', alignItems: 'flex-start', gap: 6 }}>
  <AlertTriangleIcon size={14} style={{ flexShrink: 0, marginTop: 2 }} />
  <span><strong>Live AI quota reached for this job (5/5).</strong> Further questions are answered using local high-speed OEM torque, tool, and safety specification lookups.</span>
</span>
```

---

### Part C — Remaining native dialog + alert()

**4. `frontend/src/app/repair/page.tsx`, line 157 (`handleSwitchSkillLevel`)**

Current:
```tsx
const confirmed = window.confirm(
  `Switching to "${newSkill}" mode will regenerate your procedure steps tailored to this skill level. Continue?`
);
if (confirmed && vin) {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(`rapp_repair_${vin}`);
    localStorage.removeItem(`rapp_repair_checked_${vin}`);
  }
  const sessionId = localStorage.getItem(`rapp_unlocked_${vin}`) || '';
  const tools = JSON.parse(localStorage.getItem('rapp_tools') ?? '[]') as string[];
  generateAndCache(vin, symptoms, tools, sessionId, vinData, newSkill);
}
```

**Coordination note**: Block 4.2 (see `part_2_blocks/block_4_2.md`) independently converts the *other* `window.confirm()` in this same file — inside `startOver` (line 224) — to an inline confirmation banner. **Check whether Block 4.2 has already landed before starting this item:**
- **If 4.2 has already landed**: it will have introduced some form of inline-banner state/UI for `startOver`'s confirmation. Reuse that same pattern/component for this skill-switch confirmation instead of inventing a second, visually-different banner — e.g. generalize whatever state 4.2 added (such as a `pendingConfirmAction: 'startOver' | null`) to also accept `'switchSkill'`, and parameterize the banner's message/confirm-callback instead of duplicating the whole banner markup.
- **If 4.2 has not landed yet**: implement a small local `pendingSkillSwitch: string | null` state (holding the target skill level awaiting confirmation) and an inline banner in the same visual style as this page's other inline UI (e.g. matching the `showCompletionSurvey` modal's button-pair styling):
  ```tsx
  const [pendingSkillSwitch, setPendingSkillSwitch] = useState<string | null>(null);
  ```
  Replace the `window.confirm(...)` call with `setPendingSkillSwitch(newSkill)` (deferring the actual switch), and render a small inline banner near the skill-level selector reading `Switching to "{pendingSkillSwitch}" mode regenerates your steps.` with **Confirm**/**Cancel** buttons that either proceed with the original `if (confirmed && vin) { ... }` body (on Confirm) or just clear `pendingSkillSwitch` (on Cancel). Leave a comment `// TODO: consolidate with Block 4.2's startOver confirmation banner if it lands after this` so whichever block merges second unifies the two.

**5. `frontend/src/app/results/page.tsx`, line 258 (`handlePay`'s catch block)**

Current:
```tsx
} catch {
  setPayLoading(false);
  alert('Payment service unavailable. Please try again.');
}
```

Add a dedicated state near the other page-level state declarations (do **not** reuse the existing `error` state — that one is already used for the diagnosis-load failure earlier in this file, and both failure modes could in principle need to display independently):
```tsx
const [payError, setPayError] = useState<string | null>(null);
```
Replace the catch block:
```tsx
} catch {
  setPayLoading(false);
  setPayError('Payment service unavailable. Please try again.');
}
```
Then render it immediately above the `<div className="premium-paywall sticky-mobile-cta" ...>` block (search for that exact string to find the insertion point):
```tsx
{payError && (
  <p role="alert" style={{ color: 'var(--accent-red)', fontSize: '0.875rem', textAlign: 'center', marginBottom: 12 }}>
    {payError}
  </p>
)}
```

---

### Part D — Drop internal jargon

**6. `frontend/src/app/repair/page.tsx`, line 404**

Current:
```tsx
<p className="text-muted">Retrieving vector-verified repair procedures from ChromaDB…</p>
```

Replace with:
```tsx
<p className="text-muted">Retrieving verified repair procedures from your vehicle's service data…</p>
```

---

## 3. Verification

```bash
grep -oE "#[0-9a-fA-F]{3,6}" frontend/src/app/results/page.tsx frontend/src/app/repair/page.tsx frontend/src/app/results/PartsPurchasePlan.tsx | grep -v "var(--"
```
Manually confirm every remaining match is an explicitly-documented "leave alone" exception from Part A's decision rule (fixed-background buttons/badges, or the frozen safety-banner classes) — not a stray surface color that should have been tokenized.

```bash
grep -rn "✅\|⭐\|⚠️" frontend/src/app/repair/success/page.tsx frontend/src/app/results/page.tsx frontend/src/app/repair/ChatPanel.tsx
# Expect: no output

grep -n "window.confirm\|alert(" frontend/src/app/repair/page.tsx frontend/src/app/results/page.tsx
# Expect: no output in either file (both native-dialog instances in each converted)

grep -n "ChromaDB" frontend/src/app/repair/page.tsx
# Expect: no output

cd frontend && ./node_modules/.bin/next build
```
**Expected**: `✓ Compiled successfully`, zero TS/ESLint errors.

**Manual check**: with a populated `rapp_vin`/`rapp_vin_data`/`rapp_symptoms` localStorage state, load `/results` and `/repair`, then toggle to light mode via `ThemeToggle`. Visually confirm there are no remaining dark-card-text-on-light-page or illegible-contrast regions on either page. Confirm the annual-pass heading, the payment-success page, and the chat quota banner all render icons instead of emoji. Trigger a payment failure (e.g. temporarily stop the backend) and confirm the error renders as an inline banner, not a browser `alert()` popup.
