# Plan: RAPP Phase 2 Redesign

## Overview
This plan implements the Phase 2 requirements for the RAPP (Real Automotive Professional Platform) redesign, converting the frontend into a premium, engineering-grade platform with the Deep Industrial Navy design system, cascading vehicle selector, isolated OBD-II diagnostic tooling, and affiliate garage vault.

## Milestones

### Milestone 1: Baseline Audit & Verification
- **Objective**: Run existing test suite and compile checks; audit current files to identify existing vs missing functionality.
- **Deliverables**: Verified build/test results, gap assessment report.
- **Target Location**: `/Users/prathambansal/Dev/RAPP`
- **Dependency**: None

### Milestone 2: Deep Industrial Navy Design System & 4-Step Vehicle Selector (R1, R2)
- **Objective**: Transform globals.css and layouts to the slate navy (#0F172A), charcoal, safety orange (#F97316) palette. Upgrade homepage vehicle selector to a 4-step cascading dropdown (Year -> Make -> Model -> Trim) with auto-lock specs for single-powertrain models/trims.
- **Deliverables**: globals.css styling updates, 4-step cascading dropdown on the homepage with spec locking.
- **Target Location**: `frontend/src/app/`
- **Dependency**: Milestone 1

### Milestone 3: Automotive Diagnostic Panel (R3)
- **Objective**: Enhance the /diagnose page with a brand logo badge, isolated OBD-II tags/chips, HEIC photo previews (up to 3 thumbnails, collapse toggle), and searchable tool inventory with capability and brand filters.
- **Deliverables**: Updated VehicleHeroCard.tsx, ObdCodePicker.tsx, and ToolSelector.tsx.
- **Target Location**: `frontend/src/app/diagnose/`
- **Dependency**: Milestone 2

### Milestone 4: Affiliate Parts Dashboard & Garage Sign-up (R4)
- **Objective**: Enhance the /results page with curated affiliate cards (OEM vs aftermarket), 3-column price comparison (Dealer, Independent, DIY ($4 + parts)), and a post-repair Garage Vault sign-up section/modal.
- **Deliverables**: Updated PartsPurchasePlan.tsx, price comparison table, and garage registration card/modal.
- **Target Location**: `frontend/src/app/results/`
- **Dependency**: Milestone 3

### Milestone 5: Final Verification & Build Integrity
- **Objective**: Verify that the Next.js frontend builds cleanly, unit tests pass, and E2E tests pass under normal and faulty conditions. Run a Forensic Audit.
- **Deliverables**: Green E2E test results, successful build logs, and a clean Forensic Audit report.
- **Target Location**: `/Users/prathambansal/Dev/RAPP`
- **Dependency**: Milestone 4
