"""The SQL views, run in a real Postgres on the full data, must match the Python results.

scripts/pg_check.sh builds the database from sql/schema.sql, loads every CSV with sql/load.sql and
dumps the views into $PG_VIEWS_DIR. Without that variable these tests are skipped (they run in CI).
"""
import os
from pathlib import Path

import pandas as pd
import pytest

from src.export import SUPABASE_TABLES, build_tables

PG_DIR = os.environ.get("PG_VIEWS_DIR")
pytestmark = pytest.mark.skipif(not PG_DIR, reason="set PG_VIEWS_DIR after running scripts/pg_check.sh")
MONEY = ["actual_ytd", "forecast_rest_of_year", "landing", "budget_fy", "landing_vs_budget"]


@pytest.fixture(scope="module")
def py(cfg):
    return build_tables(cfg)


def view(name: str) -> pd.DataFrame:
    return pd.read_csv(Path(PG_DIR) / f"{name}.csv")


def test_every_row_of_every_csv_loaded(py):
    counts = view("row_counts").set_index("table_name")["n"]
    assert set(counts.index) == set(SUPABASE_TABLES)
    for table in SUPABASE_TABLES:
        assert counts[table] == len(py[table]), table


def test_fy_landing_matches_python_to_the_cent(py):
    sql = view("v_fy_landing").set_index("vendor_id").sort_index()
    ref = py["fy_landing"].set_index("vendor_id").sort_index()
    ref = ref[(ref["actual_ytd"] != 0) | (ref["forecast_rest_of_year"] != 0) | (ref["budget_fy"] != 0)]
    assert list(sql.index) == list(ref.index)
    for col in MONEY:
        assert (sql[col] - ref[col]).abs().max() <= 0.01, col
    assert list(sql.index[sql["unbudgeted"].astype(str).str.lower().isin(["t", "true"])]) == \
        list(ref.index[ref["budget_fy"] == 0])


def test_fy_landing_by_category_matches_python_to_the_cent(py):
    sql = view("v_fy_landing_by_category").set_index("category").sort_index()
    ref = py["fy_landing_by_category"].set_index("category").sort_index()
    assert list(sql.index) == list(ref.index)
    for col in MONEY:
        assert (sql[col] - ref[col]).abs().max() <= 0.01, col


def test_renewals_due_matches_python_recommendations(py):
    sql = view("v_renewals_due").set_index("contract_id").sort_index()
    ref = py["recommendations"].set_index("contract_id").sort_index()
    assert list(sql.index) == list(ref.index)
    assert (pd.to_datetime(sql["decision_deadline"]) == pd.to_datetime(ref["decision_deadline"])).all()
    assert (sql["days_to_deadline"] == ref["days_to_deadline"]).all()
    assert (sql["urgent"].astype(str).str.lower().isin(["t", "true"]) == ref["urgent"]).all()
    assert (sql["rule"] == ref["rule"]).all()
    assert (sql["estimated_annual_impact"] - ref["estimated_annual_impact"]).abs().max() <= 0.01


# --- views added for the front-end pages -------------------------------------------------------

def test_kpis_match_python(py, cfg):
    k = view("v_kpis").iloc[0]
    landing = py["fy_landing"]
    assert k["fy_landing"] == pytest.approx(landing["landing"].sum(), abs=0.05)
    assert k["fy_budget"] == pytest.approx(landing["budget_fy"].sum(), abs=0.05)
    s = py["savings"]
    anchor = pd.Timestamp(cfg["scenario"]["anchor_date"])
    ytd = s[(pd.to_datetime(s["date"]).dt.year == cfg["scenario"]["fiscal_year"]) & (pd.to_datetime(s["date"]) <= anchor)]
    assert k["savings_ytd"] == pytest.approx(ytd.loc[ytd["type"] == "saving", "annualized_impact"].sum(), abs=0.01)
    assert k["cost_avoidance_ytd"] == pytest.approx(ytd.loc[ytd["type"] == "cost_avoidance", "annualized_impact"].sum(), abs=0.01)
    rec = py["recommendations"].merge(py["contracts"][["contract_id", "annual_value"]], on="contract_id")
    days_to_end = (pd.to_datetime(rec["end_date"]) - anchor).dt.days
    assert k["renewals_next_90_days"] == (days_to_end <= cfg["thresholds"]["near_term_renewal_days"]).sum() == 6
    assert k["urgent_decisions"] == rec["urgent"].sum() == 2
    at_risk = rec[rec["auto_renew"] & (rec["rule"] != "renew")]["annual_value"].sum()
    assert k["value_at_risk_auto_renewal"] == pytest.approx(at_risk, abs=0.01)
    assert k["recommended_annual_impact"] == pytest.approx(rec["estimated_annual_impact"].sum(), abs=0.01)


def test_monthly_trend_matches_python_by_month(py):
    t = view("v_monthly_trend")
    t["month"] = pd.to_datetime(t["month"])
    by_month = t.groupby("month")[["actual", "budget", "forecast"]].sum()
    for series, table, col in (("actual", "monthly_spend", "actual_amount"),
                               ("budget", "budget", "budget_amount"),
                               ("forecast", "forecast_monthly", "forecast_amount")):
        ref = py[table].groupby("month")[col].sum()
        got = by_month[series].reindex(ref.index)
        assert (got - ref).abs().max() <= 0.05, series
    # no forecast in closed months, no actuals in future months
    last_closed = py["monthly_spend"]["month"].max()
    assert t.loc[t["month"] <= last_closed, "forecast"].isna().all()
    assert t.loc[t["month"] > last_closed, "actual"].isna().all()


def test_variance_waterfall_matches_python(py):
    from src.variance import waterfall
    w = view("v_variance_waterfall")
    for scope in ("ytd", "fy_landing"):
        ref = waterfall(py["variance"], scope).set_index("step")["amount"]
        got = w[w["scope"] == scope][["budget", "price", "volume", "unbudgeted", "landing"]].sum()
        for step in ref.index:
            assert got[step] == pytest.approx(ref[step], abs=0.05), (scope, step)
        assert got["budget"] + got["price"] + got["volume"] + got["unbudgeted"] == pytest.approx(got["landing"], abs=0.01)


def test_seat_utilization_covers_every_per_seat_month(py):
    u = view("v_seat_utilization")
    per_seat = py["contracts"].loc[py["contracts"]["billing_model"] == "per_seat", "contract_id"]
    assert len(u) == py["monthly_spend"]["contract_id"].isin(per_seat).sum()
    assert (u["utilization"] - u["seats_active"] / u["seats_contracted"]).abs().max() < 1e-9


def test_vendor_detail_matches_python(py, cfg):
    from src.generate import generate
    from src.recommend import utilization_table
    d = view("v_vendor_detail").set_index("contract_id")
    assert len(d) == 40
    util = utilization_table(generate(cfg), cfg).set_index("contract_id")["utilization"]
    live = py["contracts"].loc[(py["contracts"]["billing_model"] == "per_seat") & (py["contracts"]["status"] != "terminated"), "contract_id"]
    assert (d.loc[live, "utilization_3m"] - util[live]).abs().max() < 1e-6
    assert d.loc["C016", "price_vs_benchmark_pct"] == pytest.approx(102.25 / 81.80 - 1, abs=1e-4)
    assert d["rule_explanation"].notna().all()
    rec = py["recommendations"].set_index("contract_id")
    assert (d.loc[rec.index, "rule_explanation"] == rec["rationale"]).all()


# --- views for the interactive Overview and Budget vs. actual -----------------------------------

KPI_COLS = ["fy_landing", "fy_budget", "landing_vs_budget", "savings_ytd", "cost_avoidance_ytd",
            "renewals_next_90_days", "urgent_decisions", "value_at_risk_auto_renewal", "recommended_annual_impact"]


def test_kpis_by_category_add_up_to_overall_kpis():
    by_cat = view("v_kpis_by_category")
    total = view("v_kpis").iloc[0]
    assert len(by_cat) == 5
    for col in KPI_COLS:
        assert by_cat[col].sum() == pytest.approx(total[col], abs=0.05), col


def test_kpis_by_category_match_python(py):
    k = view("v_kpis_by_category").set_index("category")
    ref = py["fy_landing_by_category"].set_index("category")
    for col in ("landing_vs_budget",):
        assert (k[col] - ref[col]).abs().max() <= 0.01
    assert (k["fy_landing"] - ref["landing"]).abs().max() <= 0.01
    assert (k["landing_vs_budget_pct"] - ref["landing_vs_budget_pct"]).abs().max() < 1e-6
    sav = py["savings"].merge(py["vendors"][["vendor_id", "category"]], on="vendor_id")
    for t, col in (("saving", "savings_ytd"), ("cost_avoidance", "cost_avoidance_ytd")):
        ref_t = sav[sav["type"] == t].groupby("category")["annualized_impact"].sum().reindex(k.index).fillna(0)
        assert (k[col] - ref_t).abs().max() <= 0.01, col
    assert k.loc["Professional services", "savings_ytd"] == 0       # a real zero, not missing
    rec = py["recommendations"]
    assert (k["urgent_decisions"] == rec[rec["urgent"]].groupby("category").size().reindex(k.index).fillna(0)).all()


def test_monthly_variance_reconciles_every_row_to_the_cent():
    m = view("v_variance_monthly")
    cents = lambda s: (s * 100).round().astype("int64")
    assert (cents(m["budget"]) + cents(m["price"]) + cents(m["volume"]) + cents(m["unbudgeted"]) == cents(m["landing"])).all()


def test_monthly_variance_adds_up_to_waterfall():
    m = view("v_variance_monthly")
    w = view("v_variance_waterfall")
    keys = ["scope", "category", "owner_department"]
    cols = ["budget", "price", "volume", "unbudgeted", "landing"]
    a = m.groupby(keys)[cols].sum().sort_index()
    b = w.groupby(keys)[cols].sum().sort_index()
    assert list(a.index) == list(b.index)
    assert (a - b).abs().max().max() <= 0.01


def test_monthly_variance_months_and_forecast_flag(cfg):
    m = view("v_variance_monthly")
    m["month"] = pd.to_datetime(m["month"])
    fy = m[m["scope"] == "fy_landing"]
    assert sorted(fy["month"].dt.month.unique()) == list(range(1, 13))
    assert sorted(m[m["scope"] == "ytd"]["month"].dt.month.unique()) == list(range(1, 12))
    anchor = pd.Timestamp(cfg["scenario"]["anchor_date"])
    flag = m["is_forecast"].astype(str).str.lower().isin(["t", "true"])
    assert (flag == (m["month"] > anchor)).all()
    # closed months are identical in both scopes
    keys = ["month", "category", "owner_department"]
    cols = ["budget", "price", "volume", "unbudgeted", "landing"]
    y = m[m["scope"] == "ytd"].set_index(keys)[cols].sort_index()
    f = fy[fy["month"] <= anchor].set_index(keys)[cols].sort_index()
    assert (y - f.loc[y.index]).abs().max().max() == 0
