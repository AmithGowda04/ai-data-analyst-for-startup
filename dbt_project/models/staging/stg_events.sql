select
    id as event_id,
    user_id,
    session_id,
    sequence_number,
    created_at as event_at,
    event_type,
    uri,
    traffic_source,
    browser
from {{ source('raw', 'events') }}