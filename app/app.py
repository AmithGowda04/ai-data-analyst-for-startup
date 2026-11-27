"""Streamlit chat UI for the AI data analyst."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from analyst.ask import answer
from analyst.context import load_marts

st.set_page_config(page_title="AI Data Analyst", page_icon="📊", layout="wide")
st.title("📊 AI Data Analyst")
st.caption("Ask a business question in plain English. Answers come from a governed dbt metrics layer "
           "on synthetic data (thelook e-commerce + generated ad spend).")

EXAMPLES = [
    "Which paid channel had the best ROAS in Q4 2025?",
    "How many new customers did we get each quarter of 2025?",
    "What were the top 3 product categories by net revenue in 2025?",
    "What will revenue be next year?",
]


@st.cache_data
def metric_defs():
    out = {}
    for m in load_marts():
        out.update(m["metrics"])
    return out


def metrics_used(sql):
    used = {}
    for name, definition in metric_defs().items():
        cols = set(re.findall(r"[a-z_]{4,}", definition.split(".")[0].lower())) - {"safe_divide", "sum"}
        if cols and any(c in (sql or "").lower() for c in cols):
            used[name] = definition
    return used


def chart(df):
    if len(df) < 2 or len(df.columns) < 2:
        return
    num = [c for c in df.columns[1:] if pd.api.types.is_numeric_dtype(df[c])]
    if not num:
        return
    data = df.set_index(df.columns[0])[num]
    first = df.iloc[:, 0]
    if pd.api.types.is_datetime64_any_dtype(first) or "date" in str(first.dtype) or "month" in df.columns[0].lower():
        st.line_chart(data)
    else:
        st.bar_chart(data)


def render(res):
    status = res["status"]
    if status == "ok":
        df = pd.DataFrame(res["rows"])
        for c in df.columns:
            if df[c].map(lambda v: hasattr(v, "quantize")).any():
                df[c] = df[c].astype(float)
        if len(df) == 1 and len(df.columns) == 1:
            st.metric(df.columns[0], f"{df.iloc[0, 0]:,.2f}" if isinstance(df.iloc[0, 0], float) else df.iloc[0, 0])
        else:
            st.dataframe(df, use_container_width=True)
            chart(df)
    elif status == "refused":
        st.warning(f"I can't answer that: {res['message']}")
    elif status == "blocked":
        st.error(f"That query was blocked by the safety checks: {res['message']}")
    elif status == "too_expensive":
        st.error(f"That query is too expensive to run: {res['message']}")
    else:
        st.error(f"Something went wrong: {res['message']}")
    if res.get("sql"):
        with st.expander("SQL used"):
            st.code(res["sql"], language="sql")
    used = metrics_used(res.get("sql"))
    if used:
        with st.expander("Metric definitions used"):
            for n, d in used.items():
                st.markdown(f"**{n}**: {d}")
    st.caption(f"model {res['model']} · {res['seconds']}s · scanned {res['bytes_billed'] / 1e6:.1f} MB billed")


if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.subheader("Try one")
    for ex in EXAMPLES:
        if st.button(ex, use_container_width=True):
            st.session_state.pending = ex
    st.markdown("---")
    st.caption("Read-only access to a `marts` dataset only. Every query is validated, dry-run "
               "against a byte cap, and logged.")

for q, res in st.session_state.history:
    with st.chat_message("user"):
        st.write(q)
    with st.chat_message("assistant"):
        render(res)

question = st.chat_input("Ask about revenue, orders, ad spend, ROAS, CAC, conversion or retention")
question = question or st.session_state.pop("pending", None)
if question:
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            res = answer(question, run_id="ui")
        render(res)
    st.session_state.history.append((question, res))