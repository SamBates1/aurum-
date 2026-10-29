"""Strategy registry: every strategy version tried, its status and history, Fair Test reports and owner approvals."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from aurum import fairtest as FT
from aurum import gates
from aurum import registry as R
from aurum import spec as SP

st.set_page_config(page_title="Aurum Strategy Registry", page_icon="🗂️", layout="wide")
st.title("🗂️ Strategy registry")
st.caption(
    "Every version of every strategy that was backtested, tested or approved. Counting the "
    "tries is what makes the luck check honest."
)

reg = R.Registry()
rows = reg.strategies()
st.markdown(
    f"**{len(rows)}** versions registered here · **{reg.n_trials()}** tries counted for the "
    f"luck check (including {reg.prior_trials} earlier experiment variants) · holdout looked at "
    f"**{reg.holdout_views()}** times"
)
for w in R.overfitting_warnings(reg, ""):
    st.caption("⚠️ " + w)

if rows:
    df = pd.DataFrame(rows)[["spec_hash", "id", "version", "name", "status", "status_at", "created_at"]]
    st.dataframe(df.iloc[::-1], hide_index=True, width="stretch")
    pick = st.selectbox(
        "Details for", df["spec_hash"], format_func=lambda h: f"{h} · {df.set_index('spec_hash').at[h, 'name']}"
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Status history**")
        st.dataframe(pd.DataFrame(reg.history(pick)), hide_index=True, width="stretch")
        st.markdown("**Runs**")
        runs = pd.DataFrame(reg.runs(pick))
        if len(runs):
            st.dataframe(
                runs[["run_id", "kind", "created_at", "period", "data_label", "sharpe_daily"]],
                hide_index=True,
                width="stretch",
            )
    with c2:
        st.markdown("**Definition**")
        st.code(SP.dump(reg.spec_of(pick)), language="yaml")
else:
    st.info("Nothing registered yet: run a backtest in the Strategy Designer.")

st.divider()
st.markdown("### Fair Test reports")
fts = FT.latest_results()
if fts:
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "strategy": r["name"],
                    "version": r["version"],
                    "hash": h,
                    "verdict": r["status"].upper(),
                    "run": r["run_at"],
                    "data": r["data_label"],
                    "file": r.get("_file", ""),
                }
                for h, r in fts.items()
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    h = st.selectbox("Read report", list(fts), format_func=lambda k: f"{fts[k]['name']} ({k})")
    st.markdown(FT.report_markdown(fts[h]))
else:
    st.info("No Fair Test reports saved yet.")

st.divider()
st.markdown("### Owner approvals (research/approvals.yaml)")
appr = gates.load_approvals()
if appr:
    st.dataframe(pd.DataFrame(appr), hide_index=True, width="stretch")
st.download_button(
    "Download registry summary (JSON)",
    json.dumps({"strategies": rows, "approvals": appr}, default=str, indent=1),
    file_name="registry.json",
)
