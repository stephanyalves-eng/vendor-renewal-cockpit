"""Renewal recommendations for every contract that ends inside the renewal window.

Rules are checked in priority order; the first one that matches wins:

1. terminate   - low criticality and utilization below 20%.
                 Impact: annual value minus termination fee.
2. consolidate - another live vendor covers the same capability, and this one is not the keeper
                 (keeper = highest utilization, then lowest unit price).
                 Impact: annual value of the contract that goes away.
3. right_size  - utilization below 60%. Cut seats to the recent peak of active seats + 10%.
                 Impact: seats cut x unit price x 12.
4. renegotiate - unit price above the public list price, or escalator above IPCA.
                 Impact: the larger of the two gaps (never the sum, to avoid double counting).
5. renew       - none of the above. Impact: zero.

Every recommendation carries a decision deadline = end date - notice period: after that date an
auto-renewing contract rolls over on its current terms. All thresholds come from config.yaml.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def utilization_table(data: dict, cfg: dict) -> pd.DataFrame:
    """Per per-seat contract: average utilization and peak active seats over the look-back windows."""
    th = cfg["thresholds"]
    spend = data["monthly_spend"]
    months = sorted(spend["month"].unique())
    seats = data["contracts"].set_index("contract_id")["seats_contracted"].dropna()
    s = spend[spend["contract_id"].isin(seats.index)]
    recent = s[s["month"].isin(months[-th["utilization_lookback_months"]:])]
    peak_window = s[s["month"].isin(months[-th["peak_lookback_months"]:])]
    out = pd.DataFrame({
        "avg_active_seats": recent.groupby("contract_id")["seats_active"].mean(),
        "peak_active_seats": peak_window.groupby("contract_id")["seats_active"].max(),
    })
    out["seats_contracted"] = seats.reindex(out.index).astype(float)
    out["utilization"] = out["avg_active_seats"] / out["seats_contracted"]
    return out.reset_index().rename(columns={"index": "contract_id"})


def _keepers(contracts: pd.DataFrame, vendors: pd.DataFrame, util: pd.Series) -> dict[str, str]:
    """capability -> contract_id of the tool to keep, for capabilities covered by 2+ live vendors."""
    live = contracts[contracts["status"] != "terminated"].merge(vendors[["vendor_id", "capability"]], on="vendor_id")
    keepers = {}
    for cap, group in live.groupby("capability"):
        if len(group) < 2:
            continue
        g = group.assign(util=group["contract_id"].map(util).fillna(0.0))
        best = g.sort_values(["util", "unit_price"], ascending=[False, True]).iloc[0]
        keepers[cap] = best["contract_id"]
    return keepers


def recommend(data: dict, cfg: dict) -> pd.DataFrame:
    th, ipca = cfg["thresholds"], cfg["economics"]["ipca_annual_pct"]
    anchor = pd.Timestamp(cfg["scenario"]["anchor_date"])
    contracts, vendors = data["contracts"], data["vendors"]
    vend = vendors.set_index("vendor_id")
    util_tab = utilization_table(data, cfg).set_index("contract_id")
    util = util_tab["utilization"]
    bench = data["benchmarks"].set_index("vendor_id")
    keepers = _keepers(contracts, vendors, util)
    names = contracts.set_index("contract_id")["vendor_id"].map(vend["name"])

    rows = []
    for c in contracts.itertuples(index=False):
        end = pd.Timestamp(c.end_date)
        days_to_end = (end - anchor).days
        if c.status == "terminated" or not (0 < days_to_end <= th["renewal_window_days"]):
            continue
        v = vend.loc[c.vendor_id]
        u = util.get(c.contract_id, np.nan)
        peak = util_tab["peak_active_seats"].get(c.contract_id, np.nan)
        target = None
        keeper = keepers.get(v["capability"])

        if c.billing_model == "per_seat" and v["criticality"] == "low" and u < th["terminate_utilization_max"]:
            rule, impact = "terminate", c.annual_value - c.termination_fee
            why = (f"Low-criticality tool with {u:.0%} seat utilization (threshold "
                   f"{th['terminate_utilization_max']:.0%}). Let it expire; savings net of the "
                   f"termination fee.")
        elif keeper is not None and keeper != c.contract_id:
            rule, impact = "consolidate", c.annual_value
            why = (f"Overlaps with {names[keeper]} on {v['capability'].replace('_', ' ').replace('e signature', 'e-signature')}. "
                   f"{names[keeper]} has the higher utilization, so move users there and drop this contract.")
        else:
            rule, impact, why = None, 0.0, ""
            if c.billing_model == "per_seat" and u < th["rightsize_utilization_max"]:
                target = math.ceil(peak * (1 + th["rightsize_buffer_pct"]))
                cut = int(c.seats_contracted) - target
                if cut > 0:
                    rule, impact = "right_size", cut * c.unit_price * 12
                    why = (f"Only {u:.0%} of {c.seats_contracted} seats are used. Renew at {target} seats "
                           f"(peak {int(peak)} active + {th['rightsize_buffer_pct']:.0%} buffer).")
            if rule is None:
                gaps = []
                if c.vendor_id in bench.index and c.billing_model == "per_seat":
                    list_price = bench.loc[c.vendor_id, "list_price_per_seat"]
                    if c.unit_price > list_price * (1 + th["benchmark_tolerance_pct"]):
                        gaps.append(((c.unit_price - list_price) * c.seats_contracted * 12,
                                     f"pays {c.unit_price:.2f} per seat vs. public list price {list_price:.2f} "
                                     f"(see benchmarks table)"))
                if c.price_escalator_pct > ipca:
                    gaps.append((c.annual_value * (c.price_escalator_pct - ipca) / 100,
                                 f"escalator of {c.price_escalator_pct:.1f}% vs. IPCA of {ipca:.1f}%"))
                if gaps:
                    impact, reason = max(gaps, key=lambda g: g[0])
                    rule = "renegotiate"
                    why = f"Renegotiate: {reason}."
                    if len(gaps) > 1:
                        why += " Both gaps apply; impact counts only the larger one."
                else:
                    rule, impact = "renew", 0.0
                    why = "Healthy utilization, price in line with benchmark and inflation. Renew as is."

        deadline = end - pd.Timedelta(days=int(c.notice_days))
        days_to_deadline = (deadline - anchor).days
        rows.append(dict(
            contract_id=c.contract_id, vendor_id=c.vendor_id, vendor_name=v["name"], category=v["category"],
            end_date=end, auto_renew=bool(c.auto_renew), notice_days=int(c.notice_days),
            decision_deadline=deadline, days_to_deadline=days_to_deadline,
            urgent=bool(days_to_deadline <= th["urgent_deadline_days"]),
            rule=rule, recommendation=RECOMMENDATION_LABEL[rule],
            estimated_annual_impact=round(float(impact), 2),
            utilization=None if np.isnan(u) else round(float(u), 4),
            peak_active_seats=None if np.isnan(peak) else int(peak),
            target_seats=target, consolidate_into=keeper if rule == "consolidate" else None,
            rationale=why,
        ))
    return pd.DataFrame(rows).sort_values("decision_deadline").reset_index(drop=True)


RECOMMENDATION_LABEL = {
    "terminate": "Terminate",
    "consolidate": "Consolidate",
    "right_size": "Right-size",
    "renegotiate": "Renegotiate",
    "renew": "Renew",
}
