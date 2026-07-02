# Plan: Automotive AI Repair Engine Product Evolution

## Overview
This plan evolves the existing RAPP app from a prototype to a polished, professional product with Firebase accounts, multiple vehicle entry methods (dropdown, OCR), smarter input features, a side-panel AI chatbot, and back navigation throughout.

## Milestones

### Milestone 1: Baseline Verification
- **Objective**: Run the existing tests and build to ensure a clean starting state.
- **Deliverables**: Verification report confirming unit tests pass, Playwright tests pass, and frontend builds without error.
- **Target Location**: `/Users/prathambansal/Dev/RAPP/`
- **Dependency**: None

### Milestone 2: Home Page & Navigation Evolution (R1, R6)
- **Objective**: Implement Year/Make/Model selector, OCR-based VIN scanner, and update home page layout.
- **Deliverables**: Cascading dropdowns (Year -> Make -> Model) storing `rapp_vin_data` in localStorage, photo capture running OCR via Tesseract.js, and back navigation buttons.
- **Target Location**: `/Users/prathambansal/Dev/RAPP/frontend/src/app/`
- **Dependency**: Milestone 1

### Milestone 3: Diagnose & Results Pages Evolution (R2, R3)
- **Objective**: Redesign `/diagnose` and `/results` pages with professional UI components, smart input fields, and back buttons.
- **Deliverables**: Vehicle hero card with manufacturer logo and styled title, searchable OBD-II code picker (P, B, C, U codes), dashboard light image upload & preview, SVG tool icons, professional symptom placeholder, copy reduced by 40%, and back navigation.
- **Target Location**: `/Users/prathambansal/Dev/RAPP/frontend/src/app/`
- **Dependency**: Milestone 2

### Milestone 4: Premium Repair Page (R4)
- **Objective**: Revamp the repair instructions page with inline diagrams, a structured 5-phase procedure, varied typography, and a persistent side-panel AI chatbot.
- **Deliverables**: SVG schematics embedded inline contextually, detailed 5-phase procedure including a Conclusion/Verification step, persistent side-panel chatbot visible by default with proactive contextual message, and back button.
- **Target Location**: `/Users/prathambansal/Dev/RAPP/frontend/src/app/repair/`
- **Dependency**: Milestone 3

### Milestone 5: Firebase Setup & Account Integration (R5)
- **Objective**: Initialize Firebase and implement Firebase Auth + Cloud Firestore for saving repair guides.
- **Deliverables**: `src/lib/firebase.ts` client-side initialization, env vars in `.env.example`, Firebase Auth sign-up/login, Firestore database integration to save repairs/profile, optional/dismissible sign-up card at the end of `/repair`, `/garage` page listing saved repairs, and "Log In" link in the header.
- **Target Location**: `/Users/prathambansal/Dev/RAPP/frontend/`
- **Dependency**: Milestone 4

### Milestone 6: Final E2E Verification & Hardening
- **Objective**: Verify that all product requirements and E2E tests are 100% passing and secure.
- **Deliverables**: Verified build, passing E2E suite, passing unit tests, and a clean Forensic Audit report.
- **Target Location**: `/Users/prathambansal/Dev/RAPP/`
- **Dependency**: Milestone 5
