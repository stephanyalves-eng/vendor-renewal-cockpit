# Prompt 7: Contract intake

The three sample PDFs are in `data/contracts/`. After this page is built, sign in as the owner and run
the extraction once on each PDF; visitors then see those stored results.

```
Build the Contract intake page (/intake).

Visitors (not signed in) - no AI calls at all:
- Show stored results from table contract_extractions (columns: contract_id, file_name, field,
  extracted_value, confidence, uncertain, model, extracted_at), grouped by file_name.
- For each file, a form-like card with the five fields: end_date, auto_renew, notice_days,
  price_escalator_pct, termination_fee. Fields with uncertain = true get a "Check" icon plus the word
  "Unsure", never colour alone. Show model and extracted_at.
- Next to each extracted value, show the value stored in table contracts for the same contract_id,
  with "Match" or "Differs" (icon + word).
- A note: "Live extraction is limited to the owner to keep this demo free to run."

Signed-in owner:
- Upload a PDF. An edge function sends it to Lovable AI and asks for the five fields, each with a
  confidence between 0 and 1. Fields below 0.8 confidence are marked uncertain.
- The owner reviews and edits every field in a form before saving. Save inserts one row per field
  into contract_extractions (contract_id chosen from a select of contracts).
- SECURITY: the edge function must verify the caller's JWT and check server-side that the user id is
  in table app_admins; otherwise return 403 and do not call the AI. Do not rely on the UI hiding the
  button.
```
