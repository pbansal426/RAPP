from backend.pricing import (
    build_cost_breakdown,
    build_part_options,
    build_recommended_parts,
    parse_part_price,
)
from backend.repair_templates import _TEMPLATES, IGNITION_MISFIRE


def test_parse_part_price_range():
    name, low, high = parse_part_price("Ignition coil pack ($45-$90 each)")
    assert name == "Ignition coil pack"
    assert low == 45.0
    assert high == 90.0


def test_parse_part_price_single_value():
    name, low, high = parse_part_price("Dielectric grease ($5)")
    assert name == "Dielectric grease"
    assert low == 5.0
    assert high == 5.0


def test_parse_part_price_no_price_has_sane_default():
    name, low, high = parse_part_price("Mystery part")
    assert name == "Mystery part"
    assert low > 0
    assert high >= low


def test_build_part_options_has_all_three_tiers():
    options = build_part_options("2018 Honda Civic", "Oxygen sensor", 40.0, 120.0)
    tiers = {opt["tier"] for opt in options}
    assert tiers == {"OEM", "Aftermarket / Budget", "Upgrade"}
    for opt in options:
        assert opt["estimated_price"] > 0
        assert opt["purchase_url"].startswith("https://")
        assert opt["rationale"]


def test_build_part_options_budget_is_cheapest():
    options = build_part_options("2018 Honda Civic", "Oxygen sensor", 40.0, 120.0)
    by_tier = {opt["tier"]: opt["estimated_price"] for opt in options}
    assert by_tier["Aftermarket / Budget"] < by_tier["OEM"] < by_tier["Upgrade"]


def test_build_recommended_parts_empty_without_template():
    assert build_recommended_parts(None, "2018 Honda Civic") == []


def test_build_recommended_parts_matches_template_part_count():
    recommended = build_recommended_parts(IGNITION_MISFIRE, "2018 Honda Civic")
    assert len(recommended) == len(IGNITION_MISFIRE.parts)
    for part in recommended:
        assert part["part_name"]
        assert len(part["options"]) == 3


def test_build_cost_breakdown_without_template_has_no_parts_cost():
    breakdown = build_cost_breakdown(None)
    assert breakdown["parts_total"] == 0.0
    assert breakdown["diy_total"] == 4.00
    assert breakdown["estimated_labor_hours"] > 0


def test_build_cost_breakdown_diy_total_is_fee_plus_parts():
    breakdown = build_cost_breakdown(IGNITION_MISFIRE)
    assert breakdown["diy_total"] == round(4.00 + breakdown["parts_total"], 2)


def test_build_cost_breakdown_dealership_more_expensive_than_independent():
    breakdown = build_cost_breakdown(IGNITION_MISFIRE)
    assert (
        breakdown["dealership_cost_range"][0] > breakdown["independent_shop_range"][0]
    )
    assert (
        breakdown["dealership_cost_range"][1] > breakdown["independent_shop_range"][1]
    )


def test_build_cost_breakdown_independent_more_expensive_than_diy():
    breakdown = build_cost_breakdown(IGNITION_MISFIRE)
    assert breakdown["independent_shop_range"][0] > breakdown["diy_total"]


def test_every_template_produces_a_valid_cost_breakdown():
    for template in _TEMPLATES.values():
        breakdown = build_cost_breakdown(template)
        assert breakdown["parts_total"] >= 0
        assert breakdown["estimated_labor_hours"] > 0
        assert (
            breakdown["dealership_cost_range"][0]
            <= breakdown["dealership_cost_range"][1]
        )
        assert (
            breakdown["independent_shop_range"][0]
            <= breakdown["independent_shop_range"][1]
        )
