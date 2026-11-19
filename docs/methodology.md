# Methodology

How each number in the cockpit is produced, and why. All thresholds quoted here are the defaults in
[config.yaml](../config.yaml); change them there and every module follows. All data is synthetic.

## 1. Scenario and terms

- **Anchor date** is "today" in the scenario: 30 Nov 2026. November is the last closed month.
- **Fiscal year** is the calendar year 2026.
- **Billed quantity** is what the invoice charges for: seats (contracted, or active if higher), usage
  units, or 1 for a fixed fee.
- **Utilization** of a licence contract is average active seats ÷ contracted seats over the last 3 months.
- **Decision deadline** = contract end date − notice period. After that date, an auto-renewing contract
  rolls over for another year on its current terms, and the leverage is gone.

## 2. Forecast

The forecast follows how each kind of invoice is actually built, so a budget owner can check it against
their own bill.

| Billing model | Rule | Why |
| --- | --- | --- |
| Per seat | Seats = projected department headcount × adoption rate observed over the last 3 months. The vendor bills the contracted seats or the needed seats, whichever is higher. | Licence spend moves with hiring. Below the contracted number you still pay for the seats. Above it, the vendor bills a true-up. |
| Usage | Linear trend over the last 6 months of seasonally adjusted volume, times a seasonal index for each calendar month. | Cloud bills grow with the business. Marketing spend peaks around campaigns and Black Friday. |
| Fixed | Annual contract value ÷ 12. | Retainers and fixed-fee services do not move month to month. |

- **Headcount projection:** linear trend over the last 6 months for each department. Tools owned by IT are
  company-wide, so they are sized against total headcount.
- **Price:** the current contract price until the end of the term, then raised by the contract's escalator
  from the next month.
- **Status-quo assumption:** every live contract is assumed to renew on its current terms. That makes the
  forecast the cost of doing nothing. The savings from recommendations are shown separately, as upside
  against it. Terminated contracts are forecast at zero.
- **Never negative:** forecast volumes are floored at zero (tested).

**FY landing** = actual spend from January to the last closed month + forecast for the remaining months
of the year, compared with the full-year budget, by vendor and by category.

## 3. Variance: price, volume, unbudgeted

For each vendor and month:

```
total variance = actual − budget
               = (actual unit price − budget unit price) × actual quantity    price
               + (actual quantity − budget quantity) × budget unit price      volume
               + spend on a vendor with no budget line                        unbudgeted
```

Each part answers a different question and has a different owner:

- **Price:** did we pay more or less per unit than planned? Procurement owns it. Escalators above the IPCA
  assumed in the budget push it up. Renegotiated price cuts pull it down.
- **Volume:** did we buy more units than planned? The budget holder owns it. Cloud growth beyond plan,
  extra seats and true-ups show up here. A contract that was terminated but stayed in the budget shows a
  negative volume equal to its budget.
- **Unbudgeted:** spend on a vendor that has no budget line at all. Usually it is a new tool adopted
  mid-year, and it is a governance question before it is a cost question.

Two versions are produced: **year to date** (closed months against the budget for the same months) and
**full-year landing** (actuals plus forecast against the full-year budget). The landing version drives
the budget-to-landing waterfall.

**To the cent.** Amounts are held in whole centavos. Volume is rounded to the cent, and price is what is
left of the total, so price + volume + unbudgeted always equals the total exactly. The price figure then
differs from the formula above by less than one cent per vendor-month. Both properties are tested.

**How the budget was built** (in the synthetic data): before each fiscal year, at the price in force at
the time, with IPCA added from the month a renewal was due. Cloud was planned at 2% monthly growth.

## 4. Recommendation rules

Applied to every live contract that ends within the next **120 days**, in this order. The first rule that
matches wins, so each contract gets one recommendation.

| # | Rule | When | Recommendation | Estimated annual impact |
| --- | --- | --- | --- | --- |
| 1 | Terminate | Criticality is low **and** utilization is below 20% | Let the contract expire | Annual value − termination fee |
| 2 | Consolidate | Another live vendor covers the same capability, and this one is not the one to keep | Move users to the kept tool and drop this contract | Annual value of the dropped contract |
| 3 | Right-size | Utilization is below 60% | Renew at peak active seats over the last 6 months + 10%, rounded up | Seats cut × unit price × 12 |
| 4 | Renegotiate | Unit price is above the public list price, **or** the escalator is above IPCA | Negotiate down to list price or to IPCA | The larger of the two gaps |
| 5 | Renew | None of the above | Renew as is | Zero |

**Why this order?**

- **Terminate comes first.** If nobody uses a non-critical tool, negotiating its price or seat count
  is wasted effort.
- **Consolidate comes before right-size.** If a tool is going away, its seat count no longer matters.
- **Right-size comes before renegotiate.** Agree how many seats you need first, then negotiate the price
  on the smaller base.
- **Renew is an explicit outcome.** "Looked at it, nothing to do" is a decision too, and it is recorded
  with its deadline.

**Choices behind the rules**

- **Overlap** means two or more live vendors share the same capability, for example three
  video-conferencing tools. The tool to keep is the one with the highest utilization. A tie goes to the
  lowest price per seat. The kept tool itself goes through rules 3 to 5.
- **Consolidation impact ignores switching costs:** migration work, extra seats at the kept vendor, and
  overlap months. Treat it as a gross figure that needs a business case.
- **Right-size uses the peak, not the average,** plus a 10% buffer. Cutting to the average would force a
  true-up in the next busy month.
- **Renegotiate takes the larger gap, not the sum.** Getting to list price and capping the escalator at
  IPCA overlap, and adding them would double count.
- **Escalator gap** = annual value × (escalator − IPCA). It is the extra cost the renewal would lock in
  above inflation.
- **Benchmark gap** = (unit price − public list price) × seats × 12. List prices are a ceiling for
  enterprise buyers, so a price above list is a strong signal.
- **Urgent** means the decision deadline is less than 30 days away. Auto-renewing contracts deserve the
  most attention, because doing nothing commits the company for another year.

## 5. Savings vs. cost avoidance

- **Saving:** the new price is below the price paid before. It shows up in the P&L.
- **Cost avoidance:** the negotiated price is below the first quote for something with no price history.
  It is real value, but it does not reduce spend against last year, so it is reported separately.

## 6. What the tests prove

- The same seed generates the same data and byte-identical CSVs.
- Price + volume + unbudgeted = total variance, to the cent, per row and in aggregate.
- The forecast is never negative.
- Every decision deadline falls before its end date.
- Each planted pattern is found by its rule, and no unplanted finding appears in the renewal window.
- The priority order holds: an overlapping tool that is also under-used is consolidated, not right-sized.
- Thresholds come from the config: tightening one changes the outcome.
- No real vendor name appears anywhere except the benchmarks table.
