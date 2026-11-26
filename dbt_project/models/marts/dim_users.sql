with users as (
    select * from {{ ref('stg_users') }}
),

net_orders as (
    select user_id, ordered_at, net_revenue
    from {{ ref('fct_orders') }}
    where is_net_order
),

agg as (
    select
        user_id,
        min(ordered_at) as first_net_order_at,
        count(*) as net_order_count,
        sum(net_revenue) as lifetime_net_revenue
    from net_orders
    group by user_id
),

repeaters as (
    select o.user_id, true as repeat_within_30d
    from net_orders o
    join agg a on o.user_id = a.user_id
    where o.ordered_at > a.first_net_order_at
      and o.ordered_at <= timestamp_add(a.first_net_order_at, interval 30 day)
    group by o.user_id
)

select
    u.user_id,
    u.age,
    u.gender,
    u.country,
    u.state,
    u.city,
    u.acquisition_channel,
    u.signed_up_at,
    a.first_net_order_at,
    date(a.first_net_order_at) as first_net_order_date,
    a.first_net_order_at is not null as is_customer,
    coalesce(a.net_order_count, 0) as net_order_count,
    coalesce(a.lifetime_net_revenue, 0) as lifetime_net_revenue,
    coalesce(r.repeat_within_30d, false) as repeat_within_30d
from users u
left join agg a on u.user_id = a.user_id
left join repeaters r on u.user_id = r.user_id