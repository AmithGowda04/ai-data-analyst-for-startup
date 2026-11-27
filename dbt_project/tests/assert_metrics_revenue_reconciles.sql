select abs(m.total - f.total) as diff
from (select sum(net_revenue) as total from {{ ref('metrics_daily') }}) m,
     (select sum(net_revenue) as total from {{ ref('fct_order_items') }}) f
where abs(m.total - f.total) > 0.01