"""sql/schema.sql must match the exported CSVs column for column, and define the front-end views."""
import re
from pathlib import Path

import pytest

from src.config import ROOT
from src.export import SUPABASE_TABLES, run

SCHEMA = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
NOT_COLUMNS = ("primary", "foreign", "unique", "check", "constraint")
APP_TABLES = ["contract_extractions", "app_admins"]  # written by the app, not loaded from CSV
VIEWS = ["v_fy_landing", "v_fy_landing_by_category", "v_renewals_due", "v_kpis", "v_monthly_trend",
         "v_variance_waterfall", "v_seat_utilization", "v_vendor_detail", "v_kpis_by_category",
         "v_variance_monthly"]


def table_columns(sql: str) -> dict[str, list[str]]:
    tables = {}
    for name, body in re.findall(r"create table (\w+) \((.*?)\n\);", sql, re.IGNORECASE | re.DOTALL):
        cols = []
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("--") or line.lower().startswith(NOT_COLUMNS):
                continue
            cols.append(line.split()[0])
        tables[name] = cols
    return tables


@pytest.fixture(scope="module")
def exported(tmp_path_factory, cfg):
    root = tmp_path_factory.mktemp("schema")
    run(cfg, root)
    return root / "supabase"


def test_every_exported_table_is_created_in_load_order():
    tables = table_columns(SCHEMA)
    assert list(tables) == SUPABASE_TABLES + APP_TABLES


@pytest.mark.parametrize("table", SUPABASE_TABLES)
def test_columns_match_csv_header(exported, table):
    header = (exported / f"{table}.csv").read_text(encoding="utf-8").splitlines()[0].split(",")
    assert table_columns(SCHEMA)[table] == header


def test_front_end_views_exist():
    for view in VIEWS:
        assert re.search(rf"create or replace view {view}\b", SCHEMA, re.IGNORECASE), view


def test_renewals_view_is_driven_by_scenario_not_today():
    """The synthetic scenario has a fixed anchor date; CURRENT_DATE would empty the view over time."""
    body = SCHEMA.split("create or replace view v_renewals_due", 1)[1]
    assert "current_date" not in body.lower()
    assert "renewal_window_days" in body and "notice_days" in body


def test_views_respect_row_level_security():
    assert SCHEMA.lower().count("security_invoker = true") == len(VIEWS)


def test_supabase_policies_never_grant_anon_writes():
    policies = (ROOT / "sql" / "supabase_policies.sql").read_text(encoding="utf-8").lower()
    assert "revoke insert, update, delete, truncate on all tables in schema public from anon, authenticated" in policies
    for line in policies.splitlines():
        if line.startswith("grant") and "anon" in line:
            assert line.startswith(("grant usage on schema", "grant select on")), line


def test_supabase_policies_grant_reads_explicitly():
    """New Supabase projects do not expose psql-created tables to the API: reads must be granted."""
    policies = (ROOT / "sql" / "supabase_policies.sql").read_text(encoding="utf-8").lower()
    assert "grant select on all tables in schema public to anon, authenticated, service_role" in policies
    assert "grant execute on function is_app_admin() to authenticated" in policies


def test_patches_match_schema_and_grant_reads():
    """A patch must not drift from schema.sql, and must grant reads (new Supabase projects need it)."""
    for patch in sorted((ROOT / "sql" / "patches").glob("*.sql")):
        text = patch.read_text(encoding="utf-8")
        for view in re.findall(r"create or replace view (\w+) ", text):
            start = text.index(f"create or replace view {view} ")
            end = text.index(";", start) + 1
            block = text[start:end]
            assert block in SCHEMA, f"{patch.name}: {view} differs from schema.sql"
            grant = re.compile("grant select on [^;]*" + re.escape(view) + "[,; ][^;]*to anon")
            assert grant.search(text), f"{patch.name}: no read grant for {view}"
