-- CI ONLY: prove the write rules in sql/supabase_policies.sql. Everything is rolled back.
\set ON_ERROR_STOP on
begin;
insert into app_admins (user_id) values ('00000000-0000-0000-0000-000000000001');

-- 1. Visitors can read every page's data but cannot change anything.
set local role anon;
do $$ declare n int; begin
    select count(*) into n from v_kpis;
    if n <> 1 then raise exception 'FAIL: anon cannot read v_kpis'; end if;
    select count(*) into n from v_renewals_due;
    if n = 0 then raise exception 'FAIL: anon sees no renewals'; end if;
    -- one read per relation (a comma list would be a cross join)
    perform 1 from v_fy_landing limit 1;
    perform 1 from v_fy_landing_by_category limit 1;
    perform 1 from v_monthly_trend limit 1;
    perform 1 from v_variance_waterfall limit 1;
    perform 1 from v_seat_utilization limit 1;
    perform 1 from v_vendor_detail limit 1;
    perform 1 from savings limit 1;
    perform 1 from vendors limit 1;
    perform 1 from contract_extractions limit 1;
    begin
        perform 1 from app_admins;
        raise exception 'FAIL: anon can read app_admins';
    exception when insufficient_privilege then null; end;
end $$;
do $$ begin
    begin
        update contracts set status = 'renegotiating' where contract_id = 'C013';
        raise exception 'FAIL: anon could update contracts';
    exception when insufficient_privilege then null; end;
    begin
        insert into contract_extractions (contract_id, file_name, field) values ('C013', 'x.pdf', 'end_date');
        raise exception 'FAIL: anon could insert extractions';
    exception when insufficient_privilege then null; end;
end $$;
reset role;

-- 2. A signed-in user who is not an admin changes nothing, and never touches other columns.
set local role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000002', true);
do $$ declare n int; begin
    update contracts set status = 'renegotiating' where contract_id = 'C013';
    get diagnostics n = row_count;
    if n <> 0 then raise exception 'FAIL: non-admin updated % rows', n; end if;
    begin
        update contracts set unit_price = 1 where contract_id = 'C013';
        raise exception 'FAIL: unit_price is writable';
    exception when insufficient_privilege then null; end;
end $$;
reset role;

-- 3. The admin can change the status and add an extraction.
set local role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000001', true);
do $$ declare n int; begin
    update contracts set status = 'renegotiating' where contract_id = 'C013';
    get diagnostics n = row_count;
    if n <> 1 then raise exception 'FAIL: admin could not update status'; end if;
    insert into contract_extractions (contract_id, file_name, field, extracted_value)
    values ('C013', 'C013_dealstream.pdf', 'end_date', '2027-02-10');
end $$;
reset role;
rollback;
\echo 'Policy check: anon reads every view, cannot write; non-admin blocked; admin can update status and add extractions'
