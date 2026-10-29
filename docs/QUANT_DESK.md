# Aurum Quant Desk and automated research

## Quant Desk

The Quant Desk is an optional AI conversation layer for the existing Aurum research system. It adds specialist roles and a team-debate mode without changing the adopted trading strategy or placing orders.

- **Quant Researcher** — proposes falsifiable experiments and benchmark comparisons.
- **Technical Analyst** — discusses trend, momentum, volatility and candlestick features, treating them as hypotheses to test.
- **Macro Analyst** — interprets gold, rates, dollar and cross-asset context.
- **ML Quant** — evaluates model choice, calibration, leakage and incremental predictive value.
- **Risk Manager** — challenges drawdown, concentration, turnover, costs and position sizing.
- **Independent Reviewer** — tries to falsify conclusions and checks for overfitting.
- **Team debate** — four specialists independently assess a question, then the reviewer synthesises their answers.

The desk injects bounded, read-only excerpts from the repository's saved research. It does not execute arbitrary code, edit strategy files, or place trades.

## Run the chat

1. Install Aurum's dependencies and activate the virtual environment.
2. Install and run Ollama if you want to avoid per-token API charges.
3. Pull a chat model, for example: ollama pull qwen2.5:7b.
4. Run: python -m streamlit run app.py.
5. Open Quant Desk in Streamlit's multipage navigation.

Defaults target http://localhost:11434/v1, model qwen2.5:7b. Configure these optional variables in your local shell or ignored .env:

| Variable | Default | Purpose |
|---|---|---|
| AURUM_LLM_BASE_URL | http://localhost:11434/v1 | OpenAI-compatible /chat/completions base URL |
| AURUM_LLM_MODEL | qwen2.5:7b | Model name served by your provider |
| AURUM_LLM_API_KEY | unset | Optional provider key; never commit it |

Local models need sufficient RAM/compute and may be less capable. Hosted APIs may incur charges. Do not submit secrets or private account data.

## Automated daily market snapshot

Run manually:

    python scripts/daily_market_report.py

Use a subset:

    python scripts/daily_market_report.py --tickers GLD SLV GDX SPY

The script uses Aurum's validated/cache-aware price data layer and writes a Markdown report under reports/daily/. It summarises the most recent available bar, 1/21/63/252-session returns, 21-session annualised volatility, RSI-14, gaps to 50/200-day moving averages, and historical drawdown. The default universe includes Aurum assets plus SPY, QQQ, DBC and TLT as cross-asset comparison candidates. This is descriptive monitoring, not a signal or a fair performance comparison; a proper comparison must use the same dates, fills, costs and risk accounting.

A GitHub Actions workflow runs on weekdays at 21:30 UTC and on manual dispatch. It uploads the report as an artifact for 14 days; it does not commit generated files, call an LLM, place orders or modify the strategy. Data availability and market holidays can cause missing or stale observations, which are shown in the report.

## Asset comparison and experiment protocol

Aurum already has a research lab for comparable asset tests. Use:

- python run_plab.py --set core to reproduce the core precious-metals portfolio lab.
- python run_plab.py --set other to test the predefined alternate precious-metals universe.
- python run_lab.py --set core and python run_lab.py --set other for the strategy research lab.
- python run_experiments.py --quick for a faster experiment-code check (use synthetic/offline mode for code-path checks only).
- python run_experiments.py --tickers SPY --quick to evaluate Aurum's strategy rules on SPY against that ticker's buy-and-hold reference. This is an exploratory comparison, not proof that SPY or the rules are better; use the same holdout, costs and decision protocol.

To test whether the system generalises beyond precious metals, add a broad-market benchmark such as SPY to a separately registered, same-date experiment; do not infer a trading edge from the daily snapshot alone. Keep all variants registered before running, report gross/net and 2x-cost results, use walk-forward validation, preserve a final holdout, and account for every attempted variant in multiple-testing statistics.

## Safety and limits

- AI explanations are hypotheses, not evidence; verify numeric claims against generated reports.
- The chat does not automatically browse the internet or stream live prices.
- The daily snapshot is scheduled data collection, not continuous intraday monitoring.
- The desk does not learn from conversations or deploy generated strategy changes. Improvements require explicit, reproducible experiments and review.
- Paper-trading performance is not live execution evidence. Real-money execution is not enabled by this feature.
