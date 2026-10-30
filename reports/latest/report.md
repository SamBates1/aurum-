# Aurum research report

**Generated:** 2026-10-30T15:11:12+00:00 · **commit:** `abbe644` · **config:** `44b1b488763f`


## Setup
* Universe: GLD, SLV, GDX, NEM, AEM, WPM. Out-of-sample period starts 2013-10-18 (after 756 training days).
* **Development:** 2013-10-18 → 2023-12-31. **Untouched holdout:** 2024-01-01 → 2026-10-30.
* Decisions at the close, filled at the next open. Costs per ticker (one-way bps): {'GLD': 3, 'SLV': 5, 'GDX': 5, 'NEM': 8, 'AEM': 10, 'WPM': 10}.
* Cash and the Sharpe risk-free rate use the 3-month T-bill, lagged 2 business days.
* All parameters were fixed in `config.yaml` before this run; nothing below was tuned on the holdout.


## Portfolio results: holdout

Equal sleeves across tickers (each capped at 20%), after costs.

| strategy | cagr | volatility | sharpe | sortino | max_drawdown | calmar | time_in_market | trades | costs_per_year |
|---|---|---|---|---|---|---|---|---|---|
| strategy | 22.3% | 13.5% | 1.243 | 1.765 | -13.5% | 1.647 | 100.0% | 0 | 0.2% |
| timing_v02 | 20.8% | 17.2% | 0.935 | 1.247 | -17.2% | 1.210 | 76.8% | 78 | 0.3% |
| buy_hold | 39.7% | 36.0% | 0.993 | 1.374 | -38.0% | 1.046 | 100.0% | 0 | 0.0% |
| vol_sized_hold | 25.4% | 25.2% | 0.857 | 1.165 | -29.5% | 0.863 | 100.0% | 0 | 0.0% |
| sma_trend | 22.0% | 19.4% | 0.902 | 1.201 | -20.0% | 1.100 | 82.3% | 39 | 0.2% |
| momentum | 12.2% | 14.8% | 0.562 | 0.721 | -22.0% | 0.554 | 33.7% | 28 | 0.1% |
| technical_only | 19.0% | 15.0% | 0.953 | 1.244 | -15.7% | 1.208 | 70.5% | 127 | 0.4% |
| ml_only | 16.8% | 7.8% | 1.488 | 2.184 | -5.5% | 3.080 | 48.5% | 181 | 0.6% |
| ml_no_macro | 15.1% | 7.0% | 1.439 | 2.141 | -5.1% | 2.948 | 42.5% | 217 | 0.7% |
| cash | 4.4% | 0.0% | – | – | 0.0% | – | 0.0% | 0 | 0.0% |


## Portfolio results: development

Equal sleeves across tickers (each capped at 20%), after costs.

| strategy | cagr | volatility | sharpe | sortino | max_drawdown | calmar | time_in_market | trades | costs_per_year |
|---|---|---|---|---|---|---|---|---|---|
| strategy | 3.4% | 11.5% | 0.241 | 0.345 | -20.8% | 0.164 | 100.0% | 0 | 0.2% |
| timing_v02 | 0.7% | 8.3% | -0.025 | -0.035 | -21.9% | 0.032 | 46.1% | 567 | 0.7% |
| buy_hold | 6.0% | 30.1% | 0.303 | 0.437 | -43.0% | 0.140 | 100.0% | 0 | 0.0% |
| vol_sized_hold | 3.4% | 14.3% | 0.221 | 0.316 | -25.8% | 0.134 | 100.0% | 0 | 0.0% |
| sma_trend | -0.2% | 9.2% | -0.110 | -0.150 | -24.7% | -0.008 | 48.6% | 325 | 0.4% |
| momentum | -0.6% | 5.8% | -0.293 | -0.388 | -15.0% | -0.041 | 24.5% | 283 | 0.3% |
| technical_only | 1.7% | 9.1% | 0.090 | 0.129 | -20.4% | 0.082 | 49.4% | 613 | 0.7% |
| ml_only | -0.5% | 6.0% | -0.256 | -0.352 | -16.8% | -0.028 | 35.6% | 957 | 1.1% |
| ml_no_macro | 0.3% | 5.8% | -0.132 | -0.184 | -19.6% | 0.016 | 36.0% | 835 | 0.9% |
| cash | 1.3% | 0.1% | – | – | -0.0% | 3522.615 | 0.0% | 0 | 0.0% |


## Uncertainty (stationary block bootstrap, 90% intervals)

Descriptive intervals, not a formal significance test. Overlapping labels and many comparisons mean a single good number can easily be luck.

| period | vs | sharpe | sharpe_p05 | sharpe_p95 | sharpe_diff | diff_p05 | diff_p95 | share_resamples_better |
|---|---|---|---|---|---|---|---|---|
| development | buy_hold | 0.241 | -0.250 | 0.797 | -0.062 | -0.214 | 0.093 | 0.262 |
| development | vol_sized_hold | 0.241 | -0.250 | 0.797 | 0.020 | -0.151 | 0.187 | 0.582 |
| development | sma_trend | 0.241 | -0.250 | 0.797 | 0.351 | 0.027 | 0.713 | 0.958 |
| holdout | buy_hold | 1.243 | 0.216 | 2.224 | 0.251 | -0.035 | 0.511 | 0.927 |
| holdout | vol_sized_hold | 1.243 | 0.216 | 2.224 | 0.386 | 0.037 | 0.700 | 0.963 |
| holdout | sma_trend | 1.243 | 0.216 | 2.224 | 0.342 | -0.156 | 0.763 | 0.860 |
| full | buy_hold | 0.482 | 0.058 | 0.907 | 0.012 | -0.113 | 0.139 | 0.566 |
| full | vol_sized_hold | 0.482 | 0.058 | 0.907 | 0.069 | -0.083 | 0.237 | 0.765 |
| full | sma_trend | 0.482 | 0.058 | 0.907 | 0.239 | -0.026 | 0.541 | 0.930 |


## Model quality: holdout

AUC 0.5 = coin flip. Brier/log loss below their baseline (a constant forecast at the base rate) means the probabilities add information.

| ticker | model | n | auc | accuracy | base_rate | brier | brier_baseline | log_loss | log_loss_baseline |
|---|---|---|---|---|---|---|---|---|---|
| GLD | ml_all_features | 706 | 0.528 | 0.584 | 0.602 | 0.252 | 0.240 | 0.699 | 0.672 |
| GLD | ml_technical_only | 706 | 0.559 | 0.534 | 0.602 | 0.251 | 0.240 | 0.696 | 0.672 |
| SLV | ml_all_features | 706 | 0.453 | 0.486 | 0.562 | 0.264 | 0.246 | 0.724 | 0.685 |
| SLV | ml_technical_only | 706 | 0.444 | 0.472 | 0.562 | 0.268 | 0.246 | 0.730 | 0.685 |
| GDX | ml_all_features | 706 | 0.527 | 0.542 | 0.558 | 0.262 | 0.247 | 0.723 | 0.686 |
| GDX | ml_technical_only | 706 | 0.515 | 0.493 | 0.558 | 0.269 | 0.247 | 0.743 | 0.686 |
| NEM | ml_all_features | 706 | 0.508 | 0.487 | 0.569 | 0.264 | 0.245 | 0.724 | 0.683 |
| NEM | ml_technical_only | 706 | 0.513 | 0.514 | 0.569 | 0.267 | 0.245 | 0.732 | 0.683 |
| AEM | ml_all_features | 706 | 0.518 | 0.521 | 0.568 | 0.260 | 0.245 | 0.718 | 0.684 |
| AEM | ml_technical_only | 706 | 0.525 | 0.528 | 0.568 | 0.257 | 0.245 | 0.709 | 0.684 |
| WPM | ml_all_features | 706 | 0.526 | 0.554 | 0.557 | 0.255 | 0.247 | 0.706 | 0.687 |
| WPM | ml_technical_only | 706 | 0.553 | 0.523 | 0.557 | 0.251 | 0.247 | 0.695 | 0.687 |


## By ticker: holdout

| ticker | strategy | cagr | sharpe | max_drawdown | trades |
|---|---|---|---|---|---|
| GLD | strategy | 26.4% | 1.420 | -15.3% | 0 |
| GLD | buy_hold | 25.1% | 0.932 | -27.7% | 0 |
| GLD | vol_sized_hold | 20.2% | 0.868 | -23.7% | 0 |
| SLV | strategy | 22.1% | 1.134 | -15.2% | 0 |
| SLV | buy_hold | 29.2% | 0.714 | -57.7% | 0 |
| SLV | vol_sized_hold | 17.9% | 0.554 | -46.4% | 0 |
| GDX | strategy | 19.8% | 1.014 | -13.4% | 0 |
| GDX | buy_hold | 39.9% | 0.925 | -38.9% | 0 |
| GDX | vol_sized_hold | 23.0% | 0.770 | -28.8% | 0 |
| NEM | strategy | 20.8% | 1.018 | -17.0% | 0 |
| NEM | buy_hold | 42.6% | 0.954 | -36.6% | 0 |
| NEM | vol_sized_hold | 28.7% | 0.867 | -25.5% | 0 |
| AEM | strategy | 23.8% | 1.221 | -18.0% | 0 |
| AEM | buy_hold | 50.3% | 1.123 | -45.8% | 0 |
| AEM | vol_sized_hold | 32.7% | 0.975 | -38.1% | 0 |
| WPM | strategy | 19.8% | 1.003 | -12.4% | 0 |
| WPM | buy_hold | 37.6% | 0.894 | -37.4% | 0 |
| WPM | vol_sized_hold | 25.6% | 0.785 | -30.1% | 0 |


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
