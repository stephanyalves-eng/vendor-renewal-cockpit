-- Load the synthetic CSVs into the tables created by sql/schema.sql.
-- Run from the repository root with psql:
--   psql -v ON_ERROR_STOP=1 -f sql/schema.sql
--   psql -v ON_ERROR_STOP=1 -f sql/load.sql
-- Uses the comment-free copies in data/supabase/ (Postgres COPY cannot skip comment lines).
\set ON_ERROR_STOP on
\copy scenario from 'data/supabase/scenario.csv' with (format csv, header true)
\copy vendors from 'data/supabase/vendors.csv' with (format csv, header true)
\copy contracts from 'data/supabase/contracts.csv' with (format csv, header true)
\copy monthly_spend from 'data/supabase/monthly_spend.csv' with (format csv, header true)
\copy budget from 'data/supabase/budget.csv' with (format csv, header true)
\copy headcount from 'data/supabase/headcount.csv' with (format csv, header true)
\copy benchmarks from 'data/supabase/benchmarks.csv' with (format csv, header true)
\copy savings from 'data/supabase/savings.csv' with (format csv, header true)
\copy forecast_monthly from 'data/supabase/forecast_monthly.csv' with (format csv, header true)
\copy variance from 'data/supabase/variance.csv' with (format csv, header true)
\copy recommendations from 'data/supabase/recommendations.csv' with (format csv, header true)
