# Prompt 4: Budget vs. actual

```
Build the Budget vs. actual page (/budget).

Filters at the top: category (multi-select) and department (multi-select), both "All" by default.
Both charts below follow the filters by summing the filtered rows.

1. Monthly chart from view v_monthly_trend (columns: month, category, owner_department, actual,
   budget, forecast). Sum per month across the filtered rows.
   - actual: solid Deep Forest line; forecast: dashed line in the same colour, starting where actual
     ends; budget: Muted Sage line. Legend with words, y-axis in BRL, x-axis by month.
   - A vertical marker labelled "Today" at the last month that has actuals.
2. Variance waterfall from view v_variance_waterfall, scope = 'fy_landing'
   (columns: budget, price, volume, unbudgeted, landing). Sum the filtered rows, then draw five steps:
   Budget (total bar), Price, Volume, Unbudgeted (floating steps, up or down), Landing (total bar).
   Label each step with its BRL value; increases with an up-arrow and "Over", decreases with a
   down-arrow and "Under". Highlight only the largest step in Mineral Bronze.
   A toggle switches scope between "Full year (actuals + forecast)" = fy_landing and
   "Year to date" = ytd.
3. Under the waterfall, one plain sentence: "Price: did we pay more per unit? Volume: did we buy
   more? Unbudgeted: spend with no budget line."
```
