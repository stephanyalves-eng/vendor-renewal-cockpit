"""Synthetic data for a fictional Brazilian fintech: vendors, contracts, spend, budget, headcount,
public benchmarks and savings events.

Everything here is SYNTHETIC except the public list prices in data/reference/public_list_prices.csv.
Vendor names are invented. The generator deliberately plants the patterns listed in SPEC.md
(overlapping tools, under-used licences, escalators above inflation, near-term renewals, an
unbudgeted vendor, cloud growth and marketing seasonality) so the analytics have something to find.
Which contract carries which pattern is returned in `manifest`, so tests can prove each rule finds it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import ROOT

CATEGORIES = ["SaaS", "Cloud", "Marketing", "Professional services", "Data and security"]
BILLING_MODELS = ["per_seat", "usage", "fixed"]
STATUSES = ["onboarding", "active", "renewal_window", "renegotiating", "terminated"]
SAVINGS_TYPES = ["saving", "cost_avoidance"]
REFERENCE_PRICES = ROOT / "data" / "reference" / "public_list_prices.csv"

# Departments and their headcount at the start of the history. "IT" owns company-wide tools,
# so per-seat tools owned by IT are sized against total headcount.
DEPARTMENTS = {
    "Engineering": 180, "Product": 40, "Sales": 90, "Marketing": 35, "Customer Support": 110,
    "Finance": 30, "People": 20, "Legal": 12, "Operations": 60, "IT": 25,
}
COMPANY_WIDE_OWNER = "IT"


@dataclass(frozen=True)
class V:
    """One vendor and its single active contract.

    role: which planted pattern this vendor carries ("base" = none).
    util: target seat utilization at the anchor date (per_seat only).
    adopt: share of the department (or company) that actively uses the tool (per_seat only).
    price: current unit price in BRL per month (per seat, per usage unit, or monthly fee).
    units: monthly usage volume at the start of the history (usage only).
    end: fixed end date for planted contracts; others get a random end date outside the window.
    last_change: price change at the last renewal; defaults to the escalator. Negative = a saving.
    """
    name: str
    category: str
    capability: str
    billing: str
    dept: str
    criticality: str
    risk: str
    role: str = "base"
    util: float = 0.0
    adopt: float = 0.0
    price: float = 0.0
    units: float = 0.0
    esc: float = 4.0
    end: str | None = None
    notice: int | None = None
    auto: bool | None = None
    last_change: float | None = None
    start: str | None = None


# fmt: off
CATALOG: list[V] = [
    # --- SaaS ---------------------------------------------------------------------------------
    V("Confera", "SaaS", "video_conferencing", "per_seat", "IT", "high", "medium", "overlap_keeper", util=0.88, adopt=0.95, price=70.00),
    V("MeetLoop", "SaaS", "video_conferencing", "per_seat", "Sales", "medium", "low", "consolidate", util=0.66, adopt=0.85, price=72.00, end="2027-03-15", notice=30, auto=True),
    V("Vidmo", "SaaS", "video_conferencing", "per_seat", "Customer Support", "medium", "low", "consolidate", util=0.68, adopt=0.70, price=78.00, esc=3.0, end="2027-02-15", notice=30, auto=False),
    V("Signet", "SaaS", "e_signature", "per_seat", "Legal", "medium", "medium", "overlap_keeper", util=0.90, adopt=0.90, price=98.00),
    V("InkPact", "SaaS", "e_signature", "per_seat", "Sales", "medium", "low", "consolidate", util=0.70, adopt=0.40, price=110.00, esc=4.5, end="2027-03-10", notice=30, auto=False),
    V("Taskhive", "SaaS", "work_management", "per_seat", "Product", "medium", "low", "overlap_keeper", util=0.86, adopt=0.90, price=45.00, esc=3.0),
    V("Planora", "SaaS", "work_management", "per_seat", "Operations", "medium", "low", "consolidate", util=0.67, adopt=0.60, price=52.00, end="2027-03-25", notice=30, auto=True),
    V("Relaychat", "SaaS", "team_chat", "per_seat", "IT", "high", "medium", "renew", util=0.90, adopt=0.97, price=38.00, esc=3.5, end="2027-02-26", notice=30, auto=True),
    V("Codeforge", "SaaS", "code_hosting", "per_seat", "Engineering", "high", "high", util=0.89, adopt=0.95, price=21.00, esc=3.0, last_change=-6.0),
    V("Pixelcraft", "SaaS", "design_tools", "per_seat", "Product", "medium", "low", "rightsize", util=0.45, adopt=0.50, price=85.00, end="2027-03-05", notice=60, auto=False),
    V("Ledgerly", "SaaS", "expense_management", "per_seat", "IT", "medium", "medium", util=0.84, adopt=0.60, price=25.00),
    V("PeopleFlow", "SaaS", "hris", "per_seat", "IT", "high", "high", util=0.93, adopt=1.00, price=32.00, esc=4.5),
    V("Dealstream", "SaaS", "crm", "per_seat", "Sales", "high", "high", "rightsize", util=0.52, adopt=0.90, price=190.00, end="2027-02-10", notice=60, auto=True),
    V("Helpdeskly", "SaaS", "support_desk", "per_seat", "Customer Support", "high", "medium", "escalator", util=0.85, adopt=0.90, price=120.00, esc=12.0, end="2027-01-15", notice=30, auto=True),
    V("Wikinest", "SaaS", "knowledge_base", "per_seat", "IT", "low", "low", "terminate", util=0.12, adopt=0.10, price=18.00, end="2027-01-31", notice=30, auto=False),
    V("Workwell Suite", "SaaS", "productivity_suite", "per_seat", "IT", "high", "medium", "above_benchmark", util=0.91, adopt=1.00, price=102.25, end="2027-03-26", notice=60, auto=False),
    V("Formwise", "SaaS", "surveys", "per_seat", "Marketing", "low", "low", "rightsize", util=0.38, adopt=0.70, price=60.00, esc=3.0, end="2027-03-20", notice=30, auto=False),
    V("Learnly", "SaaS", "learning_platform", "per_seat", "IT", "low", "low", "rightsize", util=0.33, adopt=0.30, price=22.00, end="2027-03-28", notice=30, auto=True),
    V("Contractly", "SaaS", "contract_management", "per_seat", "Operations", "medium", "medium", "escalator", util=0.83, adopt=0.90, price=140.00, esc=9.0, end="2027-03-18", notice=60, auto=False),
    V("Analytiq", "SaaS", "bi_dashboards", "per_seat", "Finance", "medium", "low", "rightsize", util=0.42, adopt=1.00, price=95.00, esc=4.5, end="2027-03-12", notice=30, auto=False),
    V("Promptly", "SaaS", "ai_assistant", "per_seat", "Engineering", "medium", "medium", "unbudgeted", util=0.80, adopt=0.60, price=110.00, start="2026-05-01", end="2027-04-30", notice=30, auto=True),
    V("Recruitly", "SaaS", "recruiting_ats", "per_seat", "People", "medium", "low", "terminated", util=0.80, adopt=0.90, price=75.00, end="2026-06-30", notice=30, auto=False),
    # --- Cloud (usage grows with the business) -------------------------------------------------
    V("Nimbus Compute", "Cloud", "cloud_compute", "usage", "Engineering", "high", "high", "cloud", price=18.50, units=9000, last_change=-5.0),
    V("Stratus Storage", "Cloud", "object_storage", "usage", "Engineering", "high", "medium", "cloud", price=0.12, units=120000),
    V("Pulsewire", "Cloud", "cdn", "usage", "Engineering", "medium", "medium", "cloud", price=0.35, units=40000),
    V("Querybase", "Cloud", "managed_database", "usage", "Engineering", "high", "high", "cloud", price=42.00, units=2500),
    # --- Marketing (seasonal peaks) ------------------------------------------------------------
    V("Adreach", "Marketing", "paid_social", "usage", "Marketing", "medium", "low", "seasonal", price=32.00, units=1800),
    V("Searchlift", "Marketing", "paid_search", "usage", "Marketing", "medium", "low", "seasonal", price=3.80, units=25000),
    V("Mailbloom", "Marketing", "email_marketing", "usage", "Marketing", "medium", "low", "seasonal", price=45.00, units=600),
    V("Brandwave Studio", "Marketing", "creative_agency", "fixed", "Marketing", "low", "low", price=30000.00),
    V("Eventura", "Marketing", "events", "usage", "Marketing", "low", "low", "seasonal", price=120.00, units=900),
    # --- Professional services (fixed fees) ----------------------------------------------------
    V("Ardent Legal Partners", "Professional services", "legal_counsel", "fixed", "Legal", "high", "medium", price=40000.00),
    V("Calder & Reis Auditores", "Professional services", "external_audit", "fixed", "Finance", "high", "medium", price=35000.00),
    V("Talentbridge Consulting", "Professional services", "recruiting_agency", "fixed", "People", "low", "low", price=15000.00),
    V("Kestrel Advisory", "Professional services", "strategy_consulting", "fixed", "Operations", "medium", "low", "renew", price=20000.00, end="2027-01-20", notice=14, auto=False),
    V("Folha Certa Payroll", "Professional services", "payroll_services", "fixed", "People", "high", "high", price=12500.00),
    # --- Data and security ---------------------------------------------------------------------
    V("Sentinela Security", "Data and security", "endpoint_security", "per_seat", "IT", "high", "high", util=0.94, adopt=1.00, price=28.00, esc=4.5, last_change=-8.0),
    V("Riskwatch KYC", "Data and security", "kyc_verification", "usage", "Operations", "high", "high", price=2.90, units=30000),
    V("Logline", "Data and security", "log_monitoring", "usage", "Engineering", "high", "medium", price=55.00, units=800),
    V("Credscore Data", "Data and security", "credit_bureau_data", "usage", "Operations", "high", "high", price=1.60, units=50000),
]
# fmt: on

# Cost-avoidance events (no price history, so measured against the first quote).
COST_AVOIDANCE = [
    ("Promptly", "2026-05-01", 135.00, "First quote 135.00 per seat; negotiated to 110.00 before signing."),
    ("Brandwave Studio", "2026-08-15", 38000.00, "New campaign retainer; first quote 38,000 per month."),
]


# --- date helpers ------------------------------------------------------------------------------

def month_idx(ts) -> int:
    return ts.year * 12 + ts.month - 1


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m])
    return date(y, m + 1, day)


def price_at(unit_price: float, esc_pct: float, last_change_pct: float, end_date: date, month) -> float:
    """Unit price in force in `month`, given annual renewals that end in the month of `end_date`.

    The current term covers the 12 months up to the end month. Each earlier term is one renewal
    step cheaper; the most recent step is `last_change_pct`, older ones `esc_pct`. After the end
    month the contract is assumed to renew with the escalator (status quo).
    """
    e0, m = month_idx(end_date), month_idx(month)
    esc = 1 + esc_pct / 100
    if m > e0:
        return unit_price * esc ** ((m - e0 - 1) // 12 + 1)
    k = (e0 - m) // 12
    if k == 0:
        return unit_price
    return unit_price / (1 + last_change_pct / 100) / esc ** (k - 1)


# --- generator ---------------------------------------------------------------------------------

def generate(cfg: dict) -> dict:
    rng = np.random.default_rng(cfg["seed"])
    sc, gen, th = cfg["scenario"], cfg["generator"], cfg["thresholds"]
    ipca = cfg["economics"]["ipca_annual_pct"]
    anchor = sc["anchor_date"]
    months = list(pd.date_range(sc["history_start"], sc["history_end"], freq="MS"))
    anchor_month = months[-1]
    assert len(CATALOG) == gen["n_vendors"], "catalog size must match generator.n_vendors"

    # headcount ---------------------------------------------------------------------------------
    hc_rows = []
    for dept, base in DEPARTMENTS.items():
        level = float(base)
        for m in months:
            hc_rows.append((m, dept, int(round(level))))
            level *= 1 + gen["headcount_monthly_growth"] + rng.normal(0, 0.004)
    headcount = pd.DataFrame(hc_rows, columns=["month", "department", "headcount"])
    hc = headcount.pivot(index="month", columns="department", values="headcount")
    hc_total = hc.sum(axis=1)

    def seat_base(dept: str) -> pd.Series:
        return hc_total if dept == COMPANY_WIDE_OWNER else hc[dept]

    # vendors and contract terms ----------------------------------------------------------------
    vendors, contracts, spend_rows, budget_rows = [], [], [], []
    manifest: dict[str, list] = {k: [] for k in (
        "consolidate", "overlap_keepers", "rightsize", "terminate", "escalator", "above_benchmark",
        "renew", "urgent", "unbudgeted_vendors", "cloud_vendors", "marketing_vendors", "terminated")}

    window_end = anchor + timedelta(days=th["renewal_window_days"])
    for i, v in enumerate(CATALOG, start=1):
        vid, cid = f"V{i:03d}", f"C{i:03d}"
        vendors.append(dict(vendor_id=vid, name=v.name, category=v.category, capability=v.capability,
                            owner_department=v.dept, criticality=v.criticality, risk_tier=v.risk))

        # Term dates: planted contracts have fixed dates; the rest end after the renewal window.
        if v.end:
            end = date.fromisoformat(v.end)
        else:
            end = window_end + timedelta(days=int(rng.integers(5, 240)))
        notice = v.notice if v.notice is not None else int(rng.choice([30, 60, 90]))
        auto = v.auto if v.auto is not None else bool(rng.random() < 0.6)
        if v.start:
            start = date.fromisoformat(v.start)
        else:
            start = add_months(end, -12 * int(rng.integers(3, 6))) + timedelta(days=1)
        last_change = v.esc if v.last_change is None else v.last_change

        # Volumes per month.
        idx = [m for m in months if m >= pd.Timestamp(start.replace(day=1))
               and (v.role != "terminated" or m <= pd.Timestamp(end))]
        seats = None
        if v.billing == "per_seat":
            base = seat_base(v.dept)
            seats = int(round(v.adopt * base[anchor_month] / v.util))
            if v.role == "terminated":  # sized when it was still in use
                seats = int(round(v.adopt * base[idx[-1]] / v.util))
            active = {}
            for j, m in enumerate(idx):
                ramp = min(1.0, 0.4 + 0.2 * j) if v.role == "unbudgeted" else 1.0
                active[m] = int(round(v.adopt * base[m] * ramp * rng.normal(1, 0.01)))
        elif v.billing == "usage":
            units = {}
            for t, m in enumerate(months):
                if v.category == "Cloud":
                    level = v.units * (1 + gen["cloud_monthly_growth"]) ** t
                elif v.category == "Marketing":
                    peak = m.month in gen["marketing_peak_months"]
                    level = v.units * (gen["marketing_peak_multiplier"] if peak else 1.0)
                else:
                    level = v.units * (1 + gen["headcount_monthly_growth"]) ** t
                units[m] = max(0.0, round(level * rng.normal(1, gen["noise_sd"])))

        for m in idx:
            p = price_at(v.price, v.esc, last_change, end, m)
            if v.billing == "per_seat":
                billed = max(seats, active[m])  # contracted seats, plus true-up if usage exceeds
                row = dict(seats_active=active[m], units_used=np.nan, billed_qty=billed)
            elif v.billing == "usage":
                billed = units[m]
                row = dict(seats_active=np.nan, units_used=billed, billed_qty=billed)
            else:
                billed = 1
                row = dict(seats_active=np.nan, units_used=np.nan, billed_qty=1)
            spend_rows.append(dict(month=m, vendor_id=vid, contract_id=cid,
                                   actual_amount=round(billed * p, 2), unit_price_paid=round(p, 4), **row))

        if v.billing == "per_seat":
            annual = round(seats * v.price * 12, 2)
            fee_share = 0.10 if v.criticality == "low" else 0.25
            fee = round(annual * fee_share, 2)
        elif v.billing == "usage":
            recent = [units[m] for m in months[-3:]]
            annual = round(np.mean(recent) * v.price * 12, -3)
            fee = 0.0
        else:
            annual = round(v.price * 12, 2)
            fee = round(v.price * 2, 2)

        if v.role == "terminated":
            status = "terminated"
        elif 0 < (end - anchor).days <= th["renewal_window_days"]:
            status = "renewal_window"
        else:
            status = "active"

        contracts.append(dict(
            contract_id=cid, vendor_id=vid, start_date=start, end_date=end, auto_renew=auto,
            notice_days=notice, billing_model=v.billing, unit_price=v.price, seats_contracted=seats,
            annual_value=annual, price_escalator_pct=v.esc, termination_fee=fee, status=status))

        # Budget: set before each fiscal year at the price then in force; renewals inside the year
        # are budgeted at IPCA. The unbudgeted vendor has no budget line at all.
        if v.role != "unbudgeted":
            budget_months = pd.date_range(sc["history_start"], date(sc["fiscal_year"], 12, 1), freq="MS")
            change_month = end.month % 12 + 1
            for t, m in enumerate(budget_months):
                base_price = price_at(v.price, v.esc, last_change, end, pd.Timestamp(m.year - 1, 12, 1))
                bp = base_price * (1 + ipca / 100) if m.month >= change_month else base_price
                if v.billing == "per_seat":
                    qty = seats
                elif v.billing == "usage":
                    if v.category == "Cloud":
                        qty = v.units * (1 + gen["budget_cloud_monthly_growth"]) ** t
                    elif v.category == "Marketing":
                        peak = m.month in gen["marketing_peak_months"]
                        qty = v.units * (gen["marketing_peak_multiplier"] if peak else 1.0)
                    else:
                        qty = v.units * (1 + gen["headcount_monthly_growth"]) ** t
                    qty = round(qty)
                else:
                    qty = 1
                bp = round(bp, 4)
                budget_rows.append(dict(month=m, vendor_id=vid, budget_qty=qty, budget_unit_price=bp,
                                        budget_amount=round(qty * bp, 2)))

        # manifest
        role_key = {"consolidate": "consolidate", "overlap_keeper": "overlap_keepers",
                    "rightsize": "rightsize", "terminate": "terminate", "escalator": "escalator",
                    "above_benchmark": "above_benchmark", "renew": "renew",
                    "terminated": "terminated"}.get(v.role)
        if role_key:
            manifest[role_key].append(cid)
        if v.role == "unbudgeted":
            manifest["unbudgeted_vendors"].append(vid)
        if v.role == "cloud":
            manifest["cloud_vendors"].append(vid)
        if v.role == "seasonal":
            manifest["marketing_vendors"].append(vid)
        deadline = end - timedelta(days=notice)
        if status == "renewal_window" and auto and (deadline - anchor).days <= th["urgent_deadline_days"]:
            manifest["urgent"].append(cid)

    vendors_df = pd.DataFrame(vendors)
    contracts_df = pd.DataFrame(contracts)
    contracts_df["seats_contracted"] = contracts_df["seats_contracted"].astype("Int64")
    spend_df = pd.DataFrame(spend_rows)
    budget_df = pd.DataFrame(budget_rows)

    return dict(
        vendors=vendors_df,
        contracts=contracts_df,
        monthly_spend=spend_df,
        budget=budget_df,
        headcount=headcount,
        benchmarks=_benchmarks(vendors_df, contracts_df, cfg),
        savings=_savings(contracts_df, vendors_df, spend_df, months),
        manifest=manifest,
    )


def _benchmarks(vendors: pd.DataFrame, contracts: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Map each verified public list price to the fictional per-seat vendors with that capability."""
    ref = pd.read_csv(REFERENCE_PRICES, comment="#")
    fx = {"BRL": 1.0, "USD": cfg["economics"]["fx_usd_brl"]}
    per_seat = vendors.merge(contracts[["vendor_id", "billing_model"]], on="vendor_id")
    per_seat = per_seat[per_seat["billing_model"] == "per_seat"]
    out = per_seat.merge(ref, on="capability")
    out["list_price_per_seat"] = (out["list_price"] * out["list_currency"].map(fx)).round(2)
    return out[["vendor_id", "reference_product", "list_price", "list_currency", "list_price_per_seat",
                "billing_basis", "source_url", "as_of"]].sort_values("vendor_id").reset_index(drop=True)


def _savings(contracts: pd.DataFrame, vendors: pd.DataFrame, spend: pd.DataFrame, months) -> pd.DataFrame:
    """Savings come from the planted price cuts at renewal; cost avoidance from first quotes."""
    names = vendors.set_index("name")["vendor_id"]
    rows = []
    for v in CATALOG:
        if v.last_change is None or v.last_change >= 0:
            continue
        c = contracts[contracts["vendor_id"] == names[v.name]].iloc[0]
        renewal = add_months(c["end_date"], -12) + timedelta(days=1)
        baseline = round(v.price / (1 + v.last_change / 100), 4)
        s = spend[spend["contract_id"] == c["contract_id"]]
        qty = c["seats_contracted"] if v.billing == "per_seat" else s["billed_qty"].tail(3).mean()
        rows.append(dict(vendor_id=c["vendor_id"], date=renewal, type="saving", baseline_price=baseline,
                         negotiated_price=v.price, annualized_impact=round((baseline - v.price) * qty * 12, 2),
                         note=f"Renewal price cut of {abs(v.last_change):.0f}% against the previous term."))
    for name, when, quote, note in COST_AVOIDANCE:
        c = contracts[contracts["vendor_id"] == names[name]].iloc[0]
        qty = c["seats_contracted"] if c["billing_model"] == "per_seat" else 1
        negotiated = c["unit_price"] if c["billing_model"] == "per_seat" else 31500.00
        rows.append(dict(vendor_id=c["vendor_id"], date=date.fromisoformat(when), type="cost_avoidance",
                         baseline_price=quote, negotiated_price=negotiated,
                         annualized_impact=round((quote - negotiated) * qty * 12, 2), note=note))
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    df.insert(0, "event_id", [f"S{i:03d}" for i in range(1, len(df) + 1)])
    return df
