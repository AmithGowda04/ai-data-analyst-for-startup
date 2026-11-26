with orders as (
    select * from {{ ref('stg_orders') }}
),

items as (
    select
        order_id,
        count(*) as item_count,
        countif(is_net_sale) as net_item_count,
        sum(gross_revenue) as gross_revenue,
        sum(net_revenue) as net_revenue,
        sum(gross_profit) as gross_profit
    from {{ ref('fct_order_items') }}
    group by order_id
),

users as (
    select user_id, acquisition_channel from {{ ref('stg_users') }}
)

select
    o.order_id,
    o.user_id,
    o.ordered_at,
    date(o.ordered_at) as ordered_date,
    o.order_status,
    u.acquisition_channel,
    coalesce(i.item_count, 0) as item_count,
    coalesce(i.gross_revenue, 0) as gross_revenue,
    coalesce(i.net_revenue, 0) as net_revenue,
    coalesce(i.gross_profit, 0) as gross_profit,
    coalesce(i.net_item_count, 0) > 0 as is_net_order
from orders o
left join items i on o.order_id = i.order_id
left join users u on o.user_id = u.user_id