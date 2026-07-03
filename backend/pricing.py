"""Structured parts-pricing and cost-breakdown generation.

Turns the flat ``parts`` price-range strings on a :class:`RepairTemplate`
(e.g. ``"Ignition coil pack ($45-$90 each)"``) into comparison-shopping data
for the diagnosis response: three purchase tiers per part (OEM, budget
aftermarket, performance/heavy-duty upgrade) plus a dealership vs.
independent-shop vs. DIY cost comparison. Pure functions returning plain
dicts so ``backend/main.py`` can validate them through its Pydantic response
models without this module needing to depend on FastAPI/Pydantic.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus

from backend.repair_templates import RepairTemplate

_PRICE_RANGE_RE = re.compile(r"\$(\d+(?:\.\d+)?)(?:\s*-\s*\$(\d+(?:\.\d+)?))?")

# Rough shop-rate assumptions per the product spec.
_DEALERSHIP_LABOR_RATE = (180.0, 220.0)
_INDEPENDENT_LABOR_RATE = (110.0, 140.0)
_DEALERSHIP_PARTS_MARKUP = (1.3, 1.5)
_INDEPENDENT_PARTS_MARKUP = (1.1, 1.2)
_RAPP_GUIDE_FEE = 4.00

_DEFAULT_LABOR_HOURS = 1.5
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
}


def parse_part_price(part_str: str) -> tuple[str, float, float]:
    """ "Ignition coil pack ($45-$90 each)" -> ("Ignition coil pack", 45.0, 90.0)."""
    name = re.sub(r"\(.*?\)", "", part_str).strip().rstrip(",")
    match = _PRICE_RANGE_RE.search(part_str)
    if not match:
        return name or part_str.strip(), 20.0, 40.0
    low = float(match.group(1))
    high = float(match.group(2)) if match.group(2) else low
    if high < low:
        low, high = high, low
    return name, low, high


def _search_url(retailer: str, query: str) -> str:
    q = quote_plus(query.strip())
    if retailer == "amazon":
        return f"https://www.amazon.com/s?k={q}&i=automotive"
    if retailer == "autozone":
        return f"https://www.autozone.com/searchresult?searchText={q}"
    if retailer == "rockauto":
        return f"https://www.google.com/search?q={q}+site%3Arockauto.com"
    return f"https://www.google.com/search?q={q}"


def build_part_options(
    vehicle_desc: str, part_name: str, low: float, high: float
) -> list[dict[str, Any]]:
    query_base = f"{vehicle_desc} {part_name}".strip()
    budget_price = round(low, 2)
    oem_price = round(high * 1.35, 2)
    upgrade_price = round(high * 1.75, 2)

    return [
        {
            "tier": "Aftermarket / Budget",
            "brand": "Duralast / equivalent aftermarket",
            "part_number": None,
            "title": f"{part_name} (Aftermarket)",
            "estimated_price": budget_price,
            "purchase_url": _search_url("autozone", query_base),
            "rationale": "Reliable daily-driver replacement at the lowest verified price point.",
        },
        {
            "tier": "OEM",
            "brand": "OEM / Genuine Dealer Part",
            "part_number": None,
            "title": f"{part_name} (OEM)",
            "estimated_price": oem_price,
            "purchase_url": _search_url("amazon", f"OEM {query_base}"),
            "rationale": "Exact factory fit and spec — the safest choice for warranty and long-term reliability.",
        },
        {
            "tier": "Upgrade",
            "brand": "Performance / Heavy-Duty",
            "part_number": None,
            "title": f"{part_name} (Performance / Heavy-Duty)",
            "estimated_price": upgrade_price,
            "purchase_url": _search_url("rockauto", f"performance {query_base}"),
            "rationale": "Upgraded materials or performance rating for heavier use or extended service life.",
        },
    ]


def build_recommended_parts(
    template: RepairTemplate | None, vehicle_desc: str
) -> list[dict[str, Any]]:
    if not template:
        return []

    recommended = []
    for part_str in template.parts:
        name, low, high = parse_part_price(part_str)
        recommended.append(
            {
                "part_name": name,
                "options": build_part_options(vehicle_desc, name, low, high),
            }
        )
    return recommended


def build_cost_breakdown(template: RepairTemplate | None) -> dict[str, Any]:
    if template:
        parts_total = round(sum(parse_part_price(p)[1] for p in template.parts), 2)
        labor_hours = _LABOR_HOURS_BY_CATEGORY.get(
            template.category, _DEFAULT_LABOR_HOURS
        )
    else:
        parts_total = 0.0
        labor_hours = 1.0  # baseline diagnostic-only labor estimate

    dealer_rate_low, dealer_rate_high = _DEALERSHIP_LABOR_RATE
    indep_rate_low, indep_rate_high = _INDEPENDENT_LABOR_RATE
    dealer_markup_low, dealer_markup_high = _DEALERSHIP_PARTS_MARKUP
    indep_markup_low, indep_markup_high = _INDEPENDENT_PARTS_MARKUP

    dealership_low = round(
        parts_total * dealer_markup_low + labor_hours * dealer_rate_low, 2
    )
    dealership_high = round(
        parts_total * dealer_markup_high + labor_hours * dealer_rate_high, 2
    )
    independent_low = round(
        parts_total * indep_markup_low + labor_hours * indep_rate_low, 2
    )
    independent_high = round(
        parts_total * indep_markup_high + labor_hours * indep_rate_high, 2
    )
    diy_total = round(_RAPP_GUIDE_FEE + parts_total, 2)

    return {
        "dealership_cost_range": [dealership_low, dealership_high],
        "independent_shop_range": [independent_low, independent_high],
        "parts_total": parts_total,
        "diy_total": diy_total,
        "estimated_labor_hours": labor_hours,
    }
