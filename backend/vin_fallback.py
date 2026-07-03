"""Offline WMI-based VIN decoding fallback.

Used only when the live NHTSA vPIC API is unreachable or erroring (5xx/403/
timeout/connect failure) after `_fetch_nhtsa_vin_fields`'s retries are
exhausted. Decodes what's honestly derivable from the VIN string itself
without a manufacturer-licensed VDS table: make (from the 3-character World
Manufacturer Identifier) and model year (from the standardized position-10
code). Model, trim, engine, and drive type are deliberately left blank
rather than guessed -- full VDS decoding is manufacturer-proprietary, which
is why NHTSA's vPIC API exists as the primary path.
"""

from __future__ import annotations

from typing import Any

# Non-exhaustive: a defensible subset of well-documented WMI prefixes for the
# major North American makes an NHTSA outage most commonly needs to cover.
_WMI_MAKES: dict[str, str] = {
    "4T1": "TOYOTA",
    "4T3": "TOYOTA",
    "5TD": "TOYOTA",
    "JTD": "TOYOTA",
    "1NX": "TOYOTA",
    "1HG": "HONDA",
    "2HG": "HONDA",
    "JHM": "HONDA",
    "5FN": "HONDA",
    "1FA": "FORD",
    "1FT": "FORD",
    "1FM": "FORD",
    "3FA": "FORD",
    "1G1": "CHEVROLET",
    "1GC": "CHEVROLET",
    "2G1": "CHEVROLET",
}

# Position-10 model-year code, standard order (I, O, Q, U, Z are never used
# in a VIN, so they're never used as year codes either).
_YEAR_CODE_ORDER = "ABCDEFGHJKLMNPRSTVWXY123456789"


def _decode_model_year(vin: str) -> int | None:
    code = vin[9]
    if code not in _YEAR_CODE_ORDER:
        return None
    offset = _YEAR_CODE_ORDER.index(code)
    # The code cycles every 30 years; position 7 being alphabetic vs numeric
    # is the standard heuristic for resolving which cycle (1980s+ vs 2010s+).
    cycle_start = 2010 if vin[6].isalpha() else 1980
    return cycle_start + offset


def wmi_fallback_decode(vin: str) -> dict[str, Any] | None:
    """Best-effort offline decode from the VIN string alone.

    Returns None (never a guess) when the WMI isn't in the known table, so
    callers can fall through to a clear error instead of showing wrong
    vehicle data.
    """
    make = _WMI_MAKES.get(vin[:3])
    if not make:
        return None

    return {
        "year": _decode_model_year(vin),
        "make": make,
        "model": "",
        "trim": None,
        "engine": "",
        "drive_type": "Unknown",
        "body_class": None,
        "vehicle_type": None,
        "fuel_type": None,
        "powertrain": None,
        "decode_source": "offline_fallback",
    }
