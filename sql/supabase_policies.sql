-- Supabase only: who may write. Run after sql/schema.sql and sql/load.sql.
-- Visitors (role anon) can only read. Signed-in users can write only if their user id is in
-- app_admins, and then only the contract status and new contract extractions.
--
-- After creating your own login in Supabase Auth, add yourself by hand in the SQL editor:
--   insert into app_admins (user_id) values ('<your auth user id>');
-- Never commit that id. Consider turning off public sign-ups in Supabase Auth settings.

create policy "admins read own row" on app_admins
    for select to authenticated using (user_id = auth.uid());

create or replace function is_app_admin() returns boolean
    language sql stable security invoker set search_path = public
as $$
    select exists (select 1 from app_admins where user_id = auth.uid())
$$;

-- No writes for anyone by default (Supabase grants them to anon and authenticated otherwise).
revoke insert, update, delete, truncate on all tables in schema public from anon, authenticated;

-- Contract status: column-level grant, row-level check.
grant update (status) on contracts to authenticated;
create policy "admins update status" on contracts
    for update to authenticated using (is_app_admin()) with check (is_app_admin());

-- New AI extractions: admins only.
grant insert on contract_extractions to authenticated;
create policy "admins add extractions" on contract_extractions
    for insert to authenticated with check (is_app_admin());
