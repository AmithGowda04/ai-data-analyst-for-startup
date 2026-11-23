# 7-Day Roadmap: AI Data Analyst for a Startup
Sprint: Mon 23 Nov to Sun 29 Nov 2026, about 5-7 hours per day (35-45 hours).
Goal: a public GitHub repo where a founder asks a plain-English business question and gets a correct answer, the SQL used and a chart, built on a governed dbt metrics layer, orchestrated by Airflow, with a measured accuracy benchmark.

All tools are free: BigQuery sandbox (check current limits), dbt Core, Airflow in Docker (needs ~8 GB RAM), Streamlit, GitHub, and an LLM free tier or Ollama (check free-tier rate limits).

| Day | Focus | Output |
|---|---|---|
| 1 Mon 23 | Setup + learn dbt/Airflow basics | Tools running, data explored |
| 2 Tue 24 | Ingest scripts (thelook, GA4, ad spend) | Raw tables, idempotent loads |
| 3 Wed 25 | Airflow DAG | Scheduled incremental loads |
| 4 Thu 26 | dbt staging, marts, metrics, tests | `dbt build` passes |
| 5 Fri 27 | Text-to-SQL + guardrail tests | End-to-end guarded answer |
| 6 Sat 28 | Dry-run, refusals, query log, benchmark | First measured accuracy |
| 7 Sun 29 | Iterate accuracy, UI, README, demo | Public, polished repo |

Rule: never skip measuring. If time runs short, cut in this order: demo video, CI, UI polish, stretch goals. If Airflow is not working by the end of Day 3, drop it, keep plain Python scripts, and keep Airflow off the CV.

---
## Day 1 (Mon): setup and learning (5-6h)
- [ ] Push this starter folder to a new public GitHub repo `ai-data-analyst`
- [ ] Google Cloud project, BigQuery sandbox, read-only service account (key never committed)
- [ ] Python 3.10+, Docker Desktop, Git, `make setup`, `make adspend`
- [ ] Explore `thelook_ecommerce` (orders, order_items, users, products, events) and `ga4_obfuscated_sample_ecommerce`; write down tables and joins
- [ ] Learn dbt basics (models, sources, ref, tests) and Airflow basics (DAG, task, schedule): about 3 hours total
- [ ] Pick the LLM, make one test call
**Done when:** you can run a BigQuery query from Python and explain what dbt and Airflow each do.

## Day 2 (Tue): ingest (6h)
- [ ] Generate ad spend for the same dates as thelook orders; load to `raw.ad_spend`
- [ ] Copy orders, order_items, users, products into your own `raw` dataset; load GA4 events
- [ ] Incremental by date and idempotent (re-run must not duplicate rows)
- [ ] Log row counts per table
**Done when:** a second run changes nothing (prove it with counts).

## Day 3 (Wed): Airflow (6h)
- [ ] Run Airflow in Docker (official docker-compose)
- [ ] One DAG wrapping your load scripts: daily schedule, retries, a failure log line
- [ ] Trigger a run, then re-trigger; confirm zero duplicates
- [ ] ADR in docs/decisions: why incremental by date, how duplicates are prevented
**Timebox:** 4 hours for Airflow. If still stuck, drop it (see rule above).
**Capture:** load time per DAG run, row counts.

## Day 4 (Thu): dbt and metrics layer (6-7h)
- [ ] `dbt init`, BigQuery connection, sources
- [ ] Staging models; marts such as `fct_orders`, `fct_ad_spend_daily`, `dim_users`, `dim_products`
- [ ] Define 8 metrics in plain language: revenue, orders, AOV, ad spend, ROAS, CAC, conversion rate, retention
- [ ] Tests: unique, not_null, relationships, accepted_values, one custom test (revenue never negative)
- [ ] Descriptions on every mart column; `dbt docs generate`
- [ ] ADR: how each metric is defined and why
**Capture:** number of models and tests, dbt build time.
**Done when:** `dbt build` passes.

## Day 5 (Fri): text-to-SQL and guardrail tests (6-7h)
- [ ] Prompt = question + metric definitions + mart schemas + 3-5 worked examples
- [ ] Generate context from dbt `manifest.json`, not by hand
- [ ] Write the guard tests first, then implement `guardrails/sql_guard.py`: SELECT only, one statement, allowed tables only, enforced LIMIT
- [ ] First end-to-end: question in, validated SQL, BigQuery result out
**Done when:** a script answers a question through the guarded path and the tests pass.

## Day 6 (Sat): guards, log, benchmark (7h)
- [ ] BigQuery dry run with `maximum_bytes_billed`; reject above your cap
- [ ] Refusal path for out-of-scope or missing-context questions
- [ ] `query_log` table: question, SQL, bytes billed, latency, outcome
- [ ] Write 40 questions in `benchmark/questions.csv` (easy/medium/hard, plus 6 out-of-scope) with golden SQL; check the golden SQL by hand
- [ ] Build the scorer (compare result sets) and take your first accuracy score; tag every failure
**Done when:** you have a first measured accuracy and a failure breakdown.

## Day 7 (Sun): iterate, UI, ship (7h)
- [ ] 2-3 improvement rounds, one change at a time (prompt wording, examples, metric descriptions); re-score each time and keep a results table
- [ ] Streamlit chat: answer, SQL used, chart, metrics used, clear "can't answer" state
- [ ] README: pitch, architecture diagram on the first screen, results table with measured numbers, how to run, decisions, "what breaks at 100x"
- [ ] Fresh-folder run test; no secrets in git history; GitHub Actions for the guard tests (optional)
- [ ] 2-minute demo video linked in the README; pin the repo
**Done when:** a stranger can clone, run and understand it in 5 minutes.

---
## Numbers to capture (only measured values)
1. Execution accuracy before vs after each iteration
2. Median seconds from question to answer
3. Median bytes billed per question
4. % of out-of-scope questions safely refused

## CV line (template, use only after measuring)
"Built a BigQuery + dbt analytics platform (Airflow-orchestrated loads) with a governed metrics layer and an LLM analyst for plain-English questions; reached [X]% execution accuracy on a [N]-question benchmark, with SQL validation and dry-run guards capping each query at [Y] MB scanned."
Remove "Airflow-orchestrated" if you dropped Airflow. Send me the real numbers and I will add the project and the dbt/Airflow skills you actually used.

## Interview questions
1. How do you stop a wrong but plausible query?
2. How do you block expensive or destructive SQL?
3. What happens when the schema changes?
4. Why a metrics layer instead of raw tables?
5. Which failure category was biggest and what did you change?
6. What breaks at 100x data or users?

## Rules
- Use AI help to learn and speed up, but be able to explain every model, DAG and guard line yourself.
- Never put an unmeasured number in the README or CV. Label generated data as synthetic.
- Commit small and often.
