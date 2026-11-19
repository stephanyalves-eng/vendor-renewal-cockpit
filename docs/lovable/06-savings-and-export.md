# Prompt 6: Savings tracker and Excel export

```
1. Build the Savings page (/savings) from table savings joined to vendors on vendor_id for the
   vendor name. Columns: date, vendor, type, baseline_price, negotiated_price, annualized_impact,
   note. At the top, one sentence: "A saving is a lower price than we paid before; cost avoidance
   is a lower price than the first quote for something we never bought." Totals by type above the
   table.

2. Add an "Export to Excel" button to every table in the app (Renewals, Vendor list, Savings).
   It exports exactly the rows and columns currently shown, after filters, as .xlsx, using the
   SheetJS (xlsx) package in the browser. File name: <page>-<yyyy-mm-dd>.xlsx. Add a first row
   "Synthetic data" to every sheet.
```
