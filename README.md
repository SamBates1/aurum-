# Aurum: a macro-aware gold & miners signal bot

Aurum analyses gold, silver and gold-mining stocks in near real time and gives
**BUY / HOLD / SELL** decisions, each with plain-English reasons. It can also
trade those decisions in a **paper portfolio** (simulated money) so you can see
how good they really are.

It combines four kinds of analysis:

| Component | What it does | Weight |
|---|---|---|
| **Machine learning** | Gradient-boosted trees predict whether the price will be higher in 5 trading days, using technical *and* macro features | 50% |
| **Technical** | Trend (50/200-day averages), MACD momentum, RSI overbought/oversold | 25% |
| **News sentiment** | Scores recent headlines (VADER + a finance word list) | 15% |
| **Fundamentals** | P/E, margins, leverage, free cash flow (miners only) | 10% |

Universe (edit `config.yaml`): **GLD, SLV, GDX** (ETFs) and **NEM, AEM, WPM** (miners).
Macro inputs: 10y real yield and breakeven inflation (FRED), dollar index, 10y yield, VIX (Yahoo).

> Educational project. Nothing here is investment advice.

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py               # dashboard at http://localhost:8501
```

The first load runs the walk-forward research for all six tickers (about a minute), then caches it for 6 hours.

Other entry points:

```bash
python run_backtest.py             # backtest every ticker, saves results/backtest_summary.csv
python run_bot.py                  # print live signals every 60s in the terminal
python run_bot.py --paper          # ...and paper-trade them
AURUM_OFFLINE=1 pytest -q          # tests (synthetic data, no internet needed)
AURUM_OFFLINE=1 streamlit run app.py   # demo with synthetic data
```

## Dashboard

* **Live signals** – universe table, the decision for the selected ticker, the reasons behind it, candlestick chart with moving averages and RSI, intraday chart, scored headlines. Refreshes every 60 seconds.
* **Backtest** – strategy vs buy-and-hold equity curves, Sharpe, Sortino, max drawdown, and the model's out-of-sample accuracy and AUC.
* **Paper portfolio** – equity, positions with stop-losses, trade log. Execute signals manually or switch on auto paper-trading in the sidebar.
* **Macro** – each driver plotted against gold, with its correlation.

## How it works

```
aurum/
  data.py        prices (yfinance), macro (FRED + Yahoo), fundamentals, news
  features.py    technical + macro features, labels
  model.py       walk-forward training and out-of-sample metrics
  backtest.py    next-day execution, transaction costs, risk metrics
  sentiment.py   headline scoring
  signals.py     scores each component, combines into a decision with reasons
  paper.py       paper portfolio with volatility-scaled sizing and ATR stops
  pipeline.py    glue: research() is slow & cached, decide() is fast & live
  synthetic.py   fake market data for offline demos and tests
```

**"Real time"**: Yahoo data is free but can be delayed by up to ~15 minutes for some
exchanges. During market hours the latest daily bar is today's partial bar, so signals move
through the day. For true streaming data, see *Next steps*.

---

## Interview talking points

These are the parts that show rigour, which is what interviewers probe for.

1. **Walk-forward validation.** The model is retrained every quarter using only data available at the time and is scored only on the following quarter. No random train/test split, because shuffling time-series data leaks the future into training.
2. **Purge gap.** Labels look 5 days ahead, so the last 5 training rows overlap the test window. They are dropped before each fit.
3. **No lookahead anywhere.** Trades are decided at today's close and earn *tomorrow's* return. FRED data is lagged a day because it's published after the close. Fundamentals are *not* used in the backtest because free fundamentals aren't point-in-time (today's P/E wasn't known in 2015). `tests/` checks these properties automatically, e.g. features on truncated data must equal features on full data.
4. **Honest baselines.** Accuracy is compared with the base rate (always saying "up"), and AUC with 0.5. The dashboard warns when a model is close to a coin flip. A strategy is compared with buy-and-hold *after* costs.
5. **Why gold, why these features.** Gold pays no income, so its opportunity cost is the real yield. When real yields fall, gold usually rises. A stronger dollar makes gold dearer for non-US buyers. Spikes in VIX signal safe-haven demand. Miners behave like leveraged gold, plus company-specific risk, which is why fundamentals apply to them.
6. **Risk management.** Positions are scaled by volatility (a miner gets less capital than GLD), capped at 20% of equity, and protected by a 2×ATR stop.
7. **What I'd say about the results.** Expect a modest edge at best. Markets are close to efficient, and a 52–55% AUC that survives costs is already meaningful. The value of the project is the framework for testing ideas honestly.

## Next steps (ideas to extend it)

- **Streaming data and broker paper trading** – Alpaca offers a free paper-trading account and API. Swap `paper.py`'s local ledger for its order endpoint.
- **LLM sentiment** – replace VADER with an LLM call that judges each headline's impact on gold.
- **Point-in-time fundamentals** – a paid data source would let fundamentals enter the backtest properly.
- **Explainability** – SHAP values to show which features drive each prediction.
- **More assets** – add copper/oil or switch sector entirely by editing `config.yaml`.
- **Deploy** – Streamlit Community Cloud hosts the dashboard free; put the link on your CV.
