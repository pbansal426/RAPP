Automotive AI Repair Engine: Phase 1 MVP Specification
1. Executive Summary
This document details the precise functional and user experience requirements for Phase 1 of the Automotive AI Repair Engine. The objective of Phase 1 is strictly software validation: converting high-friction, hours-long vehicle diagnostic research into actionable, tool-aware instructions in under 10 seconds. We are validating the core value proposition before any hardware integration.
2. Core Application Flow & Architecture
2.1 The "One-Shot" Input Sequence
The application must prioritize speed to value. Users arrive with a broken vehicle; they do not want to configure a profile. The flow must be entirely frictionless.
Step 1: VIN Ingestion. The initial screen consists of a single, prominent input field for the Vehicle Identification Number (VIN) or a prominent "Scan VIN Barcode" button.
Step 2: Diagnostic Input. Once the vehicle is identified, the user is presented with a structured input interface for symptoms or specific OBD-II codes.
Step 3: Tool Constraint Profile. A rapid-selection interface where the user defines their available equipment (e.g., "Basic Hand Tools," "Jack & Stands," "Torque Wrench," "Multimeter").
Step 4: The Output. The AI generates the repair procedure.
2.2 UI/UX Philosophy: "Grease-Monkey Clean"
The interface must be designed for environments with poor lighting and dirty hands. It cannot look like a generic SaaS dashboard.
High Contrast & Legibility: Dark mode is the default. Use high-contrast typography (large, sans-serif fonts) that can be read from three feet away on a cracked smartphone screen resting on a fender.
Tactile Interactivity: Buttons and touch targets must be oversized. Input fields should leverage native mobile keyboards aggressively (e.g., numeric pads for codes, camera invocation for barcodes).
Information Hierarchy: The output must be immediately scannable. Do not present walls of text. Use bullet points, bolded warnings, and clear step-by-step numbering.
3. Feature Specifications & Strategic Rationale
3.1 Component 1: Frictionless VIN Decoding (The NHTSA Integration)
Feature: Immediate, automatic decoding of the VIN into Year, Make, Model, Engine size, and Drive type using the NHTSA API.
The "Why": Manual vehicle selection (Year -> Make -> Model dropdowns) is a legacy friction point. It creates a high barrier to entry and introduces user error. By relying on the VIN, we guarantee accurate retrieval from the vector database. It establishes immediate trust that the system "knows" their specific car.
3.2 Component 2: The "Tool-Aware" Logic Engine
Feature: A mandatory selection step before output generation where users define their available toolkit. The AI is instructed to synthesize repair steps constrained by this inventory.
The "Why": This is the primary competitive moat against generic Google searches or standard ChatGPT queries. Factory service manuals assume the user has a fully equipped dealership bay and proprietary specialty tools. Our value proposition is translating these manuals into procedures possible in a residential driveway. If a repair requires a lift and the user only has jack stands, the system must either adapt the procedure safely or flag the repair as outside their current capability.
3.3 Component 3: RAG-Verified Procedural Output
Feature: The generated repair steps must explicitly cite the specific sections of the factory service manual from which the information was derived.
The "Why": Hallucination in automotive repair can lead to catastrophic mechanical failure or physical injury. The output cannot just be a plausible guess; it must be a synthesis of verified, OEM-approved procedures. Citations build the necessary authority and allow users to verify critical torque specs or sequences.
3.4 Component 4: The "Safety & Escalation" Protocol
Feature: The application must programmatically recognize high-risk systems (e.g., SRS/Airbags, high-voltage EV battery systems, pressurized fuel lines) based on the diagnostic input. When triggered, the UI must present prominent, non-dismissible safety warnings before providing the procedure. It must also include a clear escalation path (e.g., "This procedure requires a dealer-level calibration tool. Professional service is recommended").
The "Why": Liability mitigation is critical. We must protect the user from injury and the company from lawsuits. The app must act as a responsible advisor, not just an information dump.
4. Phase 1 Monetization Integration
Feature: The initial diagnostic check (identifying the likely issue based on symptoms/codes) is free. The detailed, step-by-step repair procedure (the "Unlock") is gated behind a paywall ($3.99 single unlock / $14.99 VIN pass).
The "Why": We provide enough immediate value (diagnosing the problem) to establish credibility. The monetization occurs at the exact moment of highest intent and utility—when the user needs to know how to fix it right now. We use Stripe Payment Links for low-friction, immediate transaction processing without requiring complex user account creation first.
