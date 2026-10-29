# Aurum research report

**Generated:** 2026-10-29T13:44:24+00:00 · **commit:** `cb92b1c` · **config:** `79ebbb3a8f63`


## Setup
* Universe: GLD, SLV, GDX, NEM, AEM, WPM. Out-of-sample period starts 2013-10-18 (after 756 training days).
* **Development:** 2013-10-18 → 2023-12-31. **Untouched holdout:** 2024-01-01 → 2026-10-29.
* Decisions at the close, filled at the next open. Costs per ticker (one-way bps): {'GLD': 3, 'SLV': 5, 'GDX': 5, 'NEM': 8, 'AEM': 10, 'WPM': 10}.
* Cash and the Sharpe risk-free rate use the 3-month T-bill, lagged 2 business days.
* All parameters were fixed in `config.yaml` before this run; nothing below was tuned on the holdout.


## Portfolio results: holdout

Equal sleeves across tickers (each capped at 20%), after costs.

| strategy | cagr | volatility | sharpe | sortino | max_drawdown | calmar | time_in_market | trades | costs_per_year |
|---|---|---|---|---|---|---|---|---|---|
| strategy | 23.0% | 13.4% | 1.291 | 1.837 | -13.5% | 1.701 | 100.0% | 0 | 0.2% |
| timing_v02 | 20.8% | 17.2% | 0.937 | 1.249 | -17.2% | 1.211 | 76.9% | 78 | 0.3% |
| buy_hold | 42.5% | 35.9% | 1.049 | 1.457 | -38.0% | 1.119 | 100.0% | 0 | 0.0% |
| vol_sized_hold | 27.2% | 25.1% | 0.914 | 1.247 | -29.5% | 0.922 | 100.0% | 0 | 0.0% |
| sma_trend | 22.1% | 19.5% | 0.906 | 1.208 | -20.0% | 1.106 | 82.4% | 38 | 0.2% |
| momentum | 13.2% | 14.7% | 0.626 | 0.806 | -22.0% | 0.600 | 33.7% | 27 | 0.1% |
| technical_only | 19.0% | 15.0% | 0.954 | 1.245 | -15.7% | 1.209 | 70.6% | 127 | 0.4% |
| ml_only | 17.2% | 7.8% | 1.528 | 2.258 | -5.2% | 3.279 | 48.5% | 183 | 0.6% |
| ml_no_macro | 15.2% | 7.0% | 1.442 | 2.136 | -5.2% | 2.925 | 43.0% | 215 | 0.7% |
| cash | 4.4% | 0.0% | – | – | 0.0% | – | 0.0% | 0 | 0.0% |


## Portfolio results: development

Equal sleeves across tickers (each capped at 20%), after costs.

| strategy | cagr | volatility | sharpe | sortino | max_drawdown | calmar | time_in_market | trades | costs_per_year |
|---|---|---|---|---|---|---|---|---|---|
| strategy | 3.4% | 11.5% | 0.241 | 0.345 | -20.8% | 0.164 | 100.0% | 0 | 0.2% |
| timing_v02 | 0.8% | 8.3% | -0.017 | -0.024 | -21.1% | 0.036 | 46.1% | 570 | 0.7% |
| buy_hold | 6.0% | 30.1% | 0.303 | 0.437 | -43.0% | 0.140 | 100.0% | 0 | 0.0% |
| vol_sized_hold | 3.4% | 14.3% | 0.221 | 0.316 | -25.8% | 0.134 | 100.0% | 0 | 0.0% |
| sma_trend | -0.2% | 9.2% | -0.110 | -0.150 | -24.7% | -0.008 | 48.6% | 325 | 0.4% |
| momentum | -0.6% | 5.8% | -0.293 | -0.388 | -15.0% | -0.041 | 24.5% | 283 | 0.3% |
| technical_only | 1.7% | 9.1% | 0.090 | 0.129 | -20.4% | 0.082 | 49.4% | 613 | 0.7% |
| ml_only | -0.4% | 6.0% | -0.239 | -0.329 | -16.7% | -0.021 | 35.6% | 955 | 1.1% |
| ml_no_macro | 0.6% | 5.8% | -0.080 | -0.111 | -19.5% | 0.031 | 36.2% | 838 | 0.9% |
| cash | 1.3% | 0.1% | – | – | -0.0% | 3522.615 | 0.0% | 0 | 0.0% |


## Uncertainty (stationary block bootstrap, 90% intervals)

Descriptive intervals, not a formal significance test. Overlapping labels and many comparisons mean a single good number can easily be luck.

| period | vs | sharpe | sharpe_p05 | sharpe_p95 | sharpe_diff | diff_p05 | diff_p95 | share_resamples_better |
|---|---|---|---|---|---|---|---|---|
| development | buy_hold | 0.241 | -0.250 | 0.797 | -0.062 | -0.214 | 0.093 | 0.262 |
| development | vol_sized_hold | 0.241 | -0.250 | 0.797 | 0.020 | -0.151 | 0.187 | 0.582 |
| development | sma_trend | 0.241 | -0.250 | 0.797 | 0.351 | 0.027 | 0.713 | 0.958 |
| holdout | buy_hold | 1.291 | 0.267 | 2.282 | 0.242 | -0.026 | 0.487 | 0.931 |
| holdout | vol_sized_hold | 1.291 | 0.267 | 2.282 | 0.376 | 0.051 | 0.678 | 0.976 |
| holdout | sma_trend | 1.291 | 0.267 | 2.282 | 0.384 | -0.106 | 0.812 | 0.901 |
| full | buy_hold | 0.493 | 0.030 | 0.945 | 0.009 | -0.121 | 0.130 | 0.547 |
| full | vol_sized_hold | 0.493 | 0.030 | 0.945 | 0.063 | -0.100 | 0.216 | 0.735 |
| full | sma_trend | 0.493 | 0.030 | 0.945 | 0.249 | -0.045 | 0.521 | 0.916 |


## Model quality: holdout

AUC 0.5 = coin flip. Brier/log loss below their baseline (a constant forecast at the base rate) means the probabilities add information.

| ticker | model | n | auc | accuracy | base_rate | brier | brier_baseline | log_loss | log_loss_baseline |
|---|---|---|---|---|---|---|---|---|---|
| GLD | ml_all_features | 705 | 0.530 | 0.584 | 0.603 | 0.251 | 0.239 | 0.698 | 0.672 |
| GLD | ml_technical_only | 705 | 0.561 | 0.535 | 0.603 | 0.251 | 0.239 | 0.696 | 0.672 |
| SLV | ml_all_features | 705 | 0.454 | 0.487 | 0.563 | 0.264 | 0.246 | 0.723 | 0.685 |
| SLV | ml_technical_only | 705 | 0.446 | 0.472 | 0.563 | 0.267 | 0.246 | 0.730 | 0.685 |
| GDX | ml_all_features | 705 | 0.528 | 0.543 | 0.559 | 0.261 | 0.247 | 0.722 | 0.686 |
| GDX | ml_technical_only | 705 | 0.514 | 0.498 | 0.559 | 0.269 | 0.247 | 0.743 | 0.686 |
| NEM | ml_all_features | 705 | 0.506 | 0.484 | 0.570 | 0.264 | 0.245 | 0.725 | 0.683 |
| NEM | ml_technical_only | 705 | 0.512 | 0.513 | 0.570 | 0.267 | 0.245 | 0.731 | 0.683 |
| AEM | ml_all_features | 705 | 0.516 | 0.525 | 0.569 | 0.260 | 0.245 | 0.718 | 0.684 |
| AEM | ml_technical_only | 705 | 0.530 | 0.529 | 0.569 | 0.256 | 0.245 | 0.707 | 0.684 |
| WPM | ml_all_features | 705 | 0.530 | 0.559 | 0.557 | 0.254 | 0.247 | 0.704 | 0.687 |
| WPM | ml_technical_only | 705 | 0.558 | 0.526 | 0.557 | 0.250 | 0.247 | 0.694 | 0.687 |


## By ticker: holdout

| ticker | strategy | cagr | sharpe | max_drawdown | trades |
|---|---|---|---|---|---|
| GLD | strategy | 27.2% | 1.469 | -14.7% | 0 |
| GLD | buy_hold | 26.4% | 0.981 | -26.4% | 0 |
| GLD | vol_sized_hold | 21.2% | 0.916 | -22.7% | 0 |
| SLV | strategy | 22.8% | 1.179 | -13.7% | 0 |
| SLV | buy_hold | 31.7% | 0.758 | -55.5% | 0 |
| SLV | vol_sized_hold | 19.3% | 0.594 | -44.6% | 0 |
| GDX | strategy | 20.4% | 1.050 | -13.4% | 0 |
| GDX | buy_hold | 42.4% | 0.968 | -38.9% | 0 |
| GDX | vol_sized_hold | 24.4% | 0.816 | -28.8% | 0 |
| NEM | strategy | 21.5% | 1.056 | -17.0% | 0 |
| NEM | buy_hold | 45.0% | 0.996 | -36.6% | 0 |
| NEM | vol_sized_hold | 30.4% | 0.914 | -25.5% | 0 |
| AEM | strategy | 24.7% | 1.270 | -18.0% | 0 |
| AEM | buy_hold | 54.4% | 1.195 | -45.8% | 0 |
| AEM | vol_sized_hold | 35.5% | 1.050 | -38.1% | 0 |
| WPM | strategy | 20.4% | 1.038 | -12.4% | 0 |
| WPM | buy_hold | 40.0% | 0.938 | -37.4% | 0 |
| WPM | vol_sized_hold | 27.2% | 0.831 | -30.1% | 0 |


![portfolio_equity.png](portfolio_equity.png)


![equity_by_ticker.png](equity_by_ticker.png)


![cost_sensitivity.png](cost_sensitivity.png)


![calibration.png](calibration.png)


![fold_auc.png](fold_auc.png)


![feature_importance.png](feature_importance.png)


![regimes.png](regimes.png)


## Data warnings during this run

* `warning` CL=F: dropped 1 rows with missing/non-positive close


## Known limitations
* **Survivorship:** the universe was chosen today. Miners that failed or were acquired before today are absent.
* **Macro vintages:** FRED values are the latest revision, lagged for publication delay. Market-based series
  (TIPS yields, breakevens, T-bills) are rarely revised, but this is not a true point-in-time (ALFRED) dataset.
* **Sentiment and fundamentals** have no free point-in-time history, so they are excluded from all backtests
  and carry zero weight in live decisions by default.
* **Execution:** fills at the next open with a flat cost assumption; real spreads widen in stress and large
  orders move prices. See the cost-sensitivity chart.
* **Multiple comparisons:** several strategies and tickers are compared; the best of many will look good by chance.
