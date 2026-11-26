with spend as (
    select * from {{ ref('stg_ad_spend') }}
),

orders as (
    select
        ordered_date as spend_date,
        acquisition_channel as channel,
        countif(is_net_order) as net_orders,
        sum(net_revenue) as net_revenue
    from {{ ref('fct_orders') }}
    group by 1, 2
),

new_customers as (
    select
        first_net_order_date as spend_date,
        acquisition_channel as channel,
        count(*) as new_customers
    from {{ ref('dim_users') }}
    where is_customer
    group by 1, 2
)

select
    concat(cast(s.spend_date as string), '|', s.channel) as spend_key,
    s.spend_date,
    s.channel,
    s.spend,
    s.impressions,
    s.clicks,
    coalesce(o.net_orders, 0) as net_orders,
    coalesce(o.net_revenue, 0) as net_revenue,
    coalesce(n.new_customers, 0) as new_customers
from spend s
left join orders o on s.spend_date = o.spend_date and s.channel = o.channel
left join new_customers n on s.spend_date = n.spend_date and s.channel = n.channel