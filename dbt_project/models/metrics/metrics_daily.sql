with bounds as (
    select
        least(
            (select min(ordered_date) from {{ ref('fct_orders') }}),
            (select min(session_date) from {{ ref('fct_sessions') }}),
            (select min(spend_date) from {{ ref('fct_ad_spend_daily') }})
        ) as first_date,
        greatest(
            (select max(ordered_date) from {{ ref('fct_orders') }}),
            (select max(session_date) from {{ ref('fct_sessions') }}),
            (select max(spend_date) from {{ ref('fct_ad_spend_daily') }})
        ) as last_date
),

spine as (
    select d as metric_date, c as channel, b.last_date
    from bounds b,
        unnest(generate_date_array(b.first_date, b.last_date)) as d,
        unnest(['Search', 'Organic', 'Facebook', 'Email', 'Display']) as c
),

orders as (
    select
        ordered_date as metric_date,
        acquisition_channel as channel,
        countif(is_net_order) as net_orders,
        sum(gross_revenue) as gross_revenue,
        sum(net_revenue) as net_revenue,
        sum(gross_profit) as gross_profit
    from {{ ref('fct_orders') }}
    group by 1, 2
),

spend as (
    select
        spend_date as metric_date,
        channel,
        sum(spend) as ad_spend,
        sum(clicks) as clicks
    from {{ ref('fct_ad_spend_daily') }}
    group by 1, 2
),

customers as (
    select
        first_net_order_date as metric_date,
        acquisition_channel as channel,
        count(*) as new_customers,
        countif(repeat_within_30d) as repeat_customers_30d
    from {{ ref('dim_users') }}
    where is_customer
    group by 1, 2
),

sessions as (
    select
        session_date as metric_date,
        traffic_source as channel,
        count(*) as sessions,
        countif(purchased) as converted_sessions
    from {{ ref('fct_sessions') }}
    group by 1, 2
)

select
    concat(cast(s.metric_date as string), '|', s.channel) as metric_key,
    s.metric_date,
    s.channel,
    coalesce(o.net_orders, 0) as net_orders,
    coalesce(o.gross_revenue, 0) as gross_revenue,
    coalesce(o.net_revenue, 0) as net_revenue,
    coalesce(o.gross_profit, 0) as gross_profit,
    if(s.channel = 'Organic', null, coalesce(p.ad_spend, 0)) as ad_spend,
    if(s.channel = 'Organic', null, coalesce(p.clicks, 0)) as clicks,
    coalesce(c.new_customers, 0) as new_customers,
    coalesce(c.repeat_customers_30d, 0) as repeat_customers_30d,
    coalesce(x.sessions, 0) as sessions,
    coalesce(x.converted_sessions, 0) as converted_sessions,
    s.metric_date <= date_sub(s.last_date, interval 30 day) as retention_eligible
from spine s
left join orders o using (metric_date, channel)
left join spend p using (metric_date, channel)
left join customers c using (metric_date, channel)
left join sessions x using (metric_date, channel)