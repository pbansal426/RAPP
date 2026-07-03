# Original User Request

## Follow-up — 2026-07-03T06:54:03Z

Execute Phase 2 of the RAPP (Real Automotive Professional Platform) redesign, transforming the web application frontend into a trustworthy, professional automotive engineering platform with a Deep Industrial Navy aesthetic, cascading vehicle selector, isolated OBD-II diagnostic tooling, and affiliate garage vault.

Working directory: /Users/prathambansal/Dev/RAPP
Integrity mode: development

## Requirements

### R1. Deep Industrial Navy Design System
Transform the application visual design across `frontend/src/app/globals.css` and all layouts from hypermodern/immature to a trustworthy, high-contrast automotive engineering aesthetic using Deep Slate Navy (`#0F172A`) backgrounds, charcoal cards with subtle 1px borders (`rgba(255, 255, 255, 0.08)`), crisp engineered typography, and safety orange/amber (`#F97316`) accents.

### R2. Cascading 4-Step Vehicle Selector & Auto-Lock Specs
Upgrade the homepage vehicle identification flow (`frontend/src/app/page.tsx`) to a 4-step cascading selector (Year → Make → Model → Trim). When selecting a model/trim with a single valid powertrain (such as 2010 Toyota Corolla S or 2015 Highlander XLE), automatically populate and lock the Powertrain (Gasoline), Engine Layout, and Drive Type without requiring manual user selection.

### R3. Automotive Diagnostic Panel (Diagnose Page)
Enhance `frontend/src/app/diagnose/*` with:
- **Brand Logo Badge (`VehicleHeroCard.tsx`)**: Display a prominent, clean vehicle brand vector/SVG badge next to large bold model identification text.
- **OBD-II Picker Isolation (`ObdCodePicker.tsx` & `page.tsx`)**: Selecting OBD-II codes must populate distinct, removable diagnostic tags/chips above/below the textarea rather than inserting text into the user problem input field.
- **HEIC Photo Previews (`page.tsx`)**: Render attached dashboard/engine photo previews reliably (supporting HEIC/HEIF formatting or fallback previews), showing up to 3 thumbnails and collapsing additional photos behind a toggle.
- **Searchable Tool Inventory (`ToolSelector.tsx`)**: Remove childish icons, add a functional search bar, and implement category filters for Tool Brands (Snap-on, Milwaukee, DeWalt, Harbor Freight) and specific mechanical/electrical capabilities.

### R4. Affiliate Parts Dashboard & Garage Sign-Up Vault (Results Page)
Enhance `frontend/src/app/results/*` with:
- **Curated Affiliate Cards (`PartsPurchasePlan.tsx`)**: Render each required part/tool with 2 structured options (e.g., OEM Factory Part vs Premium Aftermarket / Synthetic vs Conventional Oil) featuring clear technical rationales and affiliate search links.
- **3-Column Price Comparison**: Accurately display Dealership vs Independent Shop vs RAPP Guided DIY costs (Guide Fee $4.00 + verified parts total).
- **Post-Repair Garage Vault Sign-Up**: Add a prominent "Save to My Garage & Keep Guide Forever" registration section/modal allowing users to archive their vehicle profile, diagnostic guide, and payment preferences.

## Acceptance Criteria

### Verification & Build Integrity
- [ ] Running `cd frontend && npm run build` (or `npx next build`) succeeds without TypeScript compilation errors or broken imports.
- [ ] All interactive UI flows (4-step selector, OBD-II tag addition/removal, tool inventory filtering, and sign-up modal trigger) function smoothly without client-side console runtime errors.

## Initial Request from User — 2026-07-03T01:54:37-05:00
You are the Project Orchestrator for Phase 2 of the RAPP redesign.
Your workspace directory is /Users/prathambansal/Dev/RAPP.
The verbatim Phase 2 request and project history are recorded in /Users/prathambansal/Dev/RAPP/ORIGINAL_REQUEST.md.
Please use /Users/prathambansal/Dev/RAPP/.agents/orchestrator/ as your coordination/metadata directory. Initialize your own plan.md and progress.md for Phase 2 (clean up/overwrite any old files in that folder).
Decompose Phase 2 into milestones, spawn specialized subagents to implement the required visual and functional updates, and guide the project to a successful completion. Keep progress.md updated.
