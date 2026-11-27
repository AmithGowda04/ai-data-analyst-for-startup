select
    session_id,
    min(user_id) as user_id,
    min(event_at) as session_start_at,
    date(min(event_at)) as session_date,
    case max(traffic_source)
        when 'Adwords' then 'Search'
        when 'YouTube' then 'Display'
        else max(traffic_source)
    end as traffic_source,
    count(*) as event_count,
    countif(event_type = 'product') > 0 as viewed_product,
    countif(event_type = 'cart') > 0 as added_to_cart,
    countif(event_type = 'purchase') > 0 as purchased
from {{ ref('stg_events') }}
where session_id is not null
group by session_id