select
    id as user_id,
    age,
    gender,
    country,
    state,
    city,
    postal_code,
    traffic_source as acquisition_channel,
    created_at as signed_up_at
from {{ source('raw', 'users') }}