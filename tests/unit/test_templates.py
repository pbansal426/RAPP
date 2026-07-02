from backend.repair_templates import select_template


def test_obd_code_ignition_misfire() -> None:
    template = select_template("Engine shaking at idle", ["P0301"])
    assert template is not None
    assert template.category == "ignition_misfire"


def test_obd_code_catalytic_converter() -> None:
    template = select_template("Check engine light on", ["P0420"])
    assert template is not None
    assert template.category == "catalytic_converter"


def test_obd_code_wheel_speed_abs() -> None:
    template = select_template("ABS light is on", ["C0035"])
    assert template is not None
    assert template.category == "wheel_speed_abs"


def test_code_embedded_in_symptoms_text() -> None:
    template = select_template("my car threw p0442 last week", [])
    assert template is not None
    assert template.category == "evap_leak"


def test_keyword_fallback_brakes() -> None:
    template = select_template("Brakes squealing when I come to a stop", [])
    assert template is not None
    assert template.category == "brakes"


def test_keyword_fallback_suspension() -> None:
    template = select_template("Loud clunk from the front strut over bumps", [])
    assert template is not None
    assert template.category == "suspension"


def test_keyword_fallback_charging() -> None:
    template = select_template("Car won't start, just clicking, battery is old", [])
    assert template is not None
    assert template.category == "charging_battery"


def test_no_match_returns_none() -> None:
    assert select_template("purple unicorn glitter engine", []) is None


def test_no_symptoms_or_codes_returns_none() -> None:
    assert select_template("", []) is None


def test_obd_codes_none_does_not_crash() -> None:
    assert select_template("random noise", None) is None


def _all_templates() -> list:
    from backend.repair_templates import _TEMPLATES

    return list(_TEMPLATES.values())


def test_every_template_has_minimum_step_count() -> None:
    for template in _all_templates():
        assert len(template.steps) >= 14, f"{template.category} has too few steps"


def test_every_template_has_a_torque_callout() -> None:
    # Matches the frontend highlight regex /(Torque [^.,;]+)/gi in repair/page.tsx,
    # which looks for "Torque " anywhere in the step text, not just at the start.
    for template in _all_templates():
        assert any(
            "Torque " in step for step in template.steps
        ), f"{template.category} has no 'Torque ' callout"


def test_no_emoji_in_any_step() -> None:
    for template in _all_templates():
        for step in template.steps:
            for ch in step:
                assert (
                    ord(ch) < 0x2190 or ord(ch) > 0x1FAFF
                ), f"emoji-like character found in {template.category}: {step!r}"


def test_every_template_has_citations_and_parts() -> None:
    for template in _all_templates():
        assert len(template.citations) >= 1, f"{template.category} has no citations"
        assert len(template.parts) >= 1, f"{template.category} has no parts"


def test_template_count() -> None:
    assert len(_all_templates()) >= 10
