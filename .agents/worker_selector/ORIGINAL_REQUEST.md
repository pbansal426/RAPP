## 2026-07-03T06:58:05Z

You are worker_selector, a teamwork_preview_worker subagent.
Your working directory is /Users/prathambansal/Dev/RAPP/.agents/worker_selector/.
Your task is to implement Milestone 2: Design System & 4-Step Selector (R1, R2) for RAPP Phase 2 Redesign.

Follow these instructions exactly:
1. Design System (R1):
   - Modify `frontend/src/app/globals.css` to update the CSS custom properties in `:root`:
     - Set `--bg-primary` to `#0F172A` (Deep Slate Navy background).
     - Set `--border` to `rgba(255, 255, 255, 0.08)` (subtle 1px borders).
     - Set `--bg-surface` to `#1E293B` or another charcoal color for cards.
     - Set `--bg-elevated` to a matching charcoal shade like `#1E293B` or `#334155`.
     - Ensure `--accent-orange` is `#F97316` (safety orange).
   - Ensure the typography feels crisp and engineered, and safety orange is consistently used for highlights, warning banners, and primary CTAs.

2. Cascading 4-Step Vehicle Selector & Auto-Lock (R2):
   - Update `frontend/src/app/page.tsx`:
     - Add a Trim select element with `data-testid="select-trim"`.
     - The selector flow must be: select Year -> select Make -> select Model -> select Trim.
     - The Trim selector should only be enabled once a Model is selected.
     - To ensure that the existing E2E test `Step 5: Year/Make/Model Cascading Dropdowns & Submit` passes without changes, make sure that selecting a model automatically selects a default trim (e.g., "Base" or the first available trim) or that the Trim selector does not block the submit button from becoming enabled. When Make/Model is Honda Accord, selecting ACCORD should unlock the submit button immediately (with Trim defaulted to "Base" or similar).
     - If the selected vehicle is a model/trim with a single valid powertrain (specifically: "2010 Toyota Corolla S" or "2015 Highlander XLE"), you must automatically populate and lock:
       - Powertrain (set to "Gasoline" and disable the Powertrain select `data-testid="select-powertrain"`)
       - Engine Layout (set to "1.8L I4" for 2010 Toyota Corolla S, and "3.5L V6" for 2015 Highlander XLE, and disable the `data-testid="engine-detail"` input field)
       - Drive Type: Add a Drive Type select element (`data-testid="select-drive"`) on the homepage, populated with standard options (FWD, RWD, AWD, 4WD). For 2010 Toyota Corolla S, set to "FWD" and disable it. For 2015 Highlander XLE, set to "AWD" and disable it. For other vehicles, keep it enabled.
     - When submitting, build the synthetic VIN correctly and write the vehicle details (including `trim` and `drive_type`) into `localStorage` as `rapp_vin` and `rapp_vin_data`.
     - Map the tools in `ToolSelector.tsx` so that their IDs match the expectations of `results/page.tsx` and the E2E tests (`tool-hand-tools`, `tool-jack-stands`, `tool-multimeter`).

3. Verification:
   - Run `cd frontend && pnpm build` (or similar build command) to verify that the Next.js app compiles successfully.
   - Run backend unit tests and E2E verification tests (`tests/verify_tests.sh`) to ensure there are no regressions and all tests pass.
   - Report the path to your handoff report (`handoff.md`) and a summary of changes.

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
