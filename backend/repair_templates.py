"""Curated repair-procedure templates, keyed by OBD-II code or symptom keyword.

Used as the middle rung of the repair-content ladder: Gemini (when
``GEMINI_API_KEY`` is set) produces the most tailored steps, RAG retrieval is
tried next, and this module is the deterministic, zero-cost fallback below
that — real, followable procedures rather than the old generic 10-step
placeholder. See ``select_template`` for the matching logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_CODE_TOKEN_RE = re.compile(r"\b([PBCU]\d{4})\b", re.IGNORECASE)

_GENERIC_CITATION = (
    "RAPP curated repair procedure -- general reference, not sourced from "
    "a vehicle-specific OEM manual. Verify torque specs and part fitment "
    "against your vehicle's official service documentation before performing "
    "this repair."
)


@dataclass(frozen=True)
class RepairTemplate:
    category: str
    title: str
    steps: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    parts: list[str] = field(default_factory=list)


IGNITION_MISFIRE = RepairTemplate(
    category="ignition_misfire",
    title="Ignition Coil & Spark Plug Replacement",
    steps=[
        "Confirm the vehicle is parked on level ground with the parking brake set and the engine fully cooled for at least 30 minutes.",
        "Disconnect the negative battery terminal using a 10mm wrench and isolate the cable so it cannot contact the terminal post.",
        "Put on safety glasses and nitrile gloves before working near the ignition system.",
        "Remove the engine cover by releasing its retaining clips or loosening the mounting bolts with a 10mm socket.",
        "Locate the ignition coil pack for the affected cylinder, identified from the misfire code, and disconnect its electrical connector by pressing the lock tab and pulling straight up.",
        "Remove the coil pack mounting bolt with a 10mm socket and a 3-inch extension, then pull the coil straight up and out of the spark plug well.",
        "Using a spark plug socket (typically 5/8 inch) with a long extension, loosen and remove the spark plug from the affected cylinder.",
        "Inspect the removed plug for fouling, oil contamination, or excessive electrode wear — this confirms whether the plug or coil was the root cause.",
        "Gap the new spark plug to the manufacturer specification (commonly 0.044 in / 1.1 mm) using a gap tool before installation.",
        "Hand-thread the new spark plug into the cylinder head to avoid cross-threading, then Torque the spark plug to 15 ft-lbs (20 Nm) on aluminum heads using a torque wrench.",
        "Apply a thin layer of dielectric grease inside the coil boot to prevent moisture intrusion and ease future removal.",
        "Seat the new or original coil pack fully into the spark plug well and Torque the coil mounting bolt to 7.5 ft-lbs (10 Nm).",
        "Reconnect the coil's electrical connector until an audible click confirms it is locked.",
        "Repeat the removal and replacement steps for any additional cylinders flagged by multiple misfire codes.",
        "Reinstall the engine cover and reconnect the negative battery terminal, tightening the clamp bolt securely.",
        "Clear the stored misfire code with an OBD-II scanner and start the engine, listening for smooth idle with no rough running.",
        "Take the vehicle on a mixed-speed test drive of 10-15 minutes and confirm the check engine light does not return.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Ignition coil pack ($45-$90 each)",
        "Spark plug set ($8-$20 per plug)",
        "Dielectric grease ($5)",
    ],
)

OXYGEN_SENSOR = RepairTemplate(
    category="oxygen_sensor",
    title="Oxygen (O2) Sensor Replacement",
    steps=[
        "Allow the exhaust system to cool completely for at least 45 minutes before starting — O2 sensors are mounted directly on hot exhaust piping.",
        "Raise the vehicle on jack stands rated for its weight, placed at the manufacturer's frame jack points, and chock the rear wheels.",
        "Disconnect the negative battery terminal with a 10mm wrench to prevent false codes while the sensor circuit is open.",
        "Trace the exhaust piping to locate the faulty sensor's position (upstream/pre-catalyst or downstream/post-catalyst) as indicated by the fault code.",
        "Disconnect the sensor's electrical connector by releasing the locking tab, then free the wiring harness from any retaining clips along the pipe.",
        "Apply penetrating oil to the sensor's threads and let it soak for 10 minutes if the sensor shows signs of corrosion.",
        "Remove the sensor using an oxygen sensor socket or a 22mm wrench, turning counterclockwise; use steady, even pressure to avoid rounding the hex.",
        "Compare the new sensor's connector and thread pitch to the original before installation to confirm correct fitment.",
        "Apply anti-seize compound to the new sensor's threads only, avoiding the sensor tip and slots.",
        "Thread the new sensor in by hand to avoid cross-threading, then Torque the sensor to 30-35 ft-lbs (40-47 Nm) using a wrench or socket.",
        "Route the new sensor's wiring harness along the same path as the original and secure it in the factory retaining clips, keeping it clear of moving parts and heat sources.",
        "Reconnect the sensor's electrical connector until it clicks into place.",
        "Reconnect the negative battery terminal and lower the vehicle off the jack stands.",
        "Clear the stored oxygen sensor code with an OBD-II scanner.",
        "Start the engine and allow it to idle for 2-3 minutes, then take a 10-15 minute mixed-speed test drive to complete a full sensor monitor cycle and confirm the code does not return.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Oxygen sensor ($40-$120)",
        "Anti-seize compound ($6)",
        "Penetrating oil ($6)",
    ],
)

FUEL_TRIM_LEAN = RepairTemplate(
    category="fuel_trim_lean",
    title="Vacuum Leak & Fuel Trim Correction",
    steps=[
        "Confirm the engine is cold before beginning to avoid burns from hot intake components.",
        "Disconnect the negative battery terminal with a 10mm wrench for safety while working near the intake.",
        "Visually inspect all vacuum hoses in the engine bay for cracking, disconnection, or collapse, paying close attention to the PCV hose and brake booster line.",
        "Inspect the air intake boot between the air filter box and throttle body for tears or a loose clamp, using a flashlight to check the underside.",
        "Remove the engine cover by loosening its retaining bolts with a 10mm socket to access the intake manifold gasket area.",
        "Check the intake manifold gasket surface for signs of a leak, such as a whistling sound at idle or visible carbon staining around the gasket edge.",
        "If a vacuum hose is cracked, cut a replacement section of hose to matching length and diameter and clamp it in place with new hose clamps.",
        "If the intake boot clamp is loose, tighten it with a flathead screwdriver or 7mm nut driver until snug, without over-compressing the rubber.",
        "If the intake manifold gasket is suspect, remove the manifold retaining bolts with the appropriate socket, working in a star pattern to release tension evenly.",
        "Clean the gasket mating surfaces on both the manifold and cylinder head with a plastic scraper, avoiding any dropped debris into the intake ports.",
        "Install the new intake manifold gasket dry (no sealant unless specified) and reinstall the manifold, then Torque the manifold bolts to 15 ft-lbs (20 Nm) in a star pattern.",
        "Reconnect all vacuum hoses to their original ports and secure the intake boot clamp.",
        "Reconnect the negative battery terminal and reinstall the engine cover.",
        "Clear the stored lean-condition code with an OBD-II scanner.",
        "Start the engine and let it idle for 5 minutes, listening for any hissing that indicates a remaining leak, then test-drive to confirm fuel trims stabilize and the code does not return.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Vacuum hose, per foot ($3-$8)",
        "Intake manifold gasket ($15-$45)",
        "Hose clamps, pack of 10 ($6)",
    ],
)

CATALYTIC_CONVERTER = RepairTemplate(
    category="catalytic_converter",
    title="Catalytic Converter Inspection & Replacement",
    steps=[
        "Allow the exhaust system to cool for at least 45 minutes before beginning work.",
        "Raise the vehicle on jack stands at the manufacturer's frame jack points and chock the wheels remaining on the ground.",
        "Disconnect the negative battery terminal with a 10mm wrench.",
        "Locate the catalytic converter between the exhaust manifold and the muffler, and inspect it and its heat shield for physical damage, rattling internal debris, or exhaust leaks at the flange joints.",
        "Apply penetrating oil to the flange bolts on both sides of the converter and let it soak for 10-15 minutes, as these bolts are frequently corroded.",
        "Support the converter's weight with a jack or transmission stand before removing any fasteners.",
        "Remove the upstream flange bolts using a 14mm or 15mm wrench, working slowly to avoid snapping a corroded stud.",
        "Remove the downstream flange bolts in the same manner, then lower the old converter clear of the vehicle.",
        "Compare the new converter's flange pattern and oxygen sensor bungs to the original to confirm correct fitment.",
        "Position the new converter with a new gasket at each flange joint, and hand-thread all bolts before tightening any of them fully.",
        "Torque the upstream flange bolts to 30 ft-lbs (40 Nm) in a criss-cross pattern to seat the gasket evenly.",
        "Torque the downstream flange bolts to 30 ft-lbs (40 Nm) in the same criss-cross pattern.",
        "Transfer the oxygen sensors from the old converter to the new one if they are reused, applying anti-seize to the threads and torquing to 30-35 ft-lbs (40-47 Nm).",
        "Reconnect all oxygen sensor electrical connectors and secure the wiring harness in its factory clips.",
        "Reconnect the negative battery terminal and lower the vehicle.",
        "Clear the catalyst efficiency code with an OBD-II scanner and take a mixed highway/city test drive of at least 15 minutes to complete the catalyst monitor and confirm the code does not return.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Catalytic converter, direct-fit ($150-$400)",
        "Flange gaskets, pair ($10)",
        "Penetrating oil ($6)",
    ],
)

EVAP_LEAK = RepairTemplate(
    category="evap_leak",
    title="EVAP System Leak Diagnosis & Repair",
    steps=[
        "Confirm the fuel filler cap is fully tightened (3-4 audible clicks) as the single most common cause of a small EVAP leak code.",
        "If the code persists after a confirmed-tight cap, disconnect the negative battery terminal with a 10mm wrench before further inspection.",
        "Locate the EVAP purge valve, typically mounted near the intake manifold, and inspect its electrical connector and vacuum hose for damage.",
        "Locate the EVAP vent valve, typically near the fuel tank or behind a rear wheel well liner, and inspect its connector and hose fittings.",
        "Trace the EVAP hoses from the fuel tank to the charcoal canister, checking for cracks, disconnection, or rodent damage along the entire run.",
        "Inspect the fuel tank filler neck and its rubber seal to the tank for cracking, especially on vehicles over 8 years old.",
        "If a hose is cracked, cut a replacement of matching diameter EVAP-rated hose (not standard vacuum hose, which can collapse under fuel vapor) to length.",
        "If the purge or vent valve is confirmed faulty, disconnect its electrical connector and remove its mounting bracket bolt with a 10mm socket.",
        "Install the new valve, ensuring the flow direction arrow (if present) matches the original orientation, then Torque the mounting bracket bolt to 44 in-lbs (5 Nm) and reconnect the electrical connector until it clicks.",
        "Reconnect all EVAP hoses to their original routing and secure any retaining clips.",
        "Reconnect the negative battery terminal.",
        "Clear the stored EVAP code with an OBD-II scanner.",
        "Refuel to at least half a tank if below that level, as the EVAP monitor requires a minimum fuel level to run.",
        "Complete several drive cycles including a cold start, and confirm the EVAP monitor completes with no code return — this can take 1-3 drive cycles to fully verify.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "EVAP purge valve ($25-$60)",
        "EVAP vent valve ($20-$70)",
        "EVAP-rated hose, per foot ($4)",
    ],
)

BRAKES = RepairTemplate(
    category="brakes",
    title="Brake Pad & Rotor Replacement",
    steps=[
        "Park on level ground, set the parking brake, and place wheel chocks behind the wheels remaining on the ground.",
        "Loosen the lug nuts on the wheel to be serviced by a quarter turn while the wheel is still on the ground, using a 19mm or 21mm socket (confirm size for your vehicle).",
        "Raise the vehicle with a floor jack at the manufacturer's jack point and support it on a jack stand before doing any work underneath.",
        "Remove the lug nuts fully and take off the wheel to expose the brake caliper and rotor.",
        "Locate the caliper slide pin bolts, typically 12mm or 14mm, and remove them, then pivot the caliper up and off the rotor, supporting it with a bungee cord or wire so it does not hang by the brake hose.",
        "Remove the caliper bracket bolts, typically 17mm or 18mm, using a breaker bar if they are torqued tight, and set the bracket aside.",
        "Remove the old brake pads from the caliper bracket and inspect the rotor surface for scoring, grooving, or uneven wear.",
        "If the rotor is worn beyond minimum thickness (stamped on the rotor edge) or has deep grooves, remove it from the hub — it may require a light tap with a rubber mallet if rust-seized.",
        "Clean the hub mounting surface with a wire brush before installing the new rotor to prevent runout and pedal pulsation.",
        "Install the new rotor onto the hub, followed by the caliper bracket, and Torque the bracket bolts to 80 ft-lbs (108 Nm) in a criss-cross pattern.",
        "Compress the caliper piston back into its bore using a caliper piston tool or large C-clamp, checking that the brake fluid reservoir does not overflow as you do so.",
        "Install the new brake pads into the caliper bracket with anti-squeal shims facing the correct direction, then pivot the caliper back over the rotor.",
        "Reinstall the caliper slide pin bolts and Torque them to 25 ft-lbs (34 Nm).",
        "Mount the wheel, hand-tighten the lug nuts, then lower the vehicle and Torque the lug nuts to 80-100 ft-lbs (108-135 Nm) in a star pattern.",
        "Pump the brake pedal several times before driving to seat the new pads against the rotor and restore normal pedal feel.",
        "Perform a brake pad break-in by making 8-10 moderate stops from about 35 mph with cool-down time between each, avoiding hard braking for the first 100 miles.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Brake pad set ($30-$90)",
        "Brake rotors, pair ($60-$150)",
        "Brake caliper grease ($6)",
    ],
)

BRAKES_DRUM = RepairTemplate(
    category="brakes_drum",
    title="Rear Drum Brake Shoe Replacement",
    steps=[
        "Park on level ground, set the parking brake, and place wheel chocks under the front wheels before working on the rear.",
        "Loosen the rear lug nuts by a quarter turn while the wheel is still on the ground, using a 19mm or 21mm socket (confirm size for your vehicle).",
        "Raise the vehicle at the manufacturer's rear jack point and support it on a jack stand before removing the wheel.",
        "Remove the lug nuts fully, take off the wheel, and pull the brake drum straight off the hub — if seized, tap the drum evenly around its edge with a rubber mallet, or back off the self-adjuster through the access hole with a brake spoon.",
        "Photograph the spring and hardware layout before disassembly — drum brake hardware orientation matters and is easy to get backward on reassembly.",
        "Using a brake spring pliers or shoe hold-down spring tool, remove the hold-down springs, pins, and cups securing each shoe to the backing plate.",
        "Disconnect the parking brake cable from the lever on the rear (secondary) shoe using needle-nose pliers.",
        "Remove the shoe return springs and the adjuster assembly, then lift both shoes away from the backing plate as a set.",
        "Clean the backing plate with brake cleaner and inspect the wheel cylinder for any sign of brake fluid leaking past its boots — a leaking wheel cylinder must be replaced before proceeding.",
        "Apply a thin layer of high-temperature brake grease to the six raised contact pads on the backing plate where the shoes ride.",
        "Transfer the parking brake lever to the new secondary shoe, then install the new shoes onto the backing plate in the same orientation as the originals, securing them with the hold-down springs, pins, and cups.",
        "Reconnect the shoe return springs and the adjuster assembly, and reconnect the parking brake cable to the lever.",
        "Turn the adjuster to expand the shoes until the drum can just be installed with slight resistance, matching the original drum's inner diameter.",
        "Reinstall the drum, wheel, and lug nuts; lower the vehicle and Torque the lug nuts to 80-100 ft-lbs (108-135 Nm) in a star pattern.",
        "Pump the brake pedal firmly several times and apply the parking brake a few times to let the self-adjuster set shoe clearance.",
        "Test drive at low speed first, confirming firm pedal feel and no dragging or pulling, before returning to normal driving.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Brake shoe set ($25-$70)",
        "Brake drum, each ($35-$90)",
        "Brake hardware kit (springs/pins/adjuster) ($10-$25)",
        "High-temperature brake grease ($6)",
    ],
)

SUSPENSION = RepairTemplate(
    category="suspension",
    title="Strut & Shock Absorber Replacement",
    steps=[
        "Park on level ground and loosen the lug nuts of the wheel to be serviced by a quarter turn while still on the ground.",
        "Raise the vehicle with a floor jack and support it securely on a jack stand at the frame rail, then remove the wheel.",
        "Locate the sway bar end link at the base of the strut and remove its retaining nut with a 15mm wrench while holding the stud with an Allen key to prevent spinning.",
        "Disconnect the ABS wheel speed sensor wire and brake hose bracket from the strut body, noting their routing for reinstallation.",
        "Remove the two or three bolts securing the strut to the steering knuckle, typically 18mm or 21mm, supporting the knuckle so it does not hang by the brake hose once free.",
        "From the engine bay or trunk, remove the strut mount retaining nuts at the top of the strut tower, typically three 14mm nuts.",
        "Carefully lower the strut assembly out from under the wheel well.",
        "If reusing the spring, compress it with a spring compressor tool rated for the load before removing the top strut mount nut — never attempt this without a compressor, as the stored spring energy is dangerous.",
        "Transfer the spring, upper mount, and bump stop to the new strut in the same orientation as the original, and release the spring compressor slowly once the top nut is seated.",
        "Position the new strut assembly up through the strut tower and hand-thread the upper mount nuts.",
        "Torque the upper strut mount nuts to 18 ft-lbs (24 Nm).",
        "Align the strut with the steering knuckle, insert the lower mounting bolts, and Torque them to 74 ft-lbs (100 Nm).",
        "Reconnect the sway bar end link and Torque its nut to 15 ft-lbs (20 Nm), then reconnect the ABS sensor wire and brake hose bracket.",
        "Reinstall the wheel, hand-tighten the lug nuts, lower the vehicle, and Torque the lug nuts to 80-100 ft-lbs (108-135 Nm) in a star pattern.",
        "Repeat for the opposite side if replacing as a pair, which is strongly recommended for even handling.",
        "Have the vehicle's wheel alignment checked within the next few days, as strut replacement can shift alignment settings.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Strut assembly, each ($80-$220)",
        "Sway bar end link ($15-$35)",
        "Spring compressor rental (varies)",
    ],
)

CHARGING_BATTERY = RepairTemplate(
    category="charging_battery",
    title="Battery & Charging System Diagnosis",
    steps=[
        "Put on safety glasses before working near the battery, as it can contain corrosive acid and vent hydrogen gas.",
        "With the engine off, use a digital multimeter set to DC volts to measure battery voltage at the terminals — a healthy resting battery reads 12.4-12.7V.",
        "Start the engine and measure voltage again at the battery terminals — a properly functioning alternator should show 13.5-14.7V.",
        "If voltage stays near 12V with the engine running, the alternator or its drive belt is a likely cause; if voltage exceeds 15V, the voltage regulator may be faulty.",
        "Inspect the battery terminals and cable ends for corrosion (white or blue-green buildup) which can cause poor connection and slow cranking.",
        "Disconnect the negative terminal first, then the positive terminal, using a 10mm wrench, to safely remove the battery.",
        "Clean corroded terminals and cable ends with a wire brush and a baking-soda-and-water solution, rinsing and drying thoroughly afterward.",
        "Inspect the alternator drive belt for cracking, glazing, or excessive play, and check that the alternator pulley spins freely without noise.",
        "If replacing the battery, confirm the new battery matches the original's group size and cold-cranking amp rating.",
        "Install the new or cleaned battery, connecting the positive terminal first and then the negative terminal, tightening each clamp securely by hand and then with a wrench.",
        "Apply a thin layer of dielectric grease or terminal protectant spray to both terminals to slow future corrosion.",
        "If the alternator itself tested faulty (low or no charging voltage with a known-good belt and battery), remove its mounting and adjustment bolts, disconnect the electrical connector and wiring harness, and remove the drive belt before lifting the alternator out.",
        "Install the replacement alternator in the reverse order, Torque the mounting bolts to the manufacturer specification (commonly 30-35 ft-lbs / 40-47 Nm), and reinstall the drive belt.",
        "Start the engine and confirm charging voltage now reads 13.5-14.7V at idle.",
        "Clear any stored charging-system codes and drive the vehicle to confirm no warning light returns.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Battery, group size varies ($90-$220)",
        "Alternator ($120-$350)",
        "Terminal protectant spray ($6)",
    ],
)

COOLING_SYSTEM = RepairTemplate(
    category="cooling_system",
    title="Thermostat & Cooling System Service",
    steps=[
        "Confirm the engine is fully cool to the touch — never open a cooling system on a hot engine, as pressurized coolant can cause severe burns.",
        "Disconnect the negative battery terminal with a 10mm wrench.",
        "Place a drain pan beneath the radiator's drain valve or lower radiator hose, then open the drain valve or loosen the hose clamp to drain the coolant into the pan.",
        "Once draining slows, locate the thermostat housing, typically where the upper radiator hose meets the engine block or cylinder head.",
        "Loosen the hose clamp on the upper radiator hose at the thermostat housing and disconnect the hose.",
        "Remove the thermostat housing bolts, typically 10mm, and lift the housing away, noting the thermostat's orientation (spring side typically faces into the engine).",
        "Remove the old thermostat and its gasket or O-ring, then clean the housing and engine mating surfaces of any old gasket material with a plastic scraper.",
        "Install the new thermostat in the same orientation as the original, with a new gasket or O-ring seated in its groove.",
        "Reinstall the thermostat housing and Torque the housing bolts to 89 in-lbs (10 Nm) — these are frequently plastic or aluminum and easy to overtighten.",
        "Reconnect the upper radiator hose and tighten the hose clamp securely.",
        "Close the radiator drain valve or fully reseat the lower hose clamp.",
        "Refill the cooling system with the manufacturer-specified coolant mixture through the radiator or coolant reservoir, adding slowly to allow air to escape.",
        "Leave the radiator cap off (or reservoir cap loose) and start the engine, allowing it to idle and reach operating temperature so the thermostat opens and purges trapped air from the system.",
        "Top off the coolant level once air is purged and the level stabilizes, then reinstall the cap.",
        "Reconnect the negative battery terminal and monitor the temperature gauge on a test drive to confirm normal operating temperature is reached and maintained.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Thermostat ($12-$35)",
        "Coolant, per gallon ($15-$25)",
        "Thermostat gasket/O-ring ($5)",
    ],
)

OIL_SERVICE = RepairTemplate(
    category="oil_service",
    title="Engine Oil & Filter Change",
    steps=[
        "Warm the engine for 3-5 minutes so the oil flows more freely and carries contaminants out during draining, then shut it off.",
        "Raise the vehicle on jack stands or drive-up ramps rated for its weight, ensuring it is level.",
        "Place a drain pan beneath the oil pan's drain plug, then loosen the plug with the correct socket (commonly 14mm or 17mm) and remove it by hand once loose.",
        "Allow the oil to fully drain for at least 5 minutes, then clean and reinstall the drain plug with a new crush washer if the plug uses one.",
        "Torque the drain plug to the manufacturer specification, typically 25-35 ft-lbs (34-47 Nm) — overtightening strips the pan threads.",
        "Locate the oil filter, using an oil filter wrench sized for the filter housing, and turn it counterclockwise to remove; be prepared for residual oil to spill.",
        "Wipe the filter mounting surface clean with a shop rag and confirm the old filter's rubber gasket came off with it and did not stick to the engine.",
        "Apply a thin film of fresh oil to the new filter's gasket before installation to ensure a proper seal.",
        "Hand-tighten the new filter until the gasket contacts the mounting surface, then turn an additional three-quarters turn by hand — do not use a wrench to over-tighten.",
        "Lower the vehicle and locate the oil fill cap on the top of the engine.",
        "Add the manufacturer-specified oil grade and quantity using a funnel, checking the dipstick level as you approach the full mark.",
        "Start the engine and let it idle for one minute, checking beneath the vehicle for leaks at the drain plug and filter.",
        "Shut off the engine, wait 2 minutes for the oil to settle, and recheck the dipstick level, topping off if needed.",
        "Reset the oil life monitor if the vehicle has one, following the manufacturer's dashboard reset procedure.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Engine oil, per manufacturer spec ($25-$60)",
        "Oil filter ($8-$20)",
        "Drain plug crush washer ($1)",
    ],
)

EXHAUST = RepairTemplate(
    category="exhaust",
    title="Exhaust Section Replacement / Cat-Back Install",
    steps=[
        "Allow the exhaust system to cool for at least 45 minutes before beginning.",
        "Raise the vehicle on jack stands at the frame rails, ensuring clearance to work along the full exhaust length.",
        "Apply penetrating oil to all exhaust hangers and flange bolts to be disturbed, and let it soak for 10-15 minutes.",
        "Locate the flange joint just behind the catalytic converter (for a cat-back install) or at the section to be replaced, and remove the flange bolts with a 14mm or 15mm wrench.",
        "Support the exhaust section with a floor jack or exhaust stand before releasing any rubber hangers, as sections can be heavier than expected.",
        "Work down the exhaust, releasing each rubber isolator hanger by pulling the hanger tab free of its bracket — a spray lubricant makes stubborn hangers easier to release.",
        "Remove the old exhaust section fully once all hangers and flange bolts are free.",
        "Dry-fit the new exhaust section, starting from the front flange and working back, hanging each rubber isolator loosely without full alignment yet.",
        "Install a new flange gasket at the connection point and hand-thread the flange bolts before tightening any fully.",
        "Adjust the entire exhaust system by hand so it hangs centered with even clearance from the frame, floor pan, and fuel tank at every point.",
        "Torque the flange bolts to 30 ft-lbs (40 Nm) once alignment is confirmed.",
        "Push each rubber hanger fully onto its bracket, seating it completely to avoid rattling.",
        "Lower the vehicle and start the engine, listening closely for exhaust leaks (a hissing or popping sound) at each joint.",
        "Take a short test drive over varied road surfaces and re-check underneath for any contact points or unusual vibration.",
    ],
    citations=[_GENERIC_CITATION],
    parts=[
        "Cat-back exhaust section ($150-$500)",
        "Exhaust flange gasket ($8)",
        "Rubber exhaust hangers, each ($6)",
    ],
)

WHEEL_SPEED_ABS = RepairTemplate(
    category="wheel_speed_abs",
    title="ABS Wheel Speed Sensor Replacement",
    steps=[
        "Park on level ground, set the parking brake, and loosen the lug nuts of the affected wheel by a quarter turn while still on the ground.",
        "Raise the vehicle on a jack stand at the frame rail and remove the wheel to expose the hub and sensor.",
        "Disconnect the negative battery terminal with a 10mm wrench before disturbing any wiring.",
        "Trace the wheel speed sensor wiring from the hub area back along the suspension to its electrical connector, and disconnect it by releasing the locking tab.",
        "Remove the sensor wiring from its retaining clips along the suspension arm, noting the exact routing for reinstallation.",
        "Remove the sensor's single mounting bolt, typically 10mm, and pull the sensor straight out of its bore in the hub or knuckle.",
        "If the sensor is seized from corrosion, apply penetrating oil and gently work it side to side while pulling rather than prying, to avoid damaging the tip.",
        "Clean the sensor bore with a wire brush to remove rust or debris that could prevent the new sensor from seating fully.",
        "Apply a light coat of anti-seize to the new sensor's mounting shaft, avoiding the sensor tip itself.",
        "Insert the new sensor fully into its bore until it seats against the mounting boss.",
        "Install and Torque the sensor mounting bolt to 89 in-lbs (10 Nm) — this is a small bolt and easy to overtighten or strip.",
        "Route the new sensor's wiring harness along the same path as the original, securing it in every factory retaining clip to keep it clear of the wheel and moving suspension parts.",
        "Reconnect the sensor's electrical connector until it clicks into place.",
        "Reconnect the negative battery terminal, reinstall the wheel, and Torque the lug nuts to 80-100 ft-lbs (108-135 Nm) in a star pattern after lowering the vehicle.",
        "Clear the stored wheel speed sensor code with an OBD-II scanner and take a test drive up to 20 mph, confirming the ABS and traction control warning lights stay off.",
    ],
    citations=[_GENERIC_CITATION],
    parts=["ABS wheel speed sensor ($35-$90)", "Anti-seize compound ($6)"],
)

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
    ]
}

# OBD-II code prefix ranges mapped to the template that best matches them.
# Checked in order; the first matching range wins.
_CODE_RANGES: list[tuple[str, str, str]] = [
    ("P0300", "P0312", "ignition_misfire"),
    ("P0130", "P0167", "oxygen_sensor"),
    ("P0171", "P0175", "fuel_trim_lean"),
    ("P0420", "P0434", "catalytic_converter"),
    ("P0440", "P0457", "evap_leak"),
    ("P0562", "P0563", "charging_battery"),
    ("P0117", "P0128", "cooling_system"),
    ("C0035", "C0050", "wheel_speed_abs"),
]

_KEYWORD_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"misfire|rough idle|shak(e|ing)|stumbl", re.IGNORECASE),
        "ignition_misfire",
    ),
    (re.compile(r"oxygen sensor|o2 sensor", re.IGNORECASE), "oxygen_sensor"),
    (re.compile(r"lean|vacuum leak|fuel trim", re.IGNORECASE), "fuel_trim_lean"),
    (re.compile(r"catalytic|catalyst", re.IGNORECASE), "catalytic_converter"),
    (re.compile(r"evap|gas cap|purge valve|vent valve", re.IGNORECASE), "evap_leak"),
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
]


def _extract_codes(symptoms: str, obd_codes: list[str] | None) -> list[str]:
    codes = [c.upper() for c in (obd_codes or []) if c]
    codes += [m.upper() for m in _CODE_TOKEN_RE.findall(symptoms or "")]
    return codes


def _match_code_range(code: str) -> str | None:
    try:
        numeric = int(code[1:])
        prefix = code[0]
    except (ValueError, IndexError):
        return None
    for start, end, category in _CODE_RANGES:
        if prefix != start[0]:
            continue
        if int(start[1:]) <= numeric <= int(end[1:]):
            return category
    return None


def select_template(
    symptoms: str, obd_codes: list[str] | None = None
) -> RepairTemplate | None:
    """Match symptom text and/or OBD codes to the best-fit repair template.

    Tries OBD code prefix ranges first (most specific), then falls back to
    keyword matching against the free-text symptoms. Returns ``None`` when
    nothing matches, so the caller can fall back to generic steps.
    """
    for code in _extract_codes(symptoms, obd_codes):
        category = _match_code_range(code)
        if category:
            return _TEMPLATES[category]

    for pattern, category in _KEYWORD_RULES:
        if pattern.search(symptoms or ""):
            return _TEMPLATES[category]

    return None


def get_template(category: str) -> RepairTemplate | None:
    """Look up a template by category name, e.g. to swap in a more specific
    template (brakes_drum) after disambiguating a keyword-matched one
    (brakes) against real retrieved OEM text. See
    backend.services.llm.refine_brake_category."""
    return _TEMPLATES.get(category)
