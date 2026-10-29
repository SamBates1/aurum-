"""Streamlit page for live conversations with Aurum specialist research agents."""

from __future__ import annotations

import streamlit as st

from aurum.desk import (
    AGENTS,
    HOW_ROLES_WORK,
    agent_reply,
    audit_record,
    log_answer,
    provider_info,
    research_context,
    team_debate,
)

st.set_page_config(page_title="Aurum Quant Desk", page_icon="🧠", layout="wide")
st.title("🧠 Aurum Quant Desk")
st.caption(
    "Interactive AI research conversations grounded in Aurum's saved research. "
    "Not live market monitoring; no strategy changes or real-money orders are made here."
)

with st.sidebar:
    st.subheader("Connection")
    st.markdown(
        "The default endpoint is a local OpenAI-compatible server. Start Ollama locally, "
        "or configure AURUM_LLM_BASE_URL, AURUM_LLM_MODEL and optional AURUM_LLM_API_KEY "
        "in your shell before starting Streamlit."
    )
    st.caption("Local models can avoid API charges; hosted models may cost money.")
    info = provider_info()
    st.markdown(
        f"**Active provider:** `{info['base_url']}`  \n**Model:** `{info['model']}`  \n"
        f"**API key set:** {'yes' if info['api_key_set'] else 'no'}  \n"
        f"**Runs on this computer:** {'yes' if info['local'] else 'no (hosted: may cost money)'}"
    )
    st.caption(HOW_ROLES_WORK)
    if st.button("Show loaded research context"):
        st.session_state["show_desk_context"] = not st.session_state.get("show_desk_context", False)
    if st.session_state.get("show_desk_context"):
        st.code(research_context()[:12000], language="markdown")

mode = st.radio("Conversation mode", ["Chat with one specialist", "Whole-team debate"], horizontal=True)
if mode == "Chat with one specialist":
    agent = st.selectbox("Choose your research partner", list(AGENTS))
    st.caption(AGENTS[agent])
else:
    st.info(
        "Four specialist prompts assess the question separately, then a reviewer prompt challenges and "
        "synthesises them. " + HOW_ROLES_WORK
    )

if "quant_desk_messages" not in st.session_state:
    st.session_state["quant_desk_messages"] = []
if "quant_desk_mode" not in st.session_state:
    st.session_state["quant_desk_mode"] = mode
if st.session_state["quant_desk_mode"] != mode:
    st.session_state["quant_desk_messages"] = []
    st.session_state["quant_desk_mode"] = mode
if st.button("Clear this conversation"):
    st.session_state["quant_desk_messages"] = []
    st.rerun()

for item in st.session_state["quant_desk_messages"]:
    with st.chat_message(item["role"]):
        if item.get("agent"):
            st.caption(item["agent"])
        st.markdown(item["content"])

question = st.chat_input("Ask about a strategy, indicator, market, model or experiment…")
if question:
    st.session_state["quant_desk_messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    if mode == "Chat with one specialist":
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state["quant_desk_messages"][:-1]
            if m["role"] in {"user", "assistant"}
        ]
        with st.chat_message("assistant"):
            st.caption(agent)
            with st.spinner(f"{agent} is thinking…"):
                try:
                    answer = agent_reply(agent, question, history=history)
                    st.markdown(answer)
                    st.session_state["quant_desk_messages"].append(
                        {"role": "assistant", "agent": agent, "content": answer}
                    )
                    log_answer(audit_record("specialist", agent, question, answer))
                except RuntimeError as exc:
                    st.error(str(exc))
    else:
        with st.spinner("The team is assessing the question…"):
            try:
                responses = team_debate(question)
                for name, answer in responses:
                    with st.chat_message("assistant"):
                        st.caption(name)
                        st.markdown(answer)
                    st.session_state["quant_desk_messages"].append(
                        {"role": "assistant", "agent": name, "content": answer}
                    )
                    log_answer(audit_record("team debate", name, question, answer))
            except RuntimeError as exc:
                st.error(str(exc))

st.divider()
st.caption(
    "Evidence rule: agent suggestions are hypotheses until a reproducible backtest supports them. "
    "The desk does not automatically train itself, deploy code, or place trades. Answers are logged locally "
    "(logs/quant_desk.jsonl, not committed) with the provider and model that produced them."
)
