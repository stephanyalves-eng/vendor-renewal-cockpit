-- Vendor Spend & Renewal Cockpit - Postgres / Supabase schema.
-- ALL DATA LOADED INTO THESE TABLES IS SYNTHETIC (fictional fintech, fictional vendors), except the
-- public list prices in benchmarks, which carry a source URL and an as-of date.
--
-- Load order = table order below. Load the comment-free CSVs from data/supabase/, e.g. with psql:
--   \copy vendors from 'data/supabase/vendors.csv' with (format csv, header true)
-- Column names and order match the CSV headers exactly; do not rename them.
--
-- The Python pipeline computes the forecast, the variance split and the recommendations; the views
-- only join and aggregate them, so the app, the alert e-mail and the README show the same numbers.

-- ---------------------------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------------------------

create table scenario (
    scenario_id integer primary key,
    anchor_date date not null,              -- "today" in the synthetic scenario
    fiscal_year integer not null,
    currency text not null,
    ipca_annual_pct numeric(6,2) not null,
    renewal_window_days integer not null,
    near_term_renewal_days integer not null,
    urgent_deadline_days integer not null,
    seed bigint not null
);

create table vendors (
    vendor_id text primary key,
    name text not null,                     -- fictional
    category text not null,
    capability text not null,               -- vendors sharing a capability overlap
    owner_department text not null,
    criticality text not null,
    risk_tier text not null,
    check (category in ('SaaS', 'Cloud', 'Marketing', 'Professional services', 'Data and security')),
    check (criticality in ('low', 'medium', 'high')),
    check (risk_tier in ('low', 'medium', 'high'))
);

create table contracts (
    contract_id text primary key,
    vendor_id text not null references vendors (vendor_id),
    start_date date not null,
    end_date date not null,
    auto_renew boolean not null,
    notice_days integer not null,
    billing_model text not null,
    unit_price numeric(14,2) not null,      -- BRL per month: per seat, per usage unit, or monthly fee
    seats_contracted integer,               -- per_seat only
    annual_value numeric(14,2) not null,
    price_escalator_pct numeric(6,2) not null,
    termination_fee numeric(14,2) not null,
    status text not null,                   -- editable in the app
    check (billing_model in ('per_seat', 'usage', 'fixed')),
    check (status in ('onboarding', 'active', 'renewal_window', 'renegotiating', 'terminated')),
    check (notice_days > 0),
    check (end_date > start_date)
);

create table monthly_spend (
    month date not null,                    -- first day of the month
    vendor_id text not null references vendors (vendor_id),
    contract_id text not null references contracts (contract_id),
    actual_amount numeric(14,2) not null,
    unit_price_paid numeric(14,4) not null,
    seats_active integer,                   -- per_seat only
    units_used numeric,                     -- usage only
    billed_qty numeric not null,            -- seats billed (incl. true-up), units, or 1 for a fixed fee
    primary key (month, contract_id)
);

create table budget (
    month date not null,
    vendor_id text not null references vendors (vendor_id),
    budget_qty numeric not null,
    budget_unit_price numeric(14,4) not null,
    budget_amount numeric(14,2) not null,
    primary key (month, vendor_id)
);

create table headcount (
    month date not null,
    department text not null,
    headcount integer not null,
    primary key (month, department)
);

create table benchmarks (
    vendor_id text primary key references vendors (vendor_id),
    reference_product text not null,        -- real product (the only real names in the database)
    list_price numeric(14,2) not null,      -- as published
    list_currency text not null,
    list_price_per_seat numeric(14,2) not null,  -- BRL per seat per month
    billing_basis text not null,
    source_url text not null,
    as_of date not null
);

create table savings (
    event_id text primary key,
    vendor_id text not null references vendors (vendor_id),
    date date not null,
    type text not null,                     -- saving: vs. previous price; cost_avoidance: vs. first quote
    baseline_price numeric(14,4) not null,
    negotiated_price numeric(14,4) not null,
    annualized_impact numeric(14,2) not null,
    note text,
    check (type in ('saving', 'cost_avoidance'))
);

create table forecast_monthly (
    month date not null,
    vendor_id text not null references vendors (vendor_id),
    contract_id text not null references contracts (contract_id),
    billing_model text not null,
    forecast_qty numeric not null,
    forecast_unit_price numeric(14,4) not null,
    forecast_amount numeric(14,2) not null,
    method text not null,
    primary key (month, contract_id),
    check (forecast_amount >= 0)
);

create table variance (
    fiscal_year integer not null,
    scope text not null,                    -- ytd: closed months; fy_landing: actuals + forecast
    month date not null,
    vendor_id text not null references vendors (vendor_id),
    category text not null,
    owner_department text not null,
    actual_qty numeric not null,
    actual_unit_price numeric,
    actual_amount numeric(14,2) not null,
    budget_qty numeric,
    budget_unit_price numeric(14,4),
    budget_amount numeric(14,2) not null,
    price_var numeric(14,2) not null,
    volume_var numeric(14,2) not null,
    unbudgeted_var numeric(14,2) not null,
    total_var numeric(14,2) not null,
    primary key (scope, month, vendor_id),
    check (scope in ('ytd', 'fy_landing'))
);

create table recommendations (
    contract_id text primary key references contracts (contract_id),
    vendor_id text not null references vendors (vendor_id),
    vendor_name text not null,
    category text not null,
    end_date date not null,
    auto_renew boolean not null,
    notice_days integer not null,
    decision_deadline date not null,
    days_to_deadline integer not null,
    urgent boolean not null,
    rule text not null,
    recommendation text not null,
    estimated_annual_impact numeric(14,2) not null,
    utilization numeric(6,4),
    peak_active_seats integer,
    target_seats integer,
    consolidate_into text references contracts (contract_id),
    rationale text not null,
    check (rule in ('terminate', 'consolidate', 'right_size', 'renegotiate', 'renew'))
);

-- Written by the app, not loaded from CSV ----------------------------------------------------

-- Fields an AI step extracted from an uploaded contract PDF. Visitors see stored results from a
-- real run; only the owner can run a new extraction (see sql/supabase_policies.sql).
create table contract_extractions (
    extraction_id bigint generated always as identity primary key,
    contract_id text references contracts (contract_id),
    file_name text not null,
    field text not null,
    extracted_value text,
    confidence numeric(4,3),
    uncertain boolean not null default false,
    model text,
    extracted_at timestamptz not null default now(),
    check (field in ('end_date', 'auto_renew', 'notice_days', 'price_escalator_pct', 'termination_fee')),
    check (confidence is null or confidence between 0 and 1)
);

-- Signed-in users allowed to write (contract status, new extractions). Rows are added by hand
-- in the database, never from the app or this repository.
create table app_admins (
    user_id uuid primary key,
    added_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------------------------
-- Views for the front end
-- ---------------------------------------------------------------------------------------------

-- FY landing by vendor: actuals of the fiscal year to date + forecast of the remaining months,
-- compared with the full-year budget.
create or replace view v_fy_landing with (security_invoker = true) as
with s as (
    select anchor_date, fiscal_year from scenario where scenario_id = 1
),
act as (
    select m.vendor_id, sum(m.actual_amount) as actual_ytd
    from monthly_spend m cross join s
    where extract(year from m.month) = s.fiscal_year and m.month <= s.anchor_date
    group by m.vendor_id
),
fc as (
    select f.vendor_id, sum(f.forecast_amount) as forecast_rest_of_year
    from forecast_monthly f cross join s
    where extract(year from f.month) = s.fiscal_year and f.month > s.anchor_date
    group by f.vendor_id
),
bud as (
    select b.vendor_id, sum(b.budget_amount) as budget_fy
    from budget b cross join s
    where extract(year from b.month) = s.fiscal_year
    group by b.vendor_id
)
select
    s.fiscal_year,
    v.vendor_id,
    v.name as vendor_name,
    v.category,
    v.owner_department,
    coalesce(act.actual_ytd, 0) as actual_ytd,
    coalesce(fc.forecast_rest_of_year, 0) as forecast_rest_of_year,
    coalesce(act.actual_ytd, 0) + coalesce(fc.forecast_rest_of_year, 0) as landing,
    coalesce(bud.budget_fy, 0) as budget_fy,
    coalesce(act.actual_ytd, 0) + coalesce(fc.forecast_rest_of_year, 0) - coalesce(bud.budget_fy, 0) as landing_vs_budget,
    case when coalesce(bud.budget_fy, 0) > 0
         then (coalesce(act.actual_ytd, 0) + coalesce(fc.forecast_rest_of_year, 0) - bud.budget_fy) / bud.budget_fy
    end as landing_vs_budget_pct,
    bud.vendor_id is null as unbudgeted
from vendors v
cross join s
left join act on act.vendor_id = v.vendor_id
left join fc on fc.vendor_id = v.vendor_id
left join bud on bud.vendor_id = v.vendor_id
where act.vendor_id is not null or fc.vendor_id is not null or bud.vendor_id is not null;

-- Same landing rolled up by category (the Overview bar chart).
create or replace view v_fy_landing_by_category with (security_invoker = true) as
select
    fiscal_year,
    category,
    sum(actual_ytd) as actual_ytd,
    sum(forecast_rest_of_year) as forecast_rest_of_year,
    sum(landing) as landing,
    sum(budget_fy) as budget_fy,
    sum(landing_vs_budget) as landing_vs_budget,
    case when sum(budget_fy) > 0 then sum(landing_vs_budget) / sum(budget_fy) end as landing_vs_budget_pct
from v_fy_landing
group by fiscal_year, category;

-- Contracts that end within the renewal window, with the recommendation, its estimated annual
-- impact and the decision deadline (end date minus notice period). Dates come from the scenario
-- anchor, not CURRENT_DATE, so the synthetic pipeline never goes stale. Deadline and status are
-- read from the live contracts row, so edits made in the app show up immediately.
create or replace view v_renewals_due with (security_invoker = true) as
with s as (
    select anchor_date, renewal_window_days, urgent_deadline_days from scenario where scenario_id = 1
)
select
    c.contract_id,
    v.vendor_id,
    v.name as vendor_name,
    v.category,
    c.end_date,
    c.auto_renew,
    c.notice_days,
    c.end_date - c.notice_days as decision_deadline,
    (c.end_date - c.notice_days) - s.anchor_date as days_to_deadline,
    ((c.end_date - c.notice_days) - s.anchor_date) <= s.urgent_deadline_days as urgent,
    c.end_date - s.anchor_date as days_to_end,
    r.rule,
    r.recommendation,
    r.estimated_annual_impact,
    r.utilization,
    r.target_seats,
    r.consolidate_into,
    r.rationale,
    c.annual_value,
    c.status
from contracts c
join vendors v on v.vendor_id = c.vendor_id
cross join s
left join recommendations r on r.contract_id = c.contract_id
where c.status <> 'terminated'
  and c.end_date - s.anchor_date between 1 and s.renewal_window_days
order by decision_deadline;

-- One-row KPI strip for the Overview page.
-- value_at_risk_auto_renewal: annual value of auto-renewing contracts in the renewal window whose
-- recommendation is anything but "renew" - money that rolls over on today's terms if nobody acts.
create or replace view v_kpis with (security_invoker = true) as
with s as (
    select anchor_date, fiscal_year, near_term_renewal_days, urgent_deadline_days
    from scenario where scenario_id = 1
),
landing as (
    select sum(landing) as fy_landing, sum(budget_fy) as fy_budget from v_fy_landing
),
sav as (
    select
        coalesce(sum(sv.annualized_impact) filter (where sv.type = 'saving'), 0) as savings_ytd,
        coalesce(sum(sv.annualized_impact) filter (where sv.type = 'cost_avoidance'), 0) as cost_avoidance_ytd
    from savings sv cross join s
    where extract(year from sv.date) = s.fiscal_year and sv.date <= s.anchor_date
),
ren as (
    select
        count(*) filter (where r.days_to_end <= s.near_term_renewal_days) as renewals_next_90_days,
        count(*) filter (where r.urgent) as urgent_decisions,
        coalesce(sum(r.annual_value) filter (where r.auto_renew and r.rule <> 'renew'), 0) as value_at_risk_auto_renewal,
        coalesce(sum(r.estimated_annual_impact), 0) as recommended_annual_impact
    from v_renewals_due r cross join s
)
select
    s.fiscal_year,
    s.anchor_date,
    landing.fy_landing,
    landing.fy_budget,
    landing.fy_landing - landing.fy_budget as landing_vs_budget,
    (landing.fy_landing - landing.fy_budget) / nullif(landing.fy_budget, 0) as landing_vs_budget_pct,
    sav.savings_ytd,
    sav.cost_avoidance_ytd,
    ren.renewals_next_90_days,
    ren.urgent_decisions,
    ren.value_at_risk_auto_renewal,
    ren.recommended_annual_impact
from s cross join landing cross join sav cross join ren;

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

-- Monthly actuals, budget and forecast by category and department (Budget vs. actual chart).
-- A column is null where that series has no value: no forecast for closed months, no actuals ahead.
create or replace view v_monthly_trend with (security_invoker = true) as
select month, category, owner_department,
       sum(actual) as actual, sum(budget) as budget, sum(forecast) as forecast
from (
    select m.month, v.category, v.owner_department, m.actual_amount as actual,
           null::numeric as budget, null::numeric as forecast
    from monthly_spend m join vendors v on v.vendor_id = m.vendor_id
    union all
    select b.month, v.category, v.owner_department, null, b.budget_amount, null
    from budget b join vendors v on v.vendor_id = b.vendor_id
    union all
    select f.month, v.category, v.owner_department, null, null, f.forecast_amount
    from forecast_monthly f join vendors v on v.vendor_id = f.vendor_id
) series
group by month, category, owner_department;

-- Budget-to-landing waterfall steps by category and department; the app sums the filtered rows.
-- budget + price + volume + unbudgeted = landing, to the cent.
create or replace view v_variance_waterfall with (security_invoker = true) as
select fiscal_year, scope, category, owner_department,
       sum(budget_amount) as budget,
       sum(price_var) as price,
       sum(volume_var) as volume,
       sum(unbudgeted_var) as unbudgeted,
       sum(actual_amount) as landing
from variance
group by fiscal_year, scope, category, owner_department;

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

-- Active vs. contracted seats per month for per-seat contracts (Vendor detail chart).
create or replace view v_seat_utilization with (security_invoker = true) as
select m.month, m.vendor_id, m.contract_id, m.seats_active, c.seats_contracted,
       m.seats_active::numeric / nullif(c.seats_contracted, 0) as utilization
from monthly_spend m
join contracts c on c.contract_id = m.contract_id
where c.billing_model = 'per_seat';

-- Everything the Vendor detail page shows, one row per vendor.
create or replace view v_vendor_detail with (security_invoker = true) as
with s as (
    select anchor_date, renewal_window_days from scenario where scenario_id = 1
),
util as (
    select u.contract_id, avg(u.seats_active)::numeric / max(u.seats_contracted) as utilization_3m
    from v_seat_utilization u cross join s
    where u.month > s.anchor_date - interval '3 months'
    group by u.contract_id
)
select
    v.vendor_id, v.name as vendor_name, v.category, v.capability, v.owner_department,
    v.criticality, v.risk_tier,
    c.contract_id, c.start_date, c.end_date, c.auto_renew, c.notice_days,
    c.end_date - c.notice_days as decision_deadline,
    c.billing_model, c.unit_price, c.seats_contracted, c.annual_value,
    c.price_escalator_pct, c.termination_fee, c.status,
    util.utilization_3m,
    b.reference_product as benchmark_product,
    b.list_price_per_seat as benchmark_price_per_seat,
    b.source_url as benchmark_source_url,
    b.as_of as benchmark_as_of,
    c.unit_price / nullif(b.list_price_per_seat, 0) - 1 as price_vs_benchmark_pct,
    l.landing as fy_landing,
    l.budget_fy as fy_budget,
    r.recommendation,
    r.estimated_annual_impact,
    coalesce(r.rationale,
             case when c.status = 'terminated' then 'Contract terminated; no renewal decision.'
                  else 'Renews on ' || to_char(c.end_date, 'YYYY-MM-DD') || ', outside the '
                       || s.renewal_window_days || '-day review window.' end) as rule_explanation
from vendors v
join contracts c on c.vendor_id = v.vendor_id
cross join s
left join util on util.contract_id = c.contract_id
left join benchmarks b on b.vendor_id = v.vendor_id
left join v_fy_landing l on l.vendor_id = v.vendor_id
left join recommendations r on r.contract_id = c.contract_id;

-- ---------------------------------------------------------------------------------------------
-- Read-only public demo: anyone may read. Writes (contract status, new extractions) are limited
-- to the owner by sql/supabase_policies.sql, which uses Supabase's auth schema and roles.
-- ---------------------------------------------------------------------------------------------

alter table scenario enable row level security;
alter table vendors enable row level security;
alter table contracts enable row level security;
alter table monthly_spend enable row level security;
alter table budget enable row level security;
alter table headcount enable row level security;
alter table benchmarks enable row level security;
alter table savings enable row level security;
alter table forecast_monthly enable row level security;
alter table variance enable row level security;
alter table recommendations enable row level security;

create policy "public read" on scenario for select using (true);
create policy "public read" on vendors for select using (true);
create policy "public read" on contracts for select using (true);
create policy "public read" on monthly_spend for select using (true);
create policy "public read" on budget for select using (true);
create policy "public read" on headcount for select using (true);
create policy "public read" on benchmarks for select using (true);
create policy "public read" on savings for select using (true);
create policy "public read" on forecast_monthly for select using (true);
create policy "public read" on variance for select using (true);
create policy "public read" on recommendations for select using (true);

alter table contract_extractions enable row level security;
alter table app_admins enable row level security;   -- no public policy: nobody can list admins
create policy "public read" on contract_extractions for select using (true);
