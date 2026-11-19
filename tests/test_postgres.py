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
