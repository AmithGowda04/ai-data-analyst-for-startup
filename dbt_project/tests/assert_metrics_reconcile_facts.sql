with m as (
    select
        sum(sessions) as sessions,
        sum(converted_sessions) as converted,
        sum(ad_spend) as ad_spend,
        sum(new_customers) as new_customers
    from {{ ref('metrics_daily') }}
),

f as (
    select
        (select count(*) from {{ ref('fct_sessions') }}) as sessions,
        (select countif(purchased) from {{ ref('fct_sessions') }}) as converted,
        (select sum(spend) from {{ ref('fct_ad_spend_daily') }}) as ad_spend,
        (select countif(is_customer) from {{ ref('dim_users') }}) as new_customers
)

select
    m.sessions as metric_sessions, f.sessions as fact_sessions,
    m.converted as metric_converted, f.converted as fact_converted,
    m.ad_spend as metric_spend, f.ad_spend as fact_spend,
    m.new_customers as metric_new_customers, f.new_customers as fact_new_customers
from m, f
where m.sessions != f.sessions
   or m.converted != f.converted
   or abs(m.ad_spend - f.ad_spend) > 0.01
   or m.new_customers != f.new_customers