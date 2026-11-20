-- Patch 001: views for the interactive Overview and Budget vs. actual pages.
-- Apply once on an existing database (Supabase SQL editor or psql). Safe to re-run.
-- The view definitions are identical to sql/schema.sql (checked by tests/test_schema.py).

-- The same KPIs per category, for the Overview's category filter. Same definitions as v_kpis; the
-- categories add up to v_kpis exactly. A category with nothing to report shows a real zero.
create or replace view v_kpis_by_category with (security_invoker = true) as
with s as (
    select anchor_date, fiscal_year, near_term_renewal_days from scenario where scenario_id = 1
),
cats as (
    select distinct category from vendors
),
landing as (
    select category, sum(landing) as fy_landing, sum(budget_fy) as fy_budget
    from v_fy_landing group by category
),
sav as (
    select v.category,
        sum(sv.annualized_impact) filter (where sv.type = 'saving') as savings_ytd,
        sum(sv.annualized_impact) filter (where sv.type = 'cost_avoidance') as cost_avoidance_ytd
    from savings sv join vendors v on v.vendor_id = sv.vendor_id cross join s
    where extract(year from sv.date) = s.fiscal_year and sv.date <= s.anchor_date
    group by v.category
),
ren as (
    select r.category,
        count(*) filter (where r.days_to_end <= s.near_term_renewal_days) as renewals_next_90_days,
        count(*) filter (where r.urgent) as urgent_decisions,
        sum(r.annual_value) filter (where r.auto_renew and r.rule <> 'renew') as value_at_risk_auto_renewal,
        sum(r.estimated_annual_impact) as recommended_annual_impact
    from v_renewals_due r cross join s
    group by r.category
)
select
    s.fiscal_year,
    s.anchor_date,
    c.category,
    coalesce(landing.fy_landing, 0) as fy_landing,
    coalesce(landing.fy_budget, 0) as fy_budget,
    coalesce(landing.fy_landing, 0) - coalesce(landing.fy_budget, 0) as landing_vs_budget,
    (coalesce(landing.fy_landing, 0) - coalesce(landing.fy_budget, 0)) / nullif(landing.fy_budget, 0) as landing_vs_budget_pct,
    coalesce(sav.savings_ytd, 0) as savings_ytd,
    coalesce(sav.cost_avoidance_ytd, 0) as cost_avoidance_ytd,
    coalesce(ren.renewals_next_90_days, 0) as renewals_next_90_days,
    coalesce(ren.urgent_decisions, 0) as urgent_decisions,
    coalesce(ren.value_at_risk_auto_renewal, 0) as value_at_risk_auto_renewal,
    coalesce(ren.recommended_annual_impact, 0) as recommended_annual_impact
from cats c
cross join s
left join landing on landing.category = c.category
left join sav on sav.category = c.category
left join ren on ren.category = c.category;

-- The same split per month, so a month or a single component (price, volume, unbudgeted) can be
-- selected. Every row reconciles: budget + price + volume + unbudgeted = landing, to the cent, and
-- the months add up to v_variance_waterfall. is_forecast marks months after the scenario date.
-- For closed months the ytd and fy_landing rows are identical; fy_landing also holds the forecast months.
create or replace view v_variance_monthly with (security_invoker = true) as
select va.fiscal_year, va.scope, va.month, va.category, va.owner_department,
       va.month > s.anchor_date as is_forecast,
       sum(va.budget_amount) as budget,
       sum(va.price_var) as price,
       sum(va.volume_var) as volume,
       sum(va.unbudgeted_var) as unbudgeted,
       sum(va.actual_amount) as landing
from variance va
cross join (select anchor_date from scenario where scenario_id = 1) s
group by va.fiscal_year, va.scope, va.month, va.category, va.owner_department, s.anchor_date;

-- New Supabase projects do not expose views created outside the dashboard: grant reads explicitly.
grant select on v_kpis_by_category, v_variance_monthly to anon, authenticated, service_role;
