"""SQL guard: one read-only SELECT over allow-listed marts tables, with an enforced LIMIT."""
import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

DATASET = "marts"
BLOCKED_NODES = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
                 exp.Alter, exp.Merge, exp.Command)


class GuardError(ValueError):
    """Raised when a query is not allowed to run."""


def validate_sql(sql, allowed_tables, project=None, max_limit=1000):
    """Return the validated SQL with an enforced LIMIT, or raise GuardError."""
    if not sql or not sql.strip():
        raise GuardError("empty query")
    try:
        statements = [s for s in sqlglot.parse(sql, read="bigquery") if s is not None]
    except SqlglotError as e:
        raise GuardError(f"cannot parse SQL: {e}") from e
    if len(statements) != 1:
        raise GuardError("exactly one statement is allowed")

    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union)):
        raise GuardError("only SELECT queries are allowed")
    if tree.find(*BLOCKED_NODES):
        raise GuardError("data-changing statements are not allowed")

    allowed = {t.lower() for t in allowed_tables}
    ctes = {c.alias.lower() for c in tree.find_all(exp.CTE)}
    for t in tree.find_all(exp.Table):
        if not isinstance(t.this, exp.Identifier):
            raise GuardError("table functions are not allowed")
        name, db, catalog = t.name.lower(), t.db.lower(), t.catalog.lower()
        if not db and not catalog and name in ctes:
            continue
        if catalog and catalog != (project or "").lower():
            raise GuardError(f"project not allowed: {catalog}")
        if db and db != DATASET:
            raise GuardError(f"dataset not allowed: {db}")
        if name not in allowed:
            raise GuardError(f"table not allowed: {name}")

    limit = tree.args.get("limit")
    n = None
    if limit is not None and isinstance(limit.expression, exp.Literal) and limit.expression.is_int:
        n = int(limit.expression.name)
    if n is None or n > max_limit:
        tree.set("limit", exp.Limit(expression=exp.Literal.number(max_limit)))
    return tree.sql(dialect="bigquery")