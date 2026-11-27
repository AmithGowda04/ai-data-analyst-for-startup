import pytest

from guardrails.sql_guard import GuardError, validate_sql

ALLOWED = {"metrics_daily", "fct_orders", "fct_order_items", "fct_sessions",
           "fct_ad_spend_daily", "dim_users", "dim_products"}
PROJECT = "ai-data-analyst-for-startups"


def check(sql, **kw):
    return validate_sql(sql, ALLOWED, project=PROJECT, **kw)


@pytest.mark.parametrize("sql", [
    "INSERT INTO fct_orders (order_id) VALUES (1)",
    "UPDATE fct_orders SET net_revenue = 0 WHERE TRUE",
    "DELETE FROM fct_orders WHERE TRUE",
    "DROP TABLE fct_orders",
    "CREATE TABLE x AS SELECT 1",
    "TRUNCATE TABLE fct_orders",
    "MERGE fct_orders t USING dim_users u ON t.user_id = u.user_id WHEN MATCHED THEN DELETE",
    "SELECT 1; DROP TABLE fct_orders",
    "SELECT 1; SELECT 2",
    "",
    "   ",
    "not sql at all",
])
def test_rejects_non_select_and_multiple_statements(sql):
    with pytest.raises(GuardError):
        check(sql)


@pytest.mark.parametrize("sql", [
    "SELECT * FROM raw.orders",
    "SELECT * FROM staging.stg_orders",
    "SELECT * FROM orders",
    "SELECT * FROM `ai-data-analyst-for-startups.raw.orders`",
    "SELECT * FROM `other-project.marts.fct_orders`",
    "SELECT * FROM `bigquery-public-data.thelook_ecommerce.orders`",
    "SELECT * FROM marts.INFORMATION_SCHEMA.TABLES",
    "SELECT * FROM metrics_daily WHERE user_id IN (SELECT id FROM raw.users)",
    "WITH x AS (SELECT * FROM raw.users) SELECT * FROM x",
    "SELECT * FROM metrics_daily UNION ALL SELECT * FROM raw.orders",
    "SELECT * FROM EXTERNAL_QUERY('conn', 'select 1')",
])
def test_rejects_tables_outside_the_allow_list(sql):
    with pytest.raises(GuardError):
        check(sql)


@pytest.mark.parametrize("sql", [
    "SELECT * FROM metrics_daily",
    "SELECT * FROM marts.metrics_daily",
    "WITH t AS (SELECT channel, net_revenue FROM metrics_daily) "
    "SELECT channel, SUM(net_revenue) FROM t GROUP BY channel",
    "SELECT o.order_id FROM fct_orders o JOIN dim_users u ON o.user_id = u.user_id",
    "SELECT channel FROM metrics_daily UNION ALL SELECT acquisition_channel FROM fct_orders",
])
def test_allows_read_only_queries_on_marts(sql):
    out = check(sql)
    assert out.upper().startswith(("SELECT", "WITH"))


def test_adds_limit_when_missing():
    out = check("SELECT channel, SUM(net_revenue) FROM metrics_daily GROUP BY channel")
    assert out.upper().endswith("LIMIT 1000")


def test_keeps_a_smaller_limit():
    assert check("SELECT * FROM metrics_daily LIMIT 10").upper().endswith("LIMIT 10")


def test_caps_a_larger_limit():
    out = check("SELECT * FROM metrics_daily LIMIT 999999")
    assert out.upper().endswith("LIMIT 1000") and "999999" not in out


def test_custom_cap():
    assert check("SELECT * FROM metrics_daily", max_limit=50).upper().endswith("LIMIT 50")


def test_union_gets_a_limit():
    out = check("SELECT channel FROM metrics_daily UNION ALL SELECT acquisition_channel FROM fct_orders")
    assert out.upper().endswith("LIMIT 1000")