-- CI ONLY - never run on Supabase. Recreates just enough of Supabase (roles, default grants and
-- auth.uid()) for sql/supabase_policies.sql to be applied and tested on plain Postgres.
-- Grants copy what a NEW Supabase project gives tables created with psql: no SELECT, INSERT, UPDATE
-- or DELETE for the API roles, and functions not executable by them. The policies file must grant
-- everything the app needs; nothing works by accident.
do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
    if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
    if not exists (select 1 from pg_roles where rolname = 'service_role') then create role service_role nologin; end if;
end $$;
create schema if not exists auth;
create or replace function auth.uid() returns uuid language sql stable
as $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
grant usage on schema auth to anon, authenticated;
grant usage on schema public to anon, authenticated, service_role;
grant truncate, references, trigger, maintain on all tables in schema public to anon, authenticated, service_role;
alter default privileges in schema public revoke execute on functions from public;
