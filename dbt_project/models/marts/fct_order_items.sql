with items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select order_id, ordered_at from {{ ref('stg_orders') }}
),

products as (
    select product_id, cost from {{ ref('stg_products') }}
),

users as (
    select user_id, acquisition_channel from {{ ref('stg_users') }}
)

select
    i.order_item_id,
    i.order_id,
    i.user_id,
    i.product_id,
    o.ordered_at,
    date(o.ordered_at) as ordered_date,
    i.item_status,
    i.item_status not in ('Cancelled', 'Returned') as is_net_sale,
    u.acquisition_channel,
    i.sale_price as gross_revenue,
    if(i.item_status not in ('Cancelled', 'Returned'), i.sale_price, 0) as net_revenue,
    p.cost as product_cost,
    if(i.item_status not in ('Cancelled', 'Returned'), i.sale_price - p.cost, 0) as gross_profit
from items i
left join orders o on i.order_id = o.order_id
left join products p on i.product_id = p.product_id
left join users u on i.user_id = u.user_id