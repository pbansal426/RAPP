# Product Evolution Specification (Phase 2 & UX Conversion Engine)

## Overview
This specification details the UX, conversion engine, instructional design, and live AI integration requirements for the Phase 2 evolution of the **Automotive AI Repair Engine (RAPP)**.

The primary objective is twofold:
1. **Unbeatable Instructional Clarity**: Ensure repair instructions are so effective, helpful, structured, and easy to follow that users will never consider choosing another alternative (such as dealership service, generic forums, or YouTube tutorials).
2. **High-Conversion Paywall & Hook Engine**: Show users exactly what the diagnosed problem is, highlight the staggering financial and time differences between dealership/shop repair and self-repair, and hook them immediately into unlocking the app's full repair guidance.

---

## 1. High-Conversion Paywall Panel (`/results` Page Redesign)

When a user completes diagnostic input and reaches the Results Page (`/results`), they must be presented with a compelling, conversion-focused paywall rather than a generic "locked" card.

### Key Components:
- **Plain-English Problem Diagnosis Card**:
  - Display the specific identified root cause clearly (e.g., *P0301 — Cylinder 1 Misfire*).
  - Explain the immediate implications and risks of ignoring the issue (e.g., *Rough idle, engine hesitation, and severe risk of permanent catalytic converter damage if left unaddressed*).
- **Interactive Price & Value Comparison Table**:
  - Show a head-to-head comparison demonstrating the immense value of RAPP self-repair:
    | Repair Route | Estimated Cost | Estimated Time | Value Hook |
    | :--- | :--- | :--- | :--- |
    | **🏢 Dealership** | $450 – $900 | 3 – 5 Days | High markup, diagnostic fees, waiting rooms |
    | **🔧 Independent Shop** | $200 – $400 | 1 – 2 Days | Labor rates $150+/hr, variable quality |
    | **⚡ RAPP Self-Repair** | **$35 – $80** | **2 – 3 Hours** | **Save up to 90%, do it right today with guided AI** |
- **Personalized Tool Match Indicator**:
  - Cross-reference the user's selected tools (from `/diagnose`) against the required tools.
  - Show reassuring confidence feedback: *✅ Good news! You already have the tools required for this repair (e.g., Hand Tools, Socket Set).*
- **Urgency & Risk Banner**:
  - If a high-risk flag or potential cascading failure exists, highlight the escalating cost: *⚠️ Delaying this repair risks secondary component failure (Estimated additional cost: $1,200+).*
- **High-Visibility Unlock CTA Button**:
  - Must preserve exact selector `data-testid="payment-cta-btn"` containing the word "Unlock".
  - Styled with neon/high-contrast accents, clear pricing ($9.99 lifetime unlock for this vehicle), and instant reassurance.

---

## 2. Ultra-Effective Repair Guides (`/repair` Page Redesign)

Once unlocked, the repair guidance must set a new industry standard for clarity and ease of execution.

### Key Components:
- **Phased & Structured Progression**:
  - Break down complex procedures into distinct, digestible phases:
    1. **🛑 Phase 1: Safety & Vehicle Preparation** (Battery disconnect, cooling wait times, lift/jack stand placement).
    2. **🔩 Phase 2: Disassembly & Access** (Removing covers, brackets, and obstructing parts).
    3. **⚙️ Phase 3: Component Replacement** (Exact removal and installation of the target part).
    4. **✅ Phase 4: Reassembly & Verification** (Torque verification, leak checks, OBD-II code clearing, and test drive protocols).
- **Inline Tool & Socket Callouts**:
  - Every step that requires a tool explicitly highlights the exact socket size, extension length, or tool type directly inline (e.g., *Remove the 4 mounting bolts using a **[10mm deep socket + 3-inch extension]***).
- **Prominent Torque Specifications**:
  - Highlight exact torque specs in bold yellow/orange contrast so overtightening or stripped bolts are prevented (e.g., *Torque bolts in a crisscross pattern to **18 ft-lbs (24 Nm)***).
- **Safety & Caution Checkpoints**:
  - Non-dismissible warnings embedded before critical steps (e.g., *⚠️ CAUTION: Ensure fuel rail pressure is fully relieved before loosening injector clips*).
- **Interactive Checkbox Tracking**:
  - Allow users to check off steps as they work in their garage, tracking visual progress via a persistent progress bar.
- **Complete Parts & Shopping List Card**:
  - Provide OEM part numbers, estimated retail prices, and typical part store availability (AutoZone, O'Reilly, Amazon).

---

## 3. Mobile-First & Garage-Ready Ergonomics

Because users will be referencing the app on phones or tablets in garages with greasy or gloved hands:
- **Minimum 48px–52px Touch Targets**: Every interactive element, button, and checkbox must exceed standard mobile touch targets.
- **Sticky Bottom Action Bar on Mobile**: Ensure the Unlock CTA on `/results` and navigation controls on `/repair` remain easily accessible via thumb reach at the bottom of mobile viewports (375px–430px).
- **High-Contrast Dark Mode Default**: High contrast dark theme (`dark bg-slate-900` body class) designed to reduce screen glare and maximize readability under harsh garage fluorescent lighting or sunlight.

---

## 4. Live AI & RAG Engine Integration

- **Live Gemini Synthesis** (done — see `backend/services/gemini.py`): Transition from static mock diagnostic summaries to real-time Gemini (`gemini-3.5-flash`) synthesis using live VIN metadata and symptom narratives. This includes vision-based VIN OCR via Gemini's native multimodal input; OpenAI is no longer used anywhere in the stack.
- **Vector-Verified Constraints**: Pull real technical repair procedures from the ChromaDB vector store (`backend/rag/`) and enforce user tool constraints so the AI never suggests procedures requiring professional equipment (like 2-post hydraulic lifts) if the user only has basic hand tools and jack stands.
