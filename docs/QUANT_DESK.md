# Aurum Quant Desk

The Quant Desk is an optional AI conversation layer for the existing Aurum research system. It adds specialist roles and a team-debate mode without changing the adopted trading strategy or placing orders.

## What is included

- **Quant Researcher** — proposes falsifiable experiments and benchmark comparisons.
- **Technical Analyst** — discusses trend, momentum, volatility and candlestick features, with a requirement to test signals rather than assume they work.
- **Macro Analyst** — interprets gold, rates, dollar and cross-asset context.
- **ML Quant** — evaluates model choice, calibration, leakage and incremental predictive value.
- **Risk Manager** — challenges drawdown, concentration, turnover, costs and position sizing.
- **Independent Reviewer** — tries to falsify the proposed conclusion and checks for overfitting.
- **Team debate** — asks multiple roles to independently assess a question and then produces a synthesis.

The desk injects a small, read-only context from the repository's README, strategy report, decisions and latest portfolio-lab summary when those files exist. It does not run arbitrary code, edit strategy files, or place trades.

## Run it

1. Install Aurum's existing dependencies and activate the virtual environment.
2. Install/run an OpenAI-compatible local model server such as Ollama if you want no per-token API bill. For Ollama, pull a chat model first, for example `ollama pull qwen2.5:7b`.
3. Run the model server, then launch the Streamlit app:
   ```bash
   python -m streamlit run app.py
   ```
4. Open **Quant Desk** in Streamlit's multipage navigation.

Defaults target a local OpenAI-compatible endpoint at `http://localhost:11434/v1`, model `qwen2.5:7b`. Configure these optional variables in your ignored local `.env` or shell:

| Variable | Default | Purpose |
|---|---|---|
| `AURUM_LLM_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible `/chat/completions` base URL |
| `AURUM_LLM_MODEL` | `qwen2.5:7b` | Model name served by your provider |
| `AURUM_LLM_API_KEY` | unset | Optional provider key; do not commit it |

A local model can avoid per-request API charges, but needs enough RAM/compute and may be less capable. A hosted API may cost money according to the provider's pricing. Chat messages are sent to whichever model endpoint you configure; do not submit secrets or private account data.

## Automation roadmap

This first version is interactive, not a permanently running autonomous agent. The next safe steps are opt-in scheduled data refreshes and research reports, followed by pre-registered experiment runs. Keep them separate from the chat UI, limit runtime/API spending, save logs and provenance, and never allow generated research to deploy strategy changes automatically.

Recommended automation sequence:
1. Reproduce the current baseline and retain a dated report.
2. Compare the existing precious-metals universe with a broad equity benchmark (e.g. SPY) using the same dates, fills, costs and risk metrics.
3. Pre-register a small number of technical/momentum/mean-reversion experiments and run walk-forward tests.
4. Accept a new signal only if it improves on simple baselines out of sample after costs, with uncertainty and multiple-testing risk reported.
5. Paper-trade approved changes with realistic fills before considering any broker integration.

## Important limits

- AI explanations are hypotheses, not evidence; verify numeric claims against generated reports.
- The model sees only the repository context included in the prompt; it is not automatically browsing the internet or streaming live prices.
- The desk does not train itself from conversations. Improvements require explicit, reproducible experiments and review.
- This is educational research software, not investment advice. No real-money execution is enabled.
