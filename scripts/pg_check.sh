#!/usr/bin/env bash
# Build the database from scratch in a real Postgres, load every CSV, and dump the views so
# tests/test_postgres.py can compare them with the Python results.
# Connection comes from the standard PG* environment variables (PGHOST, PGUSER, PGPASSWORD, ...).
# Usage (from the repository root): PG_VIEWS_DIR=/tmp/pg bash scripts/pg_check.sh
set -euo pipefail
OUT="${PG_VIEWS_DIR:?set PG_VIEWS_DIR to the folder for the view dumps}"
mkdir -p "$OUT"
PSQL=(psql -X -q -v ON_ERROR_STOP=1)

export PGOPTIONS="-c client_min_messages=warning"

# Start clean so the script can be re-run: drop only the cockpit's own objects, nothing else.
"${PSQL[@]}" -c "drop view if exists v_vendor_detail, v_seat_utilization, v_variance_waterfall,
    v_monthly_trend, v_kpis, v_renewals_due, v_fy_landing_by_category, v_fy_landing;
  drop table if exists contract_extractions, app_admins, recommendations, variance, forecast_monthly,
    savings, benchmarks, headcount, budget, monthly_spend, contracts, vendors, scenario;"
"${PSQL[@]}" -f sql/schema.sql
"${PSQL[@]}" -f sql/load.sql

# Supabase write rules, tested against stand-ins for Supabase's roles and auth.uid().
"${PSQL[@]}" -f scripts/ci_supabase_stubs.sql
"${PSQL[@]}" -f sql/supabase_policies.sql
psql -X -v ON_ERROR_STOP=1 -f scripts/ci_policy_check.sql | grep "Policy check"

VIEWS=(v_fy_landing v_fy_landing_by_category v_renewals_due v_kpis v_monthly_trend
       v_variance_waterfall v_seat_utilization v_vendor_detail)
for view in "${VIEWS[@]}"; do
  "${PSQL[@]}" -c "\copy (select * from $view) to '$OUT/$view.csv' with (format csv, header true)"
done

"${PSQL[@]}" -c "\copy (
  select 'scenario' as table_name, count(*) as n from scenario union all
  select 'vendors', count(*) from vendors union all
  select 'contracts', count(*) from contracts union all
  select 'monthly_spend', count(*) from monthly_spend union all
  select 'budget', count(*) from budget union all
  select 'headcount', count(*) from headcount union all
  select 'benchmarks', count(*) from benchmarks union all
  select 'savings', count(*) from savings union all
  select 'forecast_monthly', count(*) from forecast_monthly union all
  select 'variance', count(*) from variance union all
  select 'recommendations', count(*) from recommendations
) to '$OUT/row_counts.csv' with (format csv, header true)"

echo "Postgres check: schema applied, all CSVs loaded, views dumped to $OUT"
