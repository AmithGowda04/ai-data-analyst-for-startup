select
    date as spend_date,
    channel,
    spend,
    impressions,
    clicks,
    conversions as reported_conversions
from {{ source('raw', 'ad_spend') }}