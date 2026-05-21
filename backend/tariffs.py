"""backend/tariffs.py

LgWSC (Lukanga Water Supply and Sanitation Company) Tariff Structure.

Tariff rates are based on the LgWSC schedule for Central Province, Zambia.
All amounts are in Zambian Kwacha (ZMW).

Structure:
  1. Domestic Metered — 4 volumetric tiers (lifeline → heavy use)
  2. Domestic Unmetered — flat rate by housing area density
  3. Commercial / Institutional — elevated block tiers
  4. Water Kiosks / Communal Standpipes — subsidised per-container rate

Fixed monthly charges apply to all metered accounts:
  - Fixed Meter Charge: K15.00/month
  - Sanitation Surcharge: 2.5% of the water charge subtotal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TariffTier:
    """A single volumetric pricing tier."""
    label: str
    from_m3: float          # inclusive lower bound (m³/month)
    to_m3: Optional[float]  # exclusive upper bound; None = unlimited
    rate_per_m3: float      # ZMW per m³ within this tier


@dataclass
class TariffSchedule:
    """A complete tariff schedule for a customer category."""
    name: str
    description: str
    tiers: List[TariffTier]
    fixed_meter_charge: float = 15.00   # ZMW/month
    sanitation_surcharge_pct: float = 2.5  # % of water subtotal


@dataclass
class BillBreakdown:
    """Itemised bill calculation result."""
    consumption_m3: float
    tier_charges: List[dict]            # [{tier, m3_in_tier, rate, charge}]
    water_subtotal: float
    fixed_meter_charge: float
    sanitation_surcharge: float
    total_due: float
    schedule_name: str


# ---------------------------------------------------------------------------
# Tariff schedules
# ---------------------------------------------------------------------------

# 1. Domestic Metered
DOMESTIC_METERED = TariffSchedule(
    name="Domestic Metered",
    description="Metered household customers — four volumetric tiers",
    tiers=[
        TariffTier("Tier 1 — Lifeline Block (0–6 m³)",    0,  6,  3.50),
        TariffTier("Tier 2 — Standard Use (6–15 m³)",     6,  15, 8.20),
        TariffTier("Tier 3 — Higher Use (15–30 m³)",      15, 30, 14.50),
        TariffTier("Tier 4 — Heavy Use (>30 m³)",         30, None, 22.00),
    ],
    fixed_meter_charge=15.00,
    sanitation_surcharge_pct=2.5,
)

# 2. Domestic Unmetered — flat rates by housing density
DOMESTIC_UNMETERED_LOW_COST    = 85.00   # ZMW/month — low-cost housing areas
DOMESTIC_UNMETERED_MEDIUM_COST = 145.00  # ZMW/month — medium-cost housing areas
DOMESTIC_UNMETERED_HIGH_COST   = 220.00  # ZMW/month — high-cost housing areas

# 3. Commercial / Institutional Metered
COMMERCIAL_METERED = TariffSchedule(
    name="Commercial / Institutional Metered",
    description="Businesses, industries, schools, hospitals — elevated block rates",
    tiers=[
        TariffTier("Block 1 (0–10 m³)",    0,  10, 12.00),
        TariffTier("Block 2 (10–30 m³)",   10, 30, 18.50),
        TariffTier("Block 3 (30–60 m³)",   30, 60, 26.00),
        TariffTier("Block 4 (>60 m³)",     60, None, 35.00),
    ],
    fixed_meter_charge=25.00,
    sanitation_surcharge_pct=2.5,
)

# 4. Water Kiosks / Communal Standpipes
KIOSK_RATE_PER_20L_CONTAINER = 0.50  # ZMW per 20-litre container


# ---------------------------------------------------------------------------
# Calculation engine
# ---------------------------------------------------------------------------

def calculate_bill(consumption_m3: float, schedule: TariffSchedule) -> BillBreakdown:
    """Compute an itemised bill for a given consumption and tariff schedule.

    Args:
        consumption_m3: Total water consumed in cubic metres for the billing period.
        schedule: The applicable TariffSchedule.

    Returns:
        BillBreakdown with per-tier charges, fixed charges, sanitation surcharge,
        and total amount due.
    """
    remaining = max(0.0, consumption_m3)
    tier_charges = []
    water_subtotal = 0.0

    for tier in schedule.tiers:
        if remaining <= 0:
            break

        tier_capacity = (
            (tier.to_m3 - tier.from_m3) if tier.to_m3 is not None else remaining
        )
        m3_in_tier = min(remaining, tier_capacity)
        charge = m3_in_tier * tier.rate_per_m3

        tier_charges.append({
            "tier": tier.label,
            "m3_in_tier": round(m3_in_tier, 2),
            "rate_per_m3": tier.rate_per_m3,
            "charge": round(charge, 2),
        })

        water_subtotal += charge
        remaining -= m3_in_tier

    water_subtotal = round(water_subtotal, 2)
    sanitation = round(water_subtotal * schedule.sanitation_surcharge_pct / 100, 2)
    total = round(water_subtotal + schedule.fixed_meter_charge + sanitation, 2)

    return BillBreakdown(
        consumption_m3=consumption_m3,
        tier_charges=tier_charges,
        water_subtotal=water_subtotal,
        fixed_meter_charge=schedule.fixed_meter_charge,
        sanitation_surcharge=sanitation,
        total_due=total,
        schedule_name=schedule.name,
    )


def get_schedule_for_category(customer_category: str) -> TariffSchedule:
    """Return the appropriate tariff schedule for a customer category string."""
    cat = (customer_category or "").strip().lower()
    if cat in {"commercial", "industrial", "institutional", "government",
               "school", "hospital", "sme", "mining", "agriculture", "transport"}:
        return COMMERCIAL_METERED
    return DOMESTIC_METERED


def format_bill_breakdown(breakdown: BillBreakdown, billing_period: str) -> str:
    """Format a BillBreakdown into a human-readable billing statement."""
    lines = [
        f"Billing Period: {billing_period}",
        f"Consumption: {breakdown.consumption_m3:.1f} m³",
        "",
        "Water Charges:",
    ]

    for item in breakdown.tier_charges:
        lines.append(
            f"  {item['tier']}: "
            f"{item['m3_in_tier']:.1f} m³ × K{item['rate_per_m3']:.2f} = K{item['charge']:.2f}"
        )

    lines += [
        f"  Water Subtotal:          K{breakdown.water_subtotal:.2f}",
        "",
        "Fixed Charges:",
        f"  Meter Service Charge:    K{breakdown.fixed_meter_charge:.2f}",
        f"  Sanitation Surcharge:    K{breakdown.sanitation_surcharge:.2f}",
        "  (2.5% of water charges)",
        "",
        f"Total Amount Due:          K{breakdown.total_due:.2f}",
    ]

    return "\n".join(lines)
