import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
client = bigquery.Client(project=os.environ["GCP_PROJECT_ID"])
DS = "bigquery-public-data.thelook_ecommerce"

queries = {
    "orders.status": f"SELECT status, COUNT(*) n FROM `{DS}.orders` GROUP BY 1 ORDER BY 2 DESC",
    "order_items.status": f"SELECT status, COUNT(*) n FROM `{DS}.order_items` GROUP BY 1 ORDER BY 2 DESC",
    "users.traffic_source": f"SELECT traffic_source, COUNT(*) n FROM `{DS}.users` GROUP BY 1 ORDER BY 2 DESC",
    "events.event_type": f"SELECT event_type, COUNT(*) n FROM `{DS}.events` GROUP BY 1 ORDER BY 2 DESC",
    "orders per year": f"SELECT EXTRACT(YEAR FROM created_at) yr, COUNT(*) n FROM `{DS}.orders` GROUP BY 1 ORDER BY 1",
}
for name, sql in queries.items():
    print(f"\n== {name}")
    for r in client.query(sql).result():
        print("  ", dict(r))