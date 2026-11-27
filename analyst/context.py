"""Build the LLM prompt context from dbt's manifest.json and catalog.json."""
import datetime
import json
from pathlib import Path

TARGET = Path("dbt_project/target")
MARTS_SCHEMA = "marts"
DATA_START = datetime.date(2024, 1, 1)

RULES = """You are a data analyst assistant for a small e-commerce startup. You answer business
questions by writing ONE BigQuery Standard SQL SELECT statement over the tables below.

Rules:
- Output only the SQL. No markdown fences, no explanation.
- Use only the tables listed below, unqualified or as marts.<table>.
- For KPIs (revenue, orders, AOV, ad spend, ROAS, CAC, conversion rate, retention) use
  metrics_daily and the metric definitions exactly as written. Never average per-row ratios.
- "Revenue" means net revenue and "orders" means net orders unless gross is asked for.
- Date columns: metric_date (metrics_daily), ordered_date (orders and items), session_date
  (sessions), spend_date (ad spend), first_net_order_date (users).
- Data covers {start} to {end}. Today is {as_of}. Resolve relative dates ("last month",
  "last 7 days") from today and use explicit date literals.
- If the question cannot be answered with these tables (forecasts, personal data such as names or
  emails, anything unrelated to this business, or a metric that is not defined), reply with exactly
  one line: CANNOT_ANSWER: <short reason>. Do not guess.
- Return at most 1000 rows."""

EXAMPLES = [
    ("What was revenue by channel in 2025?",
     "SELECT channel, ROUND(SUM(net_revenue), 2) AS revenue\n"
     "FROM metrics_daily\n"
     "WHERE metric_date BETWEEN '2025-01-01' AND '2025-12-31'\n"
     "GROUP BY channel\nORDER BY revenue DESC"),
    ("What was ROAS by paid channel in Q3 2025?",
     "SELECT channel, ROUND(SAFE_DIVIDE(SUM(net_revenue), SUM(ad_spend)), 2) AS roas\n"
     "FROM metrics_daily\n"
     "WHERE channel != 'Organic' AND metric_date BETWEEN '2025-07-01' AND '2025-09-30'\n"
     "GROUP BY channel\nORDER BY roas DESC"),
    ("Show monthly orders and AOV for 2025.",
     "SELECT DATE_TRUNC(metric_date, MONTH) AS month, SUM(net_orders) AS orders,\n"
     "  ROUND(SAFE_DIVIDE(SUM(net_revenue), SUM(net_orders)), 2) AS aov\n"
     "FROM metrics_daily\n"
     "WHERE metric_date BETWEEN '2025-01-01' AND '2025-12-31'\n"
     "GROUP BY month\nORDER BY month"),
    ("Top 5 products by revenue in 2025?",
     "SELECT p.product_name, ROUND(SUM(i.net_revenue), 2) AS revenue\n"
     "FROM fct_order_items i JOIN dim_products p ON i.product_id = p.product_id\n"
     "WHERE i.ordered_date BETWEEN '2025-01-01' AND '2025-12-31'\n"
     "GROUP BY p.product_name\nORDER BY revenue DESC\nLIMIT 5"),
    ("What will revenue be next year?",
     "CANNOT_ANSWER: forecasting is not supported, only historical metrics."),
    ("List our customers' email addresses.",
     "CANNOT_ANSWER: personal data such as emails is not available."),
]


def load_marts():
    manifest = json.loads((TARGET / "manifest.json").read_text())
    catalog = json.loads((TARGET / "catalog.json").read_text())
    models = []
    for node in manifest["nodes"].values():
        if node.get("resource_type") != "model" or node.get("schema") != MARTS_SCHEMA:
            continue
        cat_cols = catalog["nodes"].get(node["unique_id"], {}).get("columns", {})
        types = {n.lower(): c.get("type", "") for n, c in cat_cols.items()}
        cols = [
            {"name": n, "type": types.get(n.lower(), ""), "description": c.get("description", "")}
            for n, c in node.get("columns", {}).items()
        ]
        meta = (node.get("config") or {}).get("meta") or node.get("meta") or {}
        models.append({
            "name": node["name"],
            "description": node.get("description", ""),
            "columns": cols,
            "metrics": meta.get("metrics", {}),
        })
    return sorted(models, key=lambda m: m["name"])


def allowed_tables():
    return {m["name"] for m in load_marts()}


def build_context(as_of=None):
    as_of = as_of or datetime.datetime.now(datetime.timezone.utc).date()
    end = as_of - datetime.timedelta(days=1)
    models = load_marts()
    parts = [RULES.format(start=DATA_START, end=end, as_of=as_of), "\n## Tables (dataset: marts)"]
    for m in models:
        parts.append(f"\n### {m['name']}\n{m['description']}")
        for c in m["columns"]:
            parts.append(f"- {c['name']} ({c['type']}): {c['description']}")
    metrics = {}
    for m in models:
        metrics.update(m["metrics"])
    if metrics:
        parts.append("\n## Metric definitions (use exactly)")
        for name, definition in metrics.items():
            parts.append(f"- {name}: {definition}")
    parts.append("\n## Examples")
    for q, sql in EXAMPLES:
        parts.append(f"\nQuestion: {q}\nSQL:\n{sql}")
    return "\n".join(parts)


if __name__ == "__main__":
    print(build_context())