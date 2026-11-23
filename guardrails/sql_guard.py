"""Week 3 task: validate LLM-generated SQL before it touches BigQuery.

Implement validate_sql() so the tests in tests/test_sql_guard.py pass.
Hints: parse with sqlglot (dialect="bigquery"), allow only SELECT, allow only
tables from ALLOWED_TABLES, enforce a LIMIT, and reject multiple statements.
"""

ALLOWED_TABLES = {
    # fill with your mart tables, e.g. "marts.fct_orders", "marts.dim_users"
}
MAX_LIMIT = 1000


def validate_sql(sql: str) -> str:
    """Return safe SQL (with LIMIT enforced) or raise ValueError with the reason."""
    raise NotImplementedError("Implement in Week 3")
