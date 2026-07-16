# Block 1.4 — Harden production email deliverability (fail loud, not silent)

> **Model**: Sonnet 5 · **Thinking**: Low · **Stage**: 1 (Trust & Correctness) · **Status**: ⬜ Not started
> **Parent**: [`../imp_part_2.md`](../imp_part_2.md) §1.4

---

## TL;DR

One backend edit (extend an existing startup validator) plus one **human-only** ops task you must flag, not attempt. Today a staging/production deploy can silently boot with Resend's *sandbox* sender (`onboarding@resend.dev`), which only delivers to the Resend account owner's own inbox — meaning **every real user's magic-link sign-in email would silently fail**. The code fix makes the process refuse to start in that misconfiguration, so the failure is loud at boot instead of invisible at runtime.

---

## Context you need

- `backend/core/config.py` defines `Settings`. It already has a `model_validator(mode="after")` named `_require_resend_key_outside_dev` (currently lines 91-99) that raises on startup if `RESEND_API_KEY` is missing in a staging/production environment.
- `EMAIL_REQUIRED_ENVIRONMENTS = frozenset({"staging", "production"})` (line 15) is the set of environments where email must really deliver.
- `email_from` defaults to `"RAPP <onboarding@resend.dev>"` (line 56) — the sandbox address.
- The auth router (`backend/routers/auth.py::request_link`) already fails *closed* in every way code can control (never leaks the link outside dev, never lets a caller distinguish accounts). The only remaining gap is the sandbox `email_from` slipping into a deployed env — which is what this block closes.

---

## ⚠️ Corrections vs. `imp_part_2.md`

None. The validator is at lines 91-99 and `email_from` at line 56, exactly as the parent plan states. The parent plan's full replacement block is correct; it's reproduced below verbatim so you don't have to reconstruct it.

---

## Part 1 — Code fix (this is what you implement)

### `backend/core/config.py` — extend the existing validator (lines 91-99)

**Current**:
```python
    @model_validator(mode="after")
    def _require_resend_key_outside_dev(self) -> "Settings":
        if self.environment in EMAIL_REQUIRED_ENVIRONMENTS and not self.resend_api_key:
            raise ValueError(
                f"RESEND_API_KEY must be set when ENVIRONMENT={self.environment!r} -- "
                "magic-link auth is not allowed to fall back to leaking the sign-in "
                "link in the API response outside development/test."
            )
        return self
```

**Change** — restructure so both the missing-key check *and* the sandbox-sender check live in the same validator (do **not** add a second validator — keep the fail-fast logic in one place):
```python
    @model_validator(mode="after")
    def _require_resend_key_outside_dev(self) -> "Settings":
        if self.environment in EMAIL_REQUIRED_ENVIRONMENTS:
            if not self.resend_api_key:
                raise ValueError(
                    f"RESEND_API_KEY must be set when ENVIRONMENT={self.environment!r} -- "
                    "magic-link auth is not allowed to fall back to leaking the sign-in "
                    "link in the API response outside development/test."
                )
            if "resend.dev" in self.email_from:
                raise ValueError(
                    f"email_from is still Resend's sandbox address ({self.email_from!r}) "
                    f"in ENVIRONMENT={self.environment!r} -- Resend's sandbox sender only "
                    "delivers to the account owner's own inbox, so every real user's "
                    "magic-link email would silently fail. Verify a custom domain with "
                    "Resend and set EMAIL_FROM to an address on that domain before deploying."
                )
        return self
```

That is the only code change.

---

## Part 2 — Human-only ops task (FLAG IT, DO NOT ATTEMPT)

A human must verify a real owned domain with Resend (DNS TXT/CNAME records in Resend's dashboard) and set `EMAIL_FROM` to an address on that verified domain in the deployed environment's actual env vars. **No AI agent can complete this** — it requires DNS control over a real domain.

**Action for you**: write this clearly in your `imp_part_2.md` §5 session-log entry as an outstanding human task. Do not mark Block 1.4 as blocked on it — the code fix is the deliverable; this note is a handoff to the human. The code fix exists precisely so a misconfigured deploy fails loudly at startup instead of shipping broken auth.

---

## Do NOT touch

- `backend/routers/auth.py` — it already fails closed correctly; no change here.
- The default value of `email_from` itself (line 56) — it stays the sandbox address, because that's the correct default for local dev. The validator only rejects it in `staging`/`production`.
- `EMAIL_REQUIRED_ENVIRONMENTS` — unchanged.

---

## Verification

1. **Existing tests still pass** (the new check only fires for `staging`/`production`, which local/test runs never set):
   ```bash
   uv run pytest tests/unit/ -v
   uv run ruff check backend/ && uv run black --check backend/ && uv run mypy backend/
   ```
2. **The new guard actually fires** — confirm a production config with the default sender raises:
   ```bash
   ENVIRONMENT=production RESEND_API_KEY=test-key uv run python -c "from backend.core.config import Settings; Settings()"
   ```
   Must raise `ValueError` mentioning `resend.dev` / sandbox. (Without this block's change, it would start silently.)
3. **The guard does NOT over-fire** — a proper production config starts fine:
   ```bash
   ENVIRONMENT=production RESEND_API_KEY=test-key EMAIL_FROM="RAPP <hello@example.com>" uv run python -c "from backend.core.config import Settings; Settings(); print('OK')"
   ```
   Must print `OK`.

---

## Definition of Done

- [ ] Validator in `config.py` extended (single validator, both checks)
- [ ] `pytest`, ruff, black, mypy all pass
- [ ] Production+sandbox config raises `ValueError`; production+real-domain config starts clean (both verified via the one-liners above)
- [ ] Human ops task (verify Resend domain + set `EMAIL_FROM`) written into the §5 session log as an outstanding handoff
- [ ] Committed: `fix(config): Block 1.4 refuse to boot with Resend sandbox sender in prod`
- [ ] `imp_part_2.md` §1 tracker row 1.4 → `✅ Done`; session logged in §5
