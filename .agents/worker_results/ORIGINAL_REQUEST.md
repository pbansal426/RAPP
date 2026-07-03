## 2026-07-03T07:08:30Z
You are worker_results, a teamwork_preview_worker subagent.
Your working directory is /Users/prathambansal/Dev/RAPP/.agents/worker_results/.
Your task is to implement Milestone 4: Affiliate Parts Dashboard & Garage Sign-up (R4) for RAPP Phase 2 Redesign.

Follow these instructions exactly:
1. Curated Affiliate Cards (PartsPurchasePlan.tsx):
   - Modify `frontend/src/app/results/PartsPurchasePlan.tsx` to group and render each recommended part/tool with exactly 2 structured options:
     - For standard auto parts: Option 1: "OEM Factory Part" and Option 2: "Premium Aftermarket".
     - For oil/fluid services (if part name contains "oil" or "fluid" or "filter"): Option 1: "Premium Synthetic Oil" and Option 2: "Standard Conventional Oil".
     - Each option must show the brand, estimated price, a clear technical rationale, and an affiliate purchase link.
     - Note: The backend unit tests verify that the backend API returns 3 tiers, so do NOT change `backend/pricing.py` or the backend schema. Filter or reshape the options array client-side inside `PartsPurchasePlan.tsx`. Pick the 'OEM' tier from the backend as the first option, and the 'Aftermarket / Budget' tier as the second option, and adapt their titles and contents (or generate them dynamically on the client side based on the backend data).

2. 3-Column Price Comparison Table (results/page.tsx):
   - Modify the price table in `frontend/src/app/results/page.tsx` to display exactly 3 columns:
     - Column 1: Repair Method (Dealership / Pro Shop, Independent Auto Shop, RAPP Guided DIY)
     - Column 2: Estimated Cost (Dealership range, Independent range, and RAPP DIY total which is verified parts total + $4.00 guide fee)
     - Column 3: Value & Details (technical markups, timeframes, or convenience details)
   - Ensure the table styling is high-contrast, slate-navy/charcoal themed, and aligns with the Deep Industrial Navy design system.

3. Post-Repair Garage Vault Sign-Up:
   - On the results page (`frontend/src/app/results/page.tsx`), add a prominent "Save to My Garage & Keep Guide Forever" registration section (or modal) allowing users to register a Firebase account to archive their vehicle profile, diagnostic guide, and payment preferences.
   - You can place this section below the price table or as part of the paywall container. It should be highly visible and contain name (optional), email, and password input fields.
   - When Firebase Auth is initialized and credentials are configured, clicking "Save to My Garage" must register the user, save the current vehicle diagnostics/symptoms to Cloud Firestore using the `saveRepair` helper in `src/lib/repairs.ts`, and display a success message.
   - Make sure that when Firebase is unconfigured, it fails/hides gracefully or shows a message, matching the behavior of `SaveGuidePrompt.tsx`.

4. Verification:
   - Run `cd frontend && pnpm build` to compile the app and check for errors.
   - Run `bash tests/verify_tests.sh` and pytest unit tests to ensure that the entire project compiles and all E2E / unit tests pass cleanly.
   - Write a detailed handoff report (`handoff.md`) in your working directory and notify me when complete.

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
