select
    order_id,
    user_id,
    status as order_status,
    created_at as ordered_at,
    shipped_at,
    delivered_at,
    returned_at,
    num_of_item as item_count
from {{ source('raw', 'orders') }}