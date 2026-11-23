# Data notes: thelook_ecommerce (public, synthetic)

Source: `bigquery-public-data.thelook_ecommerce`. Row counts as of 2026-11-23.

| Table | Rows | Grain | Key |
|---|---|---|---|
| orders | 125,042 | one row per order | order_id |
| order_items | 181,719 | one row per item in an order | id |
| users | 100,000 | one row per customer | id |
| products | 29,120 | one row per product | id |
| events | 2,431,475 | one row per web event | id |

## Joins
- order_items.order_id -> orders.order_id
- orders.user_id -> users.id
- order_items.product_id -> products.id
- events.user_id -> users.id (nullable: anonymous sessions)

## Money
- Revenue lives in order_items.sale_price (orders has no amount column).
- Cost lives in products.cost (margin = sale_price - cost).

## Timestamps
- orders.created_at ranges 2019-01-06 to present (data keeps growing).
- order_items has its own status and created_at; orders has an order-level status.

## PII / not for the LLM
users.first_name, last_name, email, street_address, latitude, longitude, ip_address, user_geom.
Exclude these from marts. The LLM only sees mart tables.

## Open questions (answer with queries)
- Distinct values of orders.status, order_items.status, events.event_type, users.traffic_source
- Does orders.num_of_item equal the count of order_items per order?
- Do cancelled orders still have order_items rows?