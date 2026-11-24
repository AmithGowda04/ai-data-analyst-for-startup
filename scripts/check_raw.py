import sys
sys.path.insert(0, "ingest")
from load_raw import PROJECT, get_client

c = get_client()
sql = f"""
SELECT channel, ROUND(SUM(spend)) AS spend, SUM(conversions) AS conversions
FROM `{PROJECT}.raw.ad_spend` GROUP BY 1 ORDER BY 1
"""
for r in c.query(sql).result():
    print(dict(r))