select
    id as order_item_id,
    order_id,
    user_id,
    product_id,
    status as item_status,
    created_at as ordered_at,
    shipped_at,
    delivered_at,
    returned_at,
    sale_price
from {{ source('raw', 'order_items') }}