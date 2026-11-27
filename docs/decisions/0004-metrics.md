# 0004: Metrics layer

## Context
- The LLM must never query raw tables. One governed table, `marts.metrics_daily`, holds additive
  components per day and channel; every metric is a ratio of sums over it.
- Data is the synthetic thelook dataset (history loaded from 2024-01-01) plus generated ad spend.

## Decisions
1. Revenue = SUM(net_revenue): items with status Cancelled or Returned are excluded.
   Gross revenue stays available as its own column.
2. Orders = orders with at least one net item.
3. All reporting dates come from the order date. Items are stamped up to several days after their
   order in this dataset, so items inherit their parent order's date.
4. Ratios are ratios of sums, written with SAFE_DIVIDE: an average of per-row ratios gives wrong
   answers, and a plain `/` crashes on a zero denominator (it did).
5. ROAS and CAC exclude Organic, which has no ad spend. A new customer is a user's first net order.
6. Conversion rate = converted sessions / sessions. Sessions are attributed to the session's traffic
   source, while orders and revenue are attributed to the customer's acquisition channel, so
   cross-dividing them within a channel is not meaningful.
7. Retention = new customers who order again within 30 days / new customers, counted only for dates
   whose 30-day window is complete (`retention_eligible`).
8. Event labels are mapped to the five channels: Adwords -> Search, YouTube -> Display.
   This mapping is an assumption (nothing in the data confirms it) and is stated as such.

## Problems found by tests (kept as evidence)
- A `relationships` test failed with 102 order items whose parent order was missing. Cause:
  orders and items were each cut by their own timestamp at the load boundary. Fix: items are loaded
  by parent order, which also recovered 1,750 items (133,451 -> 135,201).
- A division-by-zero in a sanity query revealed that sessions labelled Adwords and YouTube had
  silently dropped out of `metrics_daily` (about 130k of 325.7k sessions). Fix: an explicit label
  mapping, an `accepted_values` test on the mapped column, and a reconciliation test that compares
  `metrics_daily` totals (sessions, converted sessions, ad spend, new customers, revenue) with the
  source facts.

## Consequences
- Every additive column is reconciled against its source fact on each `dbt build`.
- Tables only (no incremental models): the BigQuery sandbox has no DML.
- Conversion rate is about 42% in every channel because the synthetic events do not vary by source.
- Measured: 13 models, 36 data tests, `dbt build` in 49.6 s (Codespace, BigQuery sandbox).