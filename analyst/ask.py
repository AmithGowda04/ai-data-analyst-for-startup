"""Question in -> LLM SQL -> guard -> dry run -> BigQuery (read-only) -> answer, with logging."""
import os
import re
import sys
import time

from dotenv import load_dotenv
from google.cloud import bigquery

from analyst.context import allowed_tables, build_context
from analyst.llm import generate
from analyst.log import log_query
from guardrails.sql_guard import GuardError, validate_sql

load_dotenv(override=True)
PROJECT = os.environ["GCP_PROJECT_ID"]
DEFAULT_MAX_BYTES = int(os.environ.get("MAX_BYTES_BILLED", "100000000"))


def extract_sql(text):
    t = text.strip()
    m = re.search(r"```(?:sql)?\s*(.*?)```", t, re.S | re.I)
    if m:
        t = m.group(1).strip()
    return t.rstrip(";").strip()


def answer(question, as_of=None, run_id="manual", max_bytes=None, log=True):
    cap = max_bytes or DEFAULT_MAX_BYTES
    t0 = time.time()
    out = {"question": question, "status": None, "sql": None, "rows": [], "bytes_estimated": 0,
           "bytes_billed": 0, "model": None, "message": ""}
    try:
        text, model = generate(build_context(as_of), f"Question: {question}\nSQL:")
        out["model"] = model
    except Exception as e:
        out.update(status="error", message=f"LLM failed: {str(e)[:200]}")
        text = None

    if text is not None:
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
                    client = bigquery.Client(project=PROJECT)  # read-only key
                    base = {"default_dataset": f"{PROJECT}.marts"}
                    dry = client.query(safe, job_config=bigquery.QueryJobConfig(dry_run=True, **base))
                    out["bytes_estimated"] = dry.total_bytes_processed or 0
                    if out["bytes_estimated"] > cap:
                        out.update(status="too_expensive",
                                   message=f"estimated {out['bytes_estimated'] / 1e6:.1f} MB "
                                           f"exceeds the {cap / 1e6:.0f} MB cap")
                    else:
                        cfg = bigquery.QueryJobConfig(
                            maximum_bytes_billed=cap, use_query_cache=False, **base)
                        job = client.query(safe, job_config=cfg)
                        out["rows"] = [dict(r) for r in job.result()]
                        out.update(status="ok", bytes_billed=job.total_bytes_billed or 0)
                except Exception as e:
                    out.update(status="error", message=str(e)[:300])

    out["seconds"] = round(time.time() - t0, 2)
    if log:
        log_query(out, run_id)
    return out


def show(res):
    print(f"\nQ: {res['question']}")
    print(f"status: {res['status']}  model: {res['model']}  {res['seconds']}s  "
          f"est: {res['bytes_estimated'] / 1e6:.2f} MB  billed: {res['bytes_billed'] / 1e6:.1f} MB")
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