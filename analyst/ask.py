"""Question in -> LLM SQL -> guard -> BigQuery (read-only) -> answer."""
import os
import re
import sys
import time

from dotenv import load_dotenv
from google.cloud import bigquery

from analyst.context import allowed_tables, build_context
from analyst.llm import generate
from guardrails.sql_guard import GuardError, validate_sql

load_dotenv()
PROJECT = os.environ["GCP_PROJECT_ID"]
MAX_BYTES = int(os.environ.get("MAX_BYTES_BILLED", "100000000"))


def extract_sql(text):
    t = text.strip()
    m = re.search(r"```(?:sql)?\s*(.*?)```", t, re.S | re.I)
    if m:
        t = m.group(1).strip()
    return t.rstrip(";").strip()


def answer(question, as_of=None):
    t0 = time.time()
    out = {"question": question, "status": None, "sql": None, "rows": [],
           "bytes_billed": 0, "model": None, "message": ""}
    text, model = generate(build_context(as_of), f"Question: {question}\nSQL:")
    out["model"] = model
    if text.strip().upper().startswith("CANNOT_ANSWER"):
        out.update(status="refused", message=text.strip().split(":", 1)[-1].strip())
    else:
        sql = extract_sql(text)
        try:
            safe = validate_sql(sql, allowed_tables(), project=PROJECT)
        except GuardError as e:
            out.update(status="blocked", sql=sql, message=str(e))
        else:
            out["sql"] = safe
            try:
                client = bigquery.Client(project=PROJECT)  # read-only key from .env
                cfg = bigquery.QueryJobConfig(
                    default_dataset=f"{PROJECT}.marts", maximum_bytes_billed=MAX_BYTES)
                job = client.query(safe, job_config=cfg)
                rows = [dict(r) for r in job.result()]
                out.update(status="ok", rows=rows, bytes_billed=job.total_bytes_billed or 0)
            except Exception as e:
                out.update(status="error", message=str(e)[:300])
    out["seconds"] = round(time.time() - t0, 2)
    return out


def show(res):
    print(f"\nQ: {res['question']}")
    print(f"status: {res['status']}  model: {res['model']}  {res['seconds']}s  "
          f"billed: {res['bytes_billed'] / 1e6:.1f} MB")
    if res["message"]:
        print(f"note: {res['message']}")
    if res["sql"]:
        print(f"\nSQL:\n{res['sql']}")
    rows = res["rows"]
    if rows:
        cols = list(rows[0].keys())
        print("\n" + " | ".join(cols))
        for r in rows[:20]:
            print(" | ".join(str(r[c]) for c in cols))
        if len(rows) > 20:
            print(f"... {len(rows)} rows total")


if __name__ == "__main__":
    show(answer(" ".join(sys.argv[1:])))