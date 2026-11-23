import pytest
from guardrails.sql_guard import validate_sql

# Write these tests FIRST (Week 3), then implement the guard. Add your own cases.

def test_rejects_delete():
    with pytest.raises(ValueError):
        validate_sql("DELETE FROM marts.fct_orders WHERE 1=1")

def test_rejects_multiple_statements():
    with pytest.raises(ValueError):
        validate_sql("SELECT 1; DROP TABLE marts.fct_orders")

def test_rejects_unknown_table():
    with pytest.raises(ValueError):
        validate_sql("SELECT * FROM raw.secret_table")

def test_adds_limit_when_missing():
    # set ALLOWED_TABLES first, then use a real mart table here
    pass
