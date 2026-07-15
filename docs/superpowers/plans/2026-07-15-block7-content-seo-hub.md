# Block 7: High-Velocity Content & SEO Hub — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Stage 3.1 (routine maintenance repair templates) and Stage 3.2 (Knowledge Hub `/hub` article library) from `docs/implementation/imp.md`, closing gap-table rows "Maintenance Content (Wipers/Oil/etc.)" and "Knowledge Hub & Article CM".

**Architecture:** Stage 3.1 adds four new deterministic `RepairTemplate` entries (wiper blades, under-hood fluid top-off, bulb replacement, tire pressure/TPMS) to the existing `backend/repair_templates.py` middle-rung content ladder — no new endpoints, no schema changes. Stage 3.2 adds a static, client-rendered `/hub` article index plus per-article routes under `frontend/src/app/hub/`, sourcing curated text content from a new presentational data file inside that same directory (not `frontend/src/lib/*.ts`, which is reserved for the Claude/Gemini pinned-contract typed data layer per `CLAUDE.md`).

**Tech Stack:** Python 3.11 / FastAPI / pytest (backend), Next.js 14 App Router / TypeScript / vanilla CSS (frontend).

## Global Constraints

- No Tailwind utility classes anywhere in new `.tsx` — vanilla CSS via `globals.css` design tokens only (`CLAUDE.md`).
- All interactive elements ≥48px × 48px touch target (`CLAUDE.md` Test infrastructure section; also imp.md §2.5 Pillar 6).
- Dark-mode body class (`<body className="dark bg-slate-900">` in `layout.tsx`) must not be altered.
- Every `RepairTemplate.steps` list needs ≥14 entries, at least one entry containing the literal substring `"Torque "`, no emoji characters, ≥1 citation, ≥1 parts entry — enforced by `tests/unit/test_templates.py` (`test_every_template_has_minimum_step_count`, `test_every_template_has_a_torque_callout`, `test_no_emoji_in_any_step`, `test_every_template_has_citations_and_parts`) and applies to every template in `_TEMPLATES`, including new ones.
- New `_KEYWORD_RULES` entries must not be shadowed by earlier, broader patterns already in the list (e.g. the existing `brake|squeal|grinding|rotor|caliper|pad` rule would incorrectly capture "brake light bulb" unless the new bulb rule is inserted *before* it).
- Do not touch `_TEMPLATES`/`_KEYWORD_RULES` entries for existing categories (`oil_service`, `charging_battery`, `brakes`, etc.) — Stage 3.1 is additive only.
- `/hub` and `/hub/[slug]` must not read or write any `localStorage` keys from the frozen list (`rapp_vin`, `rapp_vin_data`, `rapp_symptoms`, `rapp_tools`, `rapp_unlocked_{vin}`, `rapp_garage_dismissed_{vin}`) — it's a standalone, VIN-agnostic content section.
- Per CLAUDE.md's 4-step protocol: run `uv run ruff check backend/`, `uv run black --check backend/`, `uv run mypy backend/`, `uv run pytest tests/unit/ -v` before any backend commit; run `cd frontend && ./node_modules/.bin/next build` before any frontend commit; commit code and docs updates as **separate** commits; append a Section 6 log entry and flip the Block 7 row in `docs/MODEL_ASSIGNMENT_GUIDE.md` to ✅ before ending the session.

---

## File Structure

- Modify `backend/repair_templates.py` — add 4 `RepairTemplate` constants, register them in `_TEMPLATES`, add keyword rules to `_KEYWORD_RULES` (inserted at the correct position relative to existing rules), add one `_CODE_RANGES` entry for TPMS codes.
- Modify `backend/pricing.py` — add labor-hour entries for the 4 new categories to `_LABOR_HOURS_BY_CATEGORY`.
- Modify `tests/unit/test_templates.py` — add selection-matching tests for the 4 new categories plus one negative/precedence test (brake-light-bulb must not be classified as `brakes`).
- Create `frontend/src/app/hub/articles.ts` — typed array of curated article content (presentational data, lives under `app/hub` per the Claude/Gemini split, not `src/lib`).
- Create `frontend/src/app/hub/page.tsx` — `/hub` index: card grid of articles, category filter chips.
- Create `frontend/src/app/hub/[slug]/page.tsx` — individual article page, `generateStaticParams` from `articles.ts`.
- Create `frontend/src/app/hub/hub.module.css` or extend `globals.css` — hub-specific classes (card grid, chip filter, article prose) as design-token-driven vanilla CSS. (Plan uses `globals.css` extension to match the codebase's existing single-stylesheet convention — see `frontend/src/app/page.tsx`/`results/page.tsx`, which don't use CSS modules.)

---

## Task 1: Wiper Blade Replacement template

**Files:**
- Modify: `backend/repair_templates.py`

**Interfaces:**
- Produces: `WIPER_BLADES: RepairTemplate` with `category="wiper_blades"`, registered in `_TEMPLATES["wiper_blades"]`.

- [ ] **Step 1: Add the `WIPER_BLADES` constant**

Insert after the `WHEEL_SPEED_ABS = RepairTemplate(...)` block (before `_TEMPLATES: dict[str, RepairTemplate] = {`):

```python
WIPER_BLADES = RepairTemplate(
    category="wiper_blades",
    title="Wiper Blade Replacement",
    steps=[
        "Park on level ground and shut off the engine, ensuring the wiper arms are in their normal resting position (not mid-cycle) before beginning.",
        "Lift the wiper arm away from the windshield until it locks in the raised service position, taking care not to let it snap back onto the glass.",
        "Locate the small tab or button on the underside of the wiper blade where it connects to the hooked end of the wiper arm.",
        "Press the release tab and slide the old wiper blade down and off the hook of the wiper arm.",
        "Compare the new wiper blade's connector type and length to the original to confirm correct fitment before discarding the old blade.",
        "Align the new blade's connector with the hook on the wiper arm and slide it on until the release tab clicks and locks into place.",
        "Gently tug the new blade to confirm it is fully seated and will not detach during operation.",
        "Lower the wiper arm carefully back down onto the windshield rather than letting it snap, to avoid cracking the glass or bending the arm.",
        "Repeat the removal and installation steps for the opposite wiper blade, and the rear wiper blade if the vehicle has one.",
        "If a wiper arm feels loose or wobbles at its base, lift the plastic cap covering the arm's mounting nut and confirm it is snug; Torque the wiper arm retaining nut to 12-18 Nm (9-13 ft-lbs) if it was found loose, then reseat the cap.",
        "Fill the washer fluid reservoir under the hood to the indicated full line using washer fluid rated for the current season's temperatures.",
        "Turn the ignition to the accessory or on position without starting the engine, and cycle the wipers through a full sweep to confirm smooth movement with no skipping.",
        "Spray the washer fluid and confirm both nozzles stream directly onto the wiper's sweep path, adjusting nozzle aim with a pin if the spray is misdirected.",
        "Inspect the wiped windshield for streaking or missed spots, which indicates a blade is not seated flush against the glass and should be reseated.",
        "Wipe down the new blades' rubber edge with a clean cloth and glass cleaner to remove any manufacturing residue before the first full use.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Wiper blade set, driver + passenger ($15-$35)",
        "Washer fluid, per gallon ($4-$8)",
    ],
)
```

- [ ] **Step 2: Register it in `_TEMPLATES`**

In the `_TEMPLATES` dict literal, add `WIPER_BLADES,` to the list (any position — order doesn't matter, dict is keyed by `.category`).

- [ ] **Step 3: Verify manually**

Run: `uv run python -c "from backend.repair_templates import _TEMPLATES; print(_TEMPLATES['wiper_blades'].title)"`
Expected: `Wiper Blade Replacement`

- [ ] **Step 4: Commit**

Hold this commit — Tasks 2-4 touch the same file/dict/list; commit once at the end of Task 4 (Step-right-sizing: these four templates are one reviewable unit, see Task 5).

---

## Task 2: Under-Hood Fluid Check & Top-Off template

**Files:**
- Modify: `backend/repair_templates.py`

**Interfaces:**
- Produces: `FLUID_TOPOFF: RepairTemplate` with `category="fluid_topoff"`.

- [ ] **Step 1: Add the `FLUID_TOPOFF` constant**

Insert immediately after `WIPER_BLADES`:

```python
FLUID_TOPOFF = RepairTemplate(
    category="fluid_topoff",
    title="Under-Hood Fluid Check & Top-Off (Multi-Point)",
    steps=[
        "Park on level ground and allow the engine to cool for at least 15 minutes if it was recently running, since some fluid checks require a cool system.",
        "Open the hood and secure it on its prop rod or support strut before working underneath it.",
        "Locate the engine oil dipstick, pull it, wipe it clean, reinsert fully, then pull it again to confirm the oil level sits between the min and max marks.",
        "Check the coolant level at the translucent overflow reservoir (not the radiator cap) against its cold-fill line, and top off with the manufacturer-specified coolant-to-water ratio if low.",
        "Never open the radiator cap on a warm or hot engine -- pressurized coolant can cause severe burns.",
        "Locate the brake fluid reservoir, typically near the firewall on the driver's side, and confirm the level sits between the min and max marks visible through the translucent housing.",
        "Wipe the area around the brake fluid cap clean before removing it, so no dirt falls into the reservoir, then top off with the fluid type printed on the cap (commonly DOT 3 or DOT 4) if below the max line.",
        "Locate the power steering fluid reservoir (not present on electric power steering vehicles) and check the level against the marked min/max lines on the reservoir or dipstick cap.",
        "Top off power steering fluid with the manufacturer-specified type in small increments, rechecking the level between additions to avoid overfilling.",
        "Locate the windshield washer fluid reservoir, identified by its washer-symbol cap, and fill to the indicated line with a fluid rated for the current season's temperatures.",
        "Inspect the automatic transmission fluid level per the manufacturer's procedure if a dipstick is present (many modern vehicles use a sealed system with no user-serviceable dipstick -- confirm before attempting).",
        "While the hood is open, check that the battery hold-down clamp is snug; if it has loosened, Torque the battery hold-down clamp bolt to 53 in-lbs (6 Nm) so the battery cannot vibrate against the tray.",
        "Inspect each reservoir cap for cracked seals or missing gaskets, since a bad cap seal can let fluid evaporate or let contaminants in.",
        "Wipe up any spilled fluid immediately with a shop rag, since spilled coolant, oil, or brake fluid can damage drive belts, hoses, or paint.",
        "Close and latch the hood securely, confirming both hood latches engage before driving.",
        "Start the engine and check that warning lights related to fluid levels (oil pressure, coolant temperature, brake fluid) are extinguished.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Engine coolant, per gallon ($15-$25)",
        "Brake fluid, DOT 3/4 ($8-$12)",
        "Power steering fluid ($8-$15)",
        "Washer fluid, per gallon ($4-$8)",
    ],
)
```

- [ ] **Step 2: Register it in `_TEMPLATES`**

Add `FLUID_TOPOFF,` to the `_TEMPLATES` dict literal list.

- [ ] **Step 3: Verify manually**

Run: `uv run python -c "from backend.repair_templates import _TEMPLATES; print(_TEMPLATES['fluid_topoff'].title)"`
Expected: `Under-Hood Fluid Check & Top-Off (Multi-Point)`

---

## Task 3: Bulb Replacement template

**Files:**
- Modify: `backend/repair_templates.py`

**Interfaces:**
- Produces: `BULB_REPLACEMENT: RepairTemplate` with `category="bulb_replacement"`.

- [ ] **Step 1: Add the `BULB_REPLACEMENT` constant**

Insert immediately after `FLUID_TOPOFF`:

```python
BULB_REPLACEMENT = RepairTemplate(
    category="bulb_replacement",
    title="Headlight, Taillight & Turn Signal Bulb Replacement",
    steps=[
        "Park on level ground, shut off the engine, and turn off all lights before beginning to avoid burns from a hot bulb.",
        "Identify which bulb is out by cycling through headlights, taillights, brake lights, and turn signals with a helper or by watching reflections in a storefront window.",
        "Open the hood for a headlight bulb, or open the trunk/hatch and remove any interior trim panel covering the back of the taillight housing for a rear bulb.",
        "Locate the bulb socket's electrical connector on the back of the headlight or taillight housing and disconnect it by releasing the locking tab.",
        "Rotate the bulb-and-socket assembly counterclockwise about a quarter turn to release it from the housing, then pull it straight out.",
        "For headlight bulbs, avoid touching the new bulb's glass with bare fingers -- skin oils cause hot spots that can cause premature failure; handle it with a clean cloth or gloves.",
        "Compare the new bulb's part number and base type to the original before installing to confirm correct fitment.",
        "Insert the new bulb into the socket, aligning the locating tabs with the socket's slots so it can only seat in the correct orientation.",
        "Rotate the bulb-and-socket assembly clockwise a quarter turn to lock it back into the housing.",
        "Reconnect the electrical connector to the back of the bulb socket until it clicks into place.",
        "If accessing the taillight required removing the housing itself rather than a rear access panel, reinstall the housing and Torque the housing retaining nuts to 44 in-lbs (5 Nm), taking care not to overtighten the plastic mounting bosses.",
        "Turn on the corresponding light (headlight, taillight, brake light, or turn signal) and visually confirm the new bulb illuminates correctly.",
        "Reinstall any interior trim panel removed to access the taillight assembly, confirming all retaining clips snap fully back into place.",
        "Close the hood or trunk/hatch and confirm both latch securely.",
        "Walk around the vehicle at dusk or in a shaded area to visually confirm even brightness and correct color between the new bulb and its opposite-side match.",
        "If a 'bulb out' warning light remains on the dashboard after replacement, check the bulb's wattage rating matches the original, since an incorrect wattage can trigger a false warning even when the bulb itself works.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Headlight bulb, per bulb ($8-$35)",
        "Taillight/brake bulb, per bulb ($4-$12)",
        "Turn signal bulb, per bulb ($3-$10)",
    ],
)
```

- [ ] **Step 2: Register it in `_TEMPLATES`**

Add `BULB_REPLACEMENT,` to the `_TEMPLATES` dict literal list.

- [ ] **Step 3: Verify manually**

Run: `uv run python -c "from backend.repair_templates import _TEMPLATES; print(_TEMPLATES['bulb_replacement'].title)"`
Expected: `Headlight, Taillight & Turn Signal Bulb Replacement`

---

## Task 4: Tire Pressure Check, Adjustment & TPMS Reset template

**Files:**
- Modify: `backend/repair_templates.py`

**Interfaces:**
- Produces: `TIRE_PRESSURE: RepairTemplate` with `category="tire_pressure"`.

- [ ] **Step 1: Add the `TIRE_PRESSURE` constant**

Insert immediately after `BULB_REPLACEMENT`:

```python
TIRE_PRESSURE = RepairTemplate(
    category="tire_pressure",
    title="Tire Pressure Check, Adjustment & TPMS Reset",
    steps=[
        "Check tire pressure only when tires are cold -- ideally before driving more than a mile, or after the vehicle has sat for at least 3 hours, since driving heats the tires and raises the reading.",
        "Locate the manufacturer's recommended cold tire pressure on the placard inside the driver's door jamb, not the maximum pressure molded into the tire's sidewall.",
        "Remove the valve stem cap from the first tire and set it somewhere it will not be lost.",
        "Press a tire pressure gauge firmly onto the valve stem until the hissing stops and read the pressure, pressing straight on to avoid a false low reading from air escaping around the gauge.",
        "Take two or three readings and use the most consistent value, since a crooked gauge placement can under-report pressure.",
        "If the pressure is below the door-placard specification, add air in short bursts using a portable compressor or gas-station air pump, rechecking the pressure between bursts.",
        "If the pressure is above the specification, press the small pin inside the valve stem briefly with the gauge's bleed tool to release air in short bursts until at spec.",
        "Reinstall the valve stem cap finger-tight to keep out dirt and moisture -- overtightening can crack the plastic cap.",
        "Repeat the check-and-adjust process for all four tires, plus the spare if it is a full-size or matching spare intended for road use.",
        "Inspect each tire's tread for uneven wear patterns while at the wheel, which can indicate alignment or suspension issues beyond a simple pressure adjustment.",
        "If the vehicle is also due for a tire rotation as part of this service, loosen the lug nuts a quarter turn while the wheel is still on the ground, then raise the vehicle on jack stands rated for its weight.",
        "Rotate the tires per the manufacturer's pattern (commonly front-to-back on the same side, or a cross pattern for non-directional tires) and reinstall each wheel.",
        "Torque the lug nuts to the manufacturer specification (commonly 80-100 ft-lbs / 108-135 Nm) in a star pattern once the vehicle is lowered back to the ground.",
        "On vehicles with a TPMS relearn procedure, follow the manufacturer's reset sequence (commonly holding the TPMS reset button under the dash until the light blinks, then driving at 15+ mph for several minutes) so the system recognizes the corrected pressures.",
        "Confirm the dashboard TPMS or 'check tire pressure' warning light turns off after driving; if it remains on, recheck all four tires plus the spare, since a single missed tire keeps the light active.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Tire pressure gauge (one-time, $6-$15)",
        "Valve stem caps, set of 4 ($3)",
    ],
)
```

- [ ] **Step 2: Register it in `_TEMPLATES`**

Add `TIRE_PRESSURE,` to the `_TEMPLATES` dict literal list. The full list now reads:

```python
_TEMPLATES: dict[str, RepairTemplate] = {
    t.category: t
    for t in [
        IGNITION_MISFIRE,
        OXYGEN_SENSOR,
        FUEL_TRIM_LEAN,
        CATALYTIC_CONVERTER,
        EVAP_LEAK,
        BRAKES,
        BRAKES_DRUM,
        SUSPENSION,
        CHARGING_BATTERY,
        COOLING_SYSTEM,
        OIL_SERVICE,
        EXHAUST,
        WHEEL_SPEED_ABS,
        WIPER_BLADES,
        FLUID_TOPOFF,
        BULB_REPLACEMENT,
        TIRE_PRESSURE,
    ]
}
```

- [ ] **Step 3: Add the TPMS OBD-code range**

In `_CODE_RANGES`, add a row for TPMS diagnostic codes (SAE-standard `C0740`-`C0749` cover TPMS sensor/system faults):

```python
_CODE_RANGES: list[tuple[str, str, str]] = [
    ("P0300", "P0312", "ignition_misfire"),
    ("P0130", "P0167", "oxygen_sensor"),
    ("P0171", "P0175", "fuel_trim_lean"),
    ("P0420", "P0434", "catalytic_converter"),
    ("P0440", "P0457", "evap_leak"),
    ("P0562", "P0563", "charging_battery"),
    ("P0117", "P0128", "cooling_system"),
    ("C0035", "C0050", "wheel_speed_abs"),
    ("C0740", "C0749", "tire_pressure"),
]
```

- [ ] **Step 4: Add keyword rules for all four new categories, in the correct order**

The bulb rule MUST be inserted **before** the existing `brakes` rule (`re.compile(r"brake|squeal|grinding|rotor|caliper|pad", ...)`), because that pattern's bare `brake` would otherwise capture "brake light bulb" text first. Rewrite `_KEYWORD_RULES` to:

```python
_KEYWORD_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"misfire|rough idle|shak(e|ing)|stumbl", re.IGNORECASE),
        "ignition_misfire",
    ),
    (re.compile(r"oxygen sensor|o2 sensor", re.IGNORECASE), "oxygen_sensor"),
    (re.compile(r"lean|vacuum leak|fuel trim", re.IGNORECASE), "fuel_trim_lean"),
    (re.compile(r"catalytic|catalyst", re.IGNORECASE), "catalytic_converter"),
    (re.compile(r"evap|gas cap|purge valve|vent valve", re.IGNORECASE), "evap_leak"),
    (
        re.compile(
            r"headlight|tail ?light|brake light bulb|turn signal bulb|bulb (is )?(out|blown|burned out)",
            re.IGNORECASE,
        ),
        "bulb_replacement",
    ),
    (re.compile(r"brake|squeal|grinding|rotor|caliper|pad", re.IGNORECASE), "brakes"),
    (
        re.compile(r"suspension|strut|shock|coilover|clunk|bounc", re.IGNORECASE),
        "suspension",
    ),
    (
        re.compile(
            r"battery|no start|clicking|alternator|dim lights|charging", re.IGNORECASE
        ),
        "charging_battery",
    ),
    (
        re.compile(r"overheat|coolant|thermostat|radiator", re.IGNORECASE),
        "cooling_system",
    ),
    (re.compile(r"oil change|oil leak|oil life", re.IGNORECASE), "oil_service"),
    (
        re.compile(r"exhaust|muffler|catback|cat-back|resonator", re.IGNORECASE),
        "exhaust",
    ),
    (
        re.compile(r"abs light|wheel speed|traction control", re.IGNORECASE),
        "wheel_speed_abs",
    ),
    (
        re.compile(r"wiper|windshield smear|streak(y|ing)? wipers?", re.IGNORECASE),
        "wiper_blades",
    ),
    (
        re.compile(
            r"washer fluid|power steering fluid|fluid top.?off|topping off fluids|low on fluid",
            re.IGNORECASE,
        ),
        "fluid_topoff",
    ),
    (
        re.compile(r"tire pressure|tpms|low tire|tire light|under ?inflated|over ?inflated", re.IGNORECASE),
        "tire_pressure",
    ),
]
```

- [ ] **Step 5: Verify manually**

Run: `uv run python -c "from backend.repair_templates import select_template; print(select_template('brake light bulb is out', []).category)"`
Expected: `bulb_replacement` (not `brakes`)

Run: `uv run python -c "from backend.repair_templates import select_template; print(select_template('brakes squealing', []).category)"`
Expected: `brakes` (unchanged)

- [ ] **Step 6: Commit Tasks 1-4 together**

```bash
uv run ruff check backend/repair_templates.py
uv run black backend/repair_templates.py
git add backend/repair_templates.py
git commit -m "feat(templates): Block 7 Stage 3.1 -- wiper, fluid top-off, bulb, tire pressure templates"
```

---

## Task 5: Labor-hour estimates for the new categories

**Files:**
- Modify: `backend/pricing.py`

**Interfaces:**
- Consumes: `RepairTemplate.category` strings `wiper_blades`, `fluid_topoff`, `bulb_replacement`, `tire_pressure` from Task 1-4.
- Produces: `_LABOR_HOURS_BY_CATEGORY` entries consumed by `build_cost_breakdown()` (unchanged signature).

- [ ] **Step 1: Add entries to `_LABOR_HOURS_BY_CATEGORY`**

In `backend/pricing.py`, extend the dict (all four are quick DIY jobs, comparable to or faster than the existing `oil_service: 0.5`):

```python
_LABOR_HOURS_BY_CATEGORY: dict[str, float] = {
    "ignition_misfire": 1.0,
    "oxygen_sensor": 0.8,
    "fuel_trim_lean": 1.5,
    "catalytic_converter": 2.0,
    "evap_leak": 1.2,
    "brakes": 1.5,
    "suspension": 2.5,
    "charging_battery": 1.0,
    "cooling_system": 1.5,
    "oil_service": 0.5,
    "exhaust": 2.0,
    "wheel_speed_abs": 1.0,
    "wiper_blades": 0.2,
    "fluid_topoff": 0.3,
    "bulb_replacement": 0.3,
    "tire_pressure": 0.3,
}
```

- [ ] **Step 2: Verify these stay in Tier 1 pricing (`$4.99`)**

Run: `uv run python -c "
from backend.pricing import build_cost_breakdown
from backend.repair_templates import get_template
for cat in ['wiper_blades', 'fluid_topoff', 'bulb_replacement', 'tire_pressure']:
    cb = build_cost_breakdown(get_template(cat))
    print(cat, cb['guide_fee'], cb['dealership_cost_range'])
"`
Expected: `guide_fee` prints `4.99` for all four (dealership high-end must stay under \$150 — if any prints `9.99`, the parts-price strings in that template's `parts` list are too high; reduce them and re-run).

- [ ] **Step 3: Commit**

```bash
uv run ruff check backend/pricing.py
uv run black backend/pricing.py
git add backend/pricing.py
git commit -m "feat(pricing): labor-hour estimates for Block 7 maintenance templates"
```

---

## Task 6: Unit tests for the four new templates

**Files:**
- Modify: `tests/unit/test_templates.py`

**Interfaces:**
- Consumes: `select_template`, `_TEMPLATES` from `backend.repair_templates` (unchanged signatures).

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_templates.py`, after `test_keyword_fallback_charging`:

```python
def test_keyword_fallback_wiper_blades() -> None:
    template = select_template("My wiper blades are streaking badly", [])
    assert template is not None
    assert template.category == "wiper_blades"


def test_keyword_fallback_fluid_topoff() -> None:
    template = select_template("Need to top off my washer fluid", [])
    assert template is not None
    assert template.category == "fluid_topoff"


def test_keyword_fallback_bulb_replacement() -> None:
    template = select_template("My headlight bulb is out", [])
    assert template is not None
    assert template.category == "bulb_replacement"


def test_keyword_fallback_tire_pressure() -> None:
    template = select_template("TPMS light is on, tire pressure low", [])
    assert template is not None
    assert template.category == "tire_pressure"


def test_obd_code_tire_pressure() -> None:
    template = select_template("Dash warning light", ["C0741"])
    assert template is not None
    assert template.category == "tire_pressure"


def test_bulb_rule_takes_precedence_over_brakes_for_brake_light() -> None:
    # "brake light bulb" must not be misclassified as a brake-pad job --
    # regression guard for the _KEYWORD_RULES ordering fix.
    template = select_template("brake light bulb is out", [])
    assert template is not None
    assert template.category == "bulb_replacement"


def test_brakes_keyword_still_wins_for_actual_brake_symptoms() -> None:
    template = select_template("brakes squealing when I come to a stop", [])
    assert template is not None
    assert template.category == "brakes"
```

- [ ] **Step 2: Run to verify they fail before the code change lands (skip if Tasks 1-4 are already committed)**

Run: `uv run pytest tests/unit/test_templates.py -v`
If Tasks 1-4 are already applied, expected: all PASS already (implementation preceded tests here since template content had to be validated against the existing suite's structural assertions first). If run standalone against a pre-Block-7 checkout, expected: FAIL with `AttributeError: 'NoneType' object has no attribute 'category'`.

- [ ] **Step 3: Run the full suite to confirm no regressions**

Run: `uv run pytest tests/unit/ -v`
Expected: all tests pass, including the pre-existing `test_template_count` (now `len(_all_templates()) == 17`, still `>= 10`), `test_every_template_has_minimum_step_count`, `test_every_template_has_a_torque_callout`, `test_no_emoji_in_any_step`, `test_every_template_has_citations_and_parts` (all four new templates satisfy these by construction in Tasks 1-4).

- [ ] **Step 4: Full backend quality gate**

```bash
uv run ruff check backend/
uv run black --check backend/
uv run mypy backend/
```
Expected: all clean.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_templates.py
git commit -m "test(templates): coverage for Block 7 maintenance template selection"
```

---

## Task 7: Knowledge Hub article content data

**Files:**
- Create: `frontend/src/app/hub/articles.ts`

**Interfaces:**
- Produces: `Article` interface and `ARTICLES: Article[]` const, consumed by Tasks 8 and 9.

- [ ] **Step 1: Write the content file**

```typescript
export interface Article {
  slug: string;
  title: string;
  category: 'Maintenance' | 'Diagnostics' | 'Buying a Guide' | 'Safety';
  summary: string;
  readMinutes: number;
  relatedTemplateCategory?: string;
  body: string[]; // one paragraph per array entry, rendered as <p>
}

export const ARTICLES: Article[] = [
  {
    slug: 'is-my-mechanic-quote-fair',
    title: 'Is My Mechanic Quote Fair? How to Tell in 5 Minutes',
    category: 'Buying a Guide',
    summary:
      'The three numbers on any repair quote that separate a fair price from an overcharge, and where to find them for your exact vehicle.',
    readMinutes: 4,
    body: [
      'A repair quote has three components: parts, labor hours, and labor rate. Most overcharges hide in the labor-hours number, not the labor rate -- a shop quoting 4 hours for a job that takes an experienced tech 1.5 hours is the single most common way estimates get inflated.',
      'Independent shops typically bill $110-$140/hr; dealerships $180-$220/hr. Neither is inherently wrong -- dealerships carry OEM-trained technicians and genuine parts overhead -- but you should know which one you are paying for and why.',
      'Parts markup is normal (30-50% at a dealership, 10-20% at an independent shop covers sourcing, warranty, and inventory risk) but should track the part\'s actual retail price, not an arbitrary multiple of it.',
      'The fastest sanity check: get your VIN-exact diagnosis and cost breakdown from RAPP before you approve any quote. It shows the same three numbers -- parts, labor hours, and a dealer/independent/DIY cost range -- sourced from your car\'s actual specs, not a shop\'s estimate.',
    ],
  },
  {
    slug: 'oil-change-interval-myths',
    title: 'The 3,000-Mile Oil Change Myth (And What Your Car Actually Needs)',
    category: 'Maintenance',
    summary:
      'Most modern engines go 5,000-10,000 miles between changes. Here is how to find your actual interval instead of guessing.',
    readMinutes: 3,
    relatedTemplateCategory: 'oil_service',
    body: [
      'The 3,000-mile rule dates to conventional oil formulations from decades ago. Modern full-synthetic oils and tighter engine tolerances routinely support 5,000-10,000 mile intervals, and many vehicles now use an oil-life monitor that reads actual driving conditions instead of a flat mileage number.',
      'Your owner\'s manual (or the sticker on your driver\'s door jamb) lists the manufacturer interval for your specific engine and oil grade -- that number, not a generic rule of thumb, is the one to follow.',
      'Severe-use conditions (frequent short trips under 10 minutes, towing, extreme heat or cold, dusty roads) shorten the safe interval. If most of your driving fits that profile, follow the manual\'s "severe service" schedule instead of the normal one.',
      'Changing your own oil is one of the lowest-risk, highest-value DIY jobs on this list -- no special tools beyond a wrench, drain pan, and filter wrench, and it typically costs a third of a shop\'s price in parts alone.',
    ],
  },
  {
    slug: 'wiper-blades-when-to-replace',
    title: 'Streaky Wipers? Here\'s How to Tell If It\'s the Blades or the Glass',
    category: 'Maintenance',
    summary:
      'Streaking, skipping, and chatter usually mean the rubber edge has hardened -- a 10-minute, no-tools-beyond-your-hands fix.',
    readMinutes: 2,
    relatedTemplateCategory: 'wiper_blades',
    body: [
      'Wiper rubber hardens and cracks from UV exposure over 6-12 months regardless of mileage, which is why "the blades are only a year old" doesn\'t rule them out as the cause of streaking.',
      'A quick test: run the wipers dry for one pass. If you see a consistent streak along the entire blade length, it\'s almost always the rubber edge, not the glass. Chatter (a juddering, skipping motion) usually means the blade has lost its factory curvature and is no longer applying even pressure.',
      'Most vehicles use a tool-free push-tab connector -- no wrench or screwdriver required, and the whole swap for both blades takes under 10 minutes.',
      'Replace both front blades together even if only one is streaking; they wear at close to the same rate and a mismatched pair often reveals the second failure within weeks.',
    ],
  },
  {
    slug: 'check-engine-light-first-steps',
    title: 'Check Engine Light On? Do This Before You Panic (or Pay for Diagnostics)',
    category: 'Diagnostics',
    summary:
      'A steady light and a flashing light mean very different things. Here is what to check yourself before booking a shop visit.',
    readMinutes: 4,
    body: [
      'A flashing check engine light signals an active misfire that can damage your catalytic converter within minutes of continued driving -- reduce speed and get off the road as soon as safely possible. A steady light is not an emergency and is safe to drive on while you investigate.',
      'The most common trigger by far is a loose or failing gas cap, which sets an EVAP-system code. Tighten the cap until it clicks 3 times and see if the light clears after a few drive cycles before assuming anything is actually broken.',
      'A $15-$25 OBD-II Bluetooth adapter paired with a free phone app reads the exact stored code in under a minute -- that code (e.g. "P0420") is the single most useful piece of information for figuring out what\'s actually wrong, and most auto parts stores will also read it for free.',
      'Once you have a code (or a symptom description even without one), RAPP\'s free diagnosis matches it against your exact VIN and gives you a plain-language root cause plus a fair-price repair estimate before you spend anything on a shop\'s diagnostic fee.',
    ],
  },
  {
    slug: 'airbag-ev-fuel-line-professional-only',
    title: 'Three Systems You Should Never DIY (And Why)',
    category: 'Safety',
    summary:
      'Airbag/SRS, high-voltage EV batteries, and pressurized fuel lines carry injury risk that outweighs any DIY savings. Here is why RAPP refuses to guide you through them.',
    readMinutes: 3,
    body: [
      'Airbag and SRS systems store pyrotechnic charges that can deploy unexpectedly during disassembly, causing severe burns or worse, even with the battery disconnected -- some systems retain enough capacitor charge to fire for minutes afterward.',
      'Hybrid and EV high-voltage battery packs run at 200-800V DC -- roughly 10-40x household voltage -- and improper handling can be fatal. This work requires insulated tools, PPE rated for the voltage class, and manufacturer lockout procedures, not a home garage setup.',
      'Pressurized fuel lines, especially on direct-injection engines, can hold hundreds of PSI even with the engine off. An uncontrolled release can atomize fuel into a flammable mist near hot engine components.',
      'RAPP\'s diagnosis still tells you what\'s wrong and roughly what it should cost -- the step-by-step guide is what gets replaced with a "professional service required" screen and a link to a certified shop, so you still walk in informed instead of guessing.',
    ],
  },
  {
    slug: 'tire-pressure-tpms-explained',
    title: 'TPMS Light On? It\'s Not Always a Slow Leak',
    category: 'Maintenance',
    summary:
      'Temperature swings alone can trigger the TPMS light. Here is how to tell a real leak from a seasonal false alarm.',
    readMinutes: 2,
    relatedTemplateCategory: 'tire_pressure',
    body: [
      'Tire pressure drops roughly 1 PSI for every 10°F the outside temperature falls. A sharp overnight cold snap can trigger the TPMS light on all four tires simultaneously with no actual leak -- that pattern (all four, right after a temperature drop) is the signature of a seasonal false alarm, not a puncture.',
      'A single tire consistently low week after week, especially if it needs air more often than the others, points to a slow leak -- often a small nail or a corroded valve stem, both inexpensive fixes.',
      'Always check and set pressure to the number on your driver\'s door jamb placard, not the number printed on the tire\'s sidewall -- the sidewall number is the tire\'s maximum rating, not your vehicle\'s recommended setting.',
      'After any pressure correction, many vehicles need a manual TPMS relearn procedure (not just driving around) before the warning light clears -- check your owner\'s manual for the reset sequence specific to your vehicle.',
    ],
  },
];

export function getArticleBySlug(slug: string): Article | undefined {
  return ARTICLES.find((a) => a.slug === slug);
}
```

- [ ] **Step 2: Verify it type-checks in isolation**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit src/app/hub/articles.ts 2>&1 | head -20`
Expected: no output (or only pre-existing unrelated project-wide config warnings if run without full project context -- the real gate is the Task 9 `next build`).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/hub/articles.ts
git commit -m "feat(hub): Block 7 Stage 3.2 -- curated Knowledge Hub article content"
```

---

## Task 8: `/hub` index page

**Files:**
- Create: `frontend/src/app/hub/page.tsx`
- Modify: `frontend/src/app/globals.css` (append hub-specific classes; do not remove/reorder existing rules)

**Interfaces:**
- Consumes: `ARTICLES`, `Article` from `./articles` (Task 7).

- [ ] **Step 1: Write the index page**

```tsx
'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ARTICLES, Article } from './articles';

const CATEGORIES: Array<Article['category'] | 'All'> = [
  'All',
  'Maintenance',
  'Diagnostics',
  'Buying a Guide',
  'Safety',
];

export default function HubPage() {
  const [activeCategory, setActiveCategory] = useState<Article['category'] | 'All'>('All');

  const visible =
    activeCategory === 'All'
      ? ARTICLES
      : ARTICLES.filter((a) => a.category === activeCategory);

  return (
    <main className="hub-page">
      <div className="hub-header">
        <h1>Knowledge Hub</h1>
        <p className="hub-subtitle">
          Straight answers on car care, diagnostics, and fair pricing -- verified against OEM
          service data, not guessed.
        </p>
      </div>

      <div className="hub-filter-row" role="tablist" aria-label="Filter articles by category">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            role="tab"
            aria-selected={activeCategory === cat}
            className={`hub-filter-chip${activeCategory === cat ? ' hub-filter-chip-active' : ''}`}
            onClick={() => setActiveCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="hub-grid">
        {visible.map((article) => (
          <Link key={article.slug} href={`/hub/${article.slug}`} className="hub-card">
            <span className="hub-card-category">{article.category}</span>
            <h2 className="hub-card-title">{article.title}</h2>
            <p className="hub-card-summary">{article.summary}</p>
            <span className="hub-card-meta">{article.readMinutes} min read</span>
          </Link>
        ))}
      </div>

      <Link href="/" className="hub-back-link">
        Back to RAPP
      </Link>
    </main>
  );
}
```

- [ ] **Step 2: Append vanilla-CSS classes to `globals.css`**

Append at the end of `frontend/src/app/globals.css` (uses existing design tokens `--bg-primary`, `--accent-orange`, etc. -- read the top of the file first to confirm exact token names before pasting, they must match verbatim):

```css
/* Knowledge Hub (Block 7 / Stage 3.2) */
.hub-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 2rem 1.5rem 4rem;
}

.hub-header {
  margin-bottom: 2rem;
}

.hub-header h1 {
  font-size: clamp(1.75rem, 4vw, 2.5rem);
  font-weight: 700;
}

.hub-subtitle {
  max-width: 65ch;
  color: var(--text-secondary, rgba(255, 255, 255, 0.7));
  margin-top: 0.5rem;
}

.hub-filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.hub-filter-chip {
  min-height: 48px;
  padding: 0 1rem;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(15, 23, 42, 0.6);
  color: inherit;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.hub-filter-chip-active {
  border-color: var(--accent-orange, #f59e0b);
  background: rgba(245, 158, 11, 0.12);
  color: var(--accent-orange, #f59e0b);
}

.hub-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.25rem;
}

.hub-card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.25rem;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(12px);
  text-decoration: none;
  color: inherit;
  min-height: 48px;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.hub-card:hover,
.hub-card:focus-visible {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px -10px rgba(0, 0, 0, 0.4);
  outline: 2px solid var(--accent-orange, #f59e0b);
  outline-offset: 2px;
}

.hub-card-category {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--accent-orange, #f59e0b);
}

.hub-card-title {
  font-size: 1.1rem;
  font-weight: 600;
}

.hub-card-summary {
  color: var(--text-secondary, rgba(255, 255, 255, 0.7));
  font-size: 0.9rem;
  max-width: 65ch;
}

.hub-card-meta {
  margin-top: auto;
  font-size: 0.8rem;
  color: var(--text-secondary, rgba(255, 255, 255, 0.5));
}

.hub-back-link {
  display: inline-flex;
  align-items: center;
  min-height: 48px;
  margin-top: 2rem;
  color: var(--accent-orange, #f59e0b);
  text-decoration: none;
}
```

- [ ] **Step 3: Commit**

Hold this commit -- combine with Task 9 (they share the `globals.css` diff and the article-detail page reuses the same visual language). Commit once at the end of Task 9.

---

## Task 9: `/hub/[slug]` article detail page

**Files:**
- Create: `frontend/src/app/hub/[slug]/page.tsx`
- Modify: `frontend/src/app/globals.css` (append article-prose classes)

**Interfaces:**
- Consumes: `ARTICLES`, `getArticleBySlug` from `../articles` (Task 7).

- [ ] **Step 1: Write the detail page**

```tsx
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ARTICLES, getArticleBySlug } from '../articles';

export function generateStaticParams() {
  return ARTICLES.map((a) => ({ slug: a.slug }));
}

export default function ArticlePage({ params }: { params: { slug: string } }) {
  const article = getArticleBySlug(params.slug);
  if (!article) {
    notFound();
  }

  return (
    <main className="hub-article-page">
      <Link href="/hub" className="hub-back-link">
        Back to Knowledge Hub
      </Link>

      <span className="hub-card-category">{article.category}</span>
      <h1 className="hub-article-title">{article.title}</h1>
      <p className="hub-article-meta">{article.readMinutes} min read</p>

      <div className="hub-article-body">
        {article.body.map((paragraph, i) => (
          <p key={i}>{paragraph}</p>
        ))}
      </div>

      {article.relatedTemplateCategory && (
        <div className="hub-article-cta">
          <p>Ready to fix this yourself? Get a VIN-exact diagnosis and step-by-step guide.</p>
          <Link href="/" className="hub-article-cta-btn">
            Start My Diagnosis
          </Link>
        </div>
      )}
    </main>
  );
}
```

- [ ] **Step 2: Append article-prose classes to `globals.css`**

```css
.hub-article-page {
  max-width: 680px;
  margin: 0 auto;
  padding: 2rem 1.5rem 4rem;
}

.hub-article-title {
  font-size: clamp(1.75rem, 4vw, 2.25rem);
  font-weight: 700;
  margin: 0.5rem 0;
}

.hub-article-meta {
  color: var(--text-secondary, rgba(255, 255, 255, 0.5));
  font-size: 0.85rem;
  margin-bottom: 1.5rem;
}

.hub-article-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 65ch;
  line-height: 1.7;
}

.hub-article-cta {
  margin-top: 2.5rem;
  padding: 1.5rem;
  border-radius: 12px;
  border: 1px solid rgba(245, 158, 11, 0.3);
  background: rgba(245, 158, 11, 0.08);
}

.hub-article-cta-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  min-width: 48px;
  padding: 0 1.5rem;
  margin-top: 0.75rem;
  border-radius: 8px;
  background: var(--accent-orange, #f59e0b);
  color: #0f172a;
  font-weight: 600;
  text-decoration: none;
}
```

- [ ] **Step 3: Build and manually verify**

```bash
cd frontend && ./node_modules/.bin/next build
```
Expected: compiles clean, zero TypeScript/ESLint errors, `/hub` and `/hub/[slug]` appear in the route summary output (static-generated, matching `generateStaticParams`).

Then start the dev server and check both routes render correctly in-browser:
```bash
./node_modules/.bin/next dev -p 3000
```
Visit `http://localhost:3000/hub` -- confirm the category filter chips work and cards are clickable with visible focus rings (Tab key). Visit `http://localhost:3000/hub/oil-change-interval-myths` -- confirm the article renders and the "Start My Diagnosis" CTA links to `/`. Visit `http://localhost:3000/hub/does-not-exist` -- confirm it 404s via `notFound()`.

- [ ] **Step 4: Commit Tasks 8-9 together**

```bash
git add frontend/src/app/hub/page.tsx frontend/src/app/hub/[slug]/page.tsx frontend/src/app/globals.css
git commit -m "feat(hub): Block 7 Stage 3.2 -- /hub index and article detail pages"
```

---

## Task 10: Docs & tracking updates (CLAUDE.md 4-step protocol, Step 4)

**Files:**
- Modify: `docs/implementation/imp.md`
- Modify: `docs/MODEL_ASSIGNMENT_GUIDE.md`

- [ ] **Step 1: Check off Stage 3.1 and 3.2 in `imp.md` §4**

In the `### Stage 3` section, change:
```
#### 3.1 [ ] Maintenance Content (Jules)
```
to
```
#### 3.1 [x] Maintenance Content (Claude Code / Gemini 3.5 Flash)
```
and
```
#### 3.2 [ ] Knowledge Hub (Antigravity, Gemini Flash)
```
to
```
#### 3.2 [x] Knowledge Hub (Claude Code / Gemini 3.5 Flash)
```

- [ ] **Step 2: Update the §3 gap table**

Change the two rows:
```
| **Maintenance Content (Wipers/Oil/etc.)**| Retention & Value | §7, Stage 3 #9 | 🟡 Retention |
| **Knowledge Hub & Article CM** | Content & Growth | §7, Stage 3 #10 | 🟡 Growth |
```
to:
```
| **[x] Maintenance Content (Wipers/Oil/etc.)**| Retention & Value | §7, Stage 3 #9 | ✅ **COMPLETED (Block 7)** |
| **[x] Knowledge Hub & Article CM** | Content & Growth | §7, Stage 3 #10 | ✅ **COMPLETED (Block 7)** |
```
And update the progress summary line (`Progress: 11 / 15 items complete (73%)`) to `13 / 15 items complete (87%)`, appending `Block 7 (Maintenance Content, Knowledge Hub)` to the completed-blocks list.

- [ ] **Step 3: Append a Section 6 execution-log row**

Add a new row to the table in `## 6. Active Execution Log & AI Session Audit Trail` documenting: date, agent/model actually used, "Block 7: Maintenance Content & Knowledge Hub (Stages 3.1 & 3.2)", the files listed in this plan's File Structure section, the verification commands run and their results (pytest count, ruff/black/mypy clean, next build clean), and next-step handoff to Block 8 (Referral Program & Recall/TSB Watch) per `MODEL_ASSIGNMENT_GUIDE.md`.

- [ ] **Step 4: Flip the Block 7 row in `MODEL_ASSIGNMENT_GUIDE.md`**

Change:
```
| **Block 7** | **High-Velocity Content & SEO Hub**<br>...
```
to:
```
| **Block 7** ✅ **COMPLETED** | **High-Velocity Content & SEO Hub**<br>...
```
(matching the exact format of the Block 1-6 rows above it).

- [ ] **Step 5: Commit docs as a separate commit from code**

```bash
git add docs/implementation/imp.md docs/MODEL_ASSIGNMENT_GUIDE.md
git commit -m "docs: mark Block 7 complete (Stages 3.1 & 3.2)"
```

---

## Self-Review

**Spec coverage:**
- Stage 3.1 ("Write deterministic step templates ... wiper changes, fluid top-offs, oil changes, bulb replacements, and tire pressure adjustments") — `oil_service` already shipped pre-Block-7; Tasks 1-4 add the remaining four. Covered.
- Stage 3.2 ("Create `/hub` section hosting curated markdown articles, guides, and embeds") — Tasks 7-9 build the index + detail routes with 6 curated articles across all 4 categories (2 tie back to new Stage-3.1 templates, 1 ties to the Safety-redirect feature from Block 2, 1 to the outcome-capture/social-proof pitch from Block 3). "Curated video embeds" from North Star §7 explicitly deferred — no article currently needs one; adding an `embedUrl?: string` field to `Article` later is a one-line, backward-compatible extension, not scope this plan needs to pre-build (YAGNI).
- Global Constraints row on `_KEYWORD_RULES` ordering is directly exercised by Task 6's regression test.
- Pinned Claude/Gemini contract (`CLAUDE.md`) — respected: `articles.ts` lives under `app/hub/`, not `src/lib/*.ts`; no `data-testid` renamed; no localStorage keys touched.

**Placeholder scan:** none found — every step has literal code/commands, no "TBD"/"handle edge cases" language.

**Type consistency:** `Article` interface (Task 7) fields (`slug`, `title`, `category`, `summary`, `readMinutes`, `relatedTemplateCategory`, `body`) are used identically in Task 8 (`hub-card-*` rendering) and Task 9 (`hub-article-*` rendering) with no renamed fields. `RepairTemplate.category` string values (`wiper_blades`, `fluid_topoff`, `bulb_replacement`, `tire_pressure`) are consistent across Tasks 1-6 (template definition, pricing lookup, keyword rule, test assertions).
