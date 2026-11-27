"""Score the analyst: run each question, run the golden SQL live, compare result sets.

Match rule: same rows (any order, column names ignored); numbers match within 0.5% or 0.01.
Out-of-scope questions pass when the analyst refuses or the guard blocks the SQL.
"""
import csv
import datetime
import glob
import math
import os
import statistics
import sys
import time
from decimal import Decimal

from dotenv import load_dotenv
from google.cloud import bigquery

from analyst.ask import answer

load_dotenv(override=True)
PROJECT = os.environ["GCP_PROJECT_ID"]
AS_OF = datetime.date.fromisoformat(os.environ.get("BENCH_AS_OF", "2026-11-27"))
SLEEP = float(os.environ.get("BENCH_SLEEP", "2"))


def load_questions():
    qs = []
    for f in sorted(glob.glob("benchmark/q_*.csv")):
        with open(f, newline="", encoding="utf-8") as fh:
            qs.extend(csv.DictReader(fh))
    if not qs:
        sys.exit("no benchmark/q_*.csv files found")
    return qs


def run_golden(client, sql):
    cfg = bigquery.QueryJobConfig(default_dataset=f"{PROJECT}.marts",
                                  maximum_bytes_billed=500_000_000)
    return [dict(r) for r in client.query(sql, job_config=cfg).result()]


def cell(v):
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float, Decimal)):
        return float(v)
    return str(v)


def table(rows):
    return [tuple(cell(v) for v in r.values()) for r in rows]


def sort_key(row):
    return tuple(round(c) if isinstance(c, float) else c for c in row)


def same(a, b):
    if len(a) != len(b):
        return False
    try:
        pairs = zip(sorted(a, key=sort_key), sorted(b, key=sort_key))
    except TypeError:
        return False
    for ra, rb in pairs:
        if len(ra) != len(rb):
            return False
        for x, y in zip(ra, rb):
            if isinstance(x, float) and isinstance(y, float):
                if not math.isclose(x, y, rel_tol=0.005, abs_tol=0.01):
                    return False
            elif x != y:
                return False
    return True


def failure_tag(q, res, correct):
    if res["message"].startswith("LLM failed"):
        return "llm_error"
    if q["expected"] == "refuse":
        return "" if res["status"] in ("refused", "blocked") else "answered_out_of_scope"
    if correct:
        return ""
    return {"refused": "wrongly_refused", "blocked": "blocked_by_guard",
            "error": "sql_error", "too_expensive": "too_expensive"}.get(res["status"], "wrong_result")


def pct(a, b):
    return f"{100 * a / b:.0f}% ({a}/{b})" if b else "n/a"


def golden_mode(client, questions):
    for q in questions:
        if q["expected"] != "answer":
            continue
        print(f"\n{q['id']}  {q['question']}")
        try:
            rows = run_golden(client, q["golden_sql"])
            for r in rows[:8]:
                print("   ", dict(r))
            if len(rows) > 8:
                print(f"    ... {len(rows)} rows")
        except Exception as e:
            print(f"    GOLDEN SQL FAILED: {str(e)[:200]}")


def main():
    args = sys.argv[1:]
    questions = load_questions()
    client = bigquery.Client(project=PROJECT)
    if args and args[0] == "--golden":
        return golden_mode(client, questions)

    tag_name = args[0] if args else datetime.datetime.now().strftime("%Y%m%d_%H%M")
    out = []
    for i, q in enumerate(questions, 1):
        res = answer(q["question"], as_of=AS_OF, run_id=tag_name)
        correct, golden_err = False, ""
        if q["expected"] == "refuse":
            correct = res["status"] in ("refused", "blocked")
        else:
            try:
                gold = run_golden(client, q["golden_sql"])
                correct = res["status"] == "ok" and same(table(res["rows"]), table(gold))
            except Exception as e:
                golden_err = f"golden failed: {str(e)[:150]}"
        tag = "golden_error" if golden_err else failure_tag(q, res, correct)
        out.append({
            "id": q["id"], "difficulty": q["difficulty"], "question": q["question"],
            "expected": q["expected"], "status": res["status"], "correct": correct, "tag": tag,
            "seconds": res["seconds"], "bytes_estimated": res["bytes_estimated"],
            "bytes_billed": res["bytes_billed"], "model": res["model"],
            "sql": res["sql"], "message": golden_err or res["message"],
        })
        print(f"[{i}/{len(questions)}] {q['id']:<4} {'PASS' if correct else 'FAIL'}  "
              f"{res['status']:<13} {tag}")
        time.sleep(SLEEP)

    os.makedirs("benchmark/results", exist_ok=True)
    path = f"benchmark/results/{tag_name}.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    ans = [r for r in out if r["expected"] == "answer"]
    oos = [r for r in out if r["expected"] == "refuse"]
    print(f"\n=== {tag_name} | model {out[0]['model']} | as_of {AS_OF} ===")
    print(f"execution accuracy : {pct(sum(r['correct'] for r in ans), len(ans))}")
    for d in ("easy", "medium", "hard"):
        sub = [r for r in ans if r["difficulty"] == d]
        if sub:
            print(f"  {d:<7}          : {pct(sum(r['correct'] for r in sub), len(sub))}")
    print(f"safe refusals      : {pct(sum(r['correct'] for r in oos), len(oos))}")
    print(f"median seconds     : {statistics.median(r['seconds'] for r in out):.1f}")
    billed = [r["bytes_billed"] for r in out if r["status"] == "ok"]
    if billed:
        print(f"median MB billed   : {statistics.median(billed) / 1e6:.1f}")
    tags = {}
    for r in out:
        if r["tag"]:
            tags[r["tag"]] = tags.get(r["tag"], 0) + 1
    print(f"failure tags       : {tags or 'none'}")
    print(f"details            : {path}")


if __name__ == "__main__":
    main()