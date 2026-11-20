# Prompt 7: live contract extraction (owner only)

The visitor part of /intake (sample PDFs, stored extractions, Match/Differs check) was built directly in
the front-end repository. This prompt adds only the owner's live extraction.

**As built:** Lovable does not allow new Supabase Edge Functions in this TanStack Start project, so the
same logic runs as a server route, `/api/extract-contract`, in the front-end repository. It checks the
session (401) and the `app_admins` row under row level security (403) before any AI call, and never
writes to the database; saving uses the owner's session. Cost: 6.1 credits.

```
Add owner-only live AI extraction to the existing Contract intake page (/intake).

KEEP (do not change)
- The existing visitor view in src/routes/intake.tsx and the helpers in src/lib/intake-logic.ts,
  src/lib/intake.functions.ts and src/lib/intake.types.ts: sample contracts, stored extractions grouped
  by file, the "Unsure" flag and the Match/Differs check. Visitors must never trigger an AI call.
- Database schema: table contract_extractions and table app_admins already exist with row level
  security. Do not create, alter or drop tables, views, policies or functions; no migrations.
- All other pages, the public read client and the design system.

BUILD
1. A Supabase Edge Function "extract-contract" on the connected external Supabase project:
   - Requires the caller's JWT. Verify it server-side (supabase.auth.getUser with the caller's token),
     then check that the user id is in table app_admins by querying it with a client that uses the
     caller's token (row level security lets admins read their own row). If there is no JWT, or the user
     is not an admin, return 401/403 immediately and do NOT call the AI.
   - Accepts one PDF (max 5 MB, application/pdf only) and sends it to Lovable AI. Ask the model for exactly
     five fields as JSON: end_date (YYYY-MM-DD), auto_renew (true/false), notice_days (integer),
     price_escalator_pct (number), termination_fee (number, BRL), each with a confidence between 0 and 1.
   - Returns the five values with their confidence and the model name. It does not write to the database.
   - Keep the AI key server-side only.
2. On /intake, for a signed-in admin only, an "Extract a contract" card above the stored extractions:
   - Choose the contract (select of contract_id + vendor name from table contracts) and upload a PDF.
   - Call the edge function with the user's session; show progress and clear errors (not signed in, not
     an admin, wrong file type, file too large, AI failure).
   - Show the five fields in an editable review form. Fields with confidence below 0.8 show a warning
     icon and the word "Unsure". The owner can edit every value before saving.
   - "Save extraction" inserts one row per field into contract_extractions with the user's session:
     contract_id, file_name, field, extracted_value (as text), confidence, uncertain (confidence < 0.8),
     model. After saving, refresh the stored extractions so the new card appears below.
   - Signed-in users who are not admins, and visitors, keep seeing the current note instead of the card.

ACCEPTANCE
- Calling the edge function without a session, or as a non-admin, returns 401/403 and no AI request is
  made (verify with the function logs).
- As the owner, extracting C013_dealstream.pdf returns the five fields; after saving, the stored card
  shows them with Match/Differs against the contracts table.
- Visitors see no upload card and the page makes no AI or edge-function calls for them.
- Checked at 1280px and 375px.
```
