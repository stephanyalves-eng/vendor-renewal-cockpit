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

-- ---------------------------------------------------------------------------------------------
-- Read-only public demo: anyone may read; only contracts.status is meant to be edited in the app
-- (add an update policy for it once authentication is decided).
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
