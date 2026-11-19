"""Load config.yaml into a plain dict with dates parsed and required keys checked."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "config.yaml"

REQUIRED = {
    "seed": None,
    "scenario": ["anchor_date", "history_start", "history_end", "fiscal_year", "forecast_horizon_months"],
    "economics": ["ipca_annual_pct", "fx_usd_brl"],
    "thresholds": [
        "renewal_window_days", "near_term_renewal_days", "urgent_deadline_days",
        "terminate_utilization_max", "rightsize_utilization_max", "rightsize_buffer_pct",
        "utilization_lookback_months", "peak_lookback_months", "usage_trend_months",
        "adoption_lookback_months", "headcount_trend_months", "benchmark_tolerance_pct",
    ],
    "generator": ["n_vendors"],
}


def _as_date(value: Any) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def load_config(path: str | Path = DEFAULT_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    for section, keys in REQUIRED.items():
        if section not in cfg:
            raise KeyError(f"config.yaml is missing '{section}'")
        for key in keys or []:
            if key not in cfg[section]:
                raise KeyError(f"config.yaml is missing '{section}.{key}'")
    for key in ("anchor_date", "history_start", "history_end"):
        cfg["scenario"][key] = _as_date(cfg["scenario"][key])
    return cfg
