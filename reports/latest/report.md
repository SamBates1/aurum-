# Aurum research report

**Generated:** 2026-10-29T13:35:44+00:00 · **commit:** `c254cd8` · **config:** `0941fb0217c0`


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
| strategy | 23.1% | 13.4% | 1.296 | 1.844 | -13.5% | 1.707 | 100.0% | 0 | 0.2% |
| timing_v02 | 20.8% | 17.2% | 0.937 | 1.250 | -17.1% | 1.215 | 76.9% | 78 | 0.3% |
| buy_hold | 42.7% | 35.8% | 1.055 | 1.465 | -38.0% | 1.126 | 100.0% | 0 | 0.0% |
| vol_sized_hold | 27.4% | 25.1% | 0.920 | 1.255 | -29.5% | 0.927 | 100.0% | 0 | 0.0% |
| sma_trend | 22.1% | 19.5% | 0.907 | 1.208 | -20.0% | 1.106 | 82.4% | 38 | 0.2% |
| momentum | 13.3% | 14.7% | 0.634 | 0.816 | -22.0% | 0.606 | 33.7% | 27 | 0.1% |
| technical_only | 19.0% | 15.0% | 0.954 | 1.245 | -15.7% | 1.210 | 70.6% | 127 | 0.4% |
| ml_only | 16.4% | 7.7% | 1.454 | 2.124 | -5.1% | 3.219 | 48.1% | 179 | 0.6% |
| ml_no_macro | 14.6% | 6.9% | 1.390 | 2.059 | -5.1% | 2.868 | 42.7% | 215 | 0.7% |
| cash | 4.4% | 0.0% | – | – | 0.0% | – | 0.0% | 0 | 0.0% |


## Portfolio results: development

Equal sleeves across tickers (each capped at 20%), after costs.

| strategy | cagr | volatility | sharpe | sortino | max_drawdown | calmar | time_in_market | trades | costs_per_year |
|---|---|---|---|---|---|---|---|---|---|
| strategy | 3.4% | 11.5% | 0.241 | 0.345 | -20.8% | 0.164 | 100.0% | 0 | 0.2% |
| timing_v02 | 1.0% | 8.3% | 0.007 | 0.010 | -20.9% | 0.046 | 46.1% | 565 | 0.7% |
| buy_hold | 6.0% | 30.1% | 0.303 | 0.437 | -43.0% | 0.140 | 100.0% | 0 | 0.0% |
| vol_sized_hold | 3.4% | 14.3% | 0.221 | 0.316 | -25.8% | 0.134 | 100.0% | 0 | 0.0% |
| sma_trend | -0.2% | 9.2% | -0.110 | -0.150 | -24.7% | -0.008 | 48.6% | 325 | 0.4% |
| momentum | -0.6% | 5.8% | -0.293 | -0.388 | -15.0% | -0.041 | 24.5% | 283 | 0.3% |
| technical_only | 1.7% | 9.1% | 0.092 | 0.131 | -20.4% | 0.083 | 49.4% | 612 | 0.7% |
| ml_only | -0.4% | 6.0% | -0.250 | -0.345 | -16.8% | -0.025 | 35.5% | 953 | 1.1% |
| ml_no_macro | 0.6% | 5.8% | -0.090 | -0.125 | -20.5% | 0.027 | 36.0% | 818 | 0.9% |
| cash | 1.3% | 0.1% | – | – | -0.0% | 3522.615 | 0.0% | 0 | 0.0% |


## Uncertainty (stationary block bootstrap, 90% intervals)

Descriptive intervals, not a formal significance test. Overlapping labels and many comparisons mean a single good number can easily be luck.

| period | vs | sharpe | sharpe_p05 | sharpe_p95 | sharpe_diff | diff_p05 | diff_p95 | share_resamples_better |
|---|---|---|---|---|---|---|---|---|
| development | buy_hold | 0.241 | -0.250 | 0.797 | -0.062 | -0.214 | 0.093 | 0.262 |
| development | vol_sized_hold | 0.241 | -0.250 | 0.797 | 0.020 | -0.151 | 0.187 | 0.582 |
| development | sma_trend | 0.241 | -0.250 | 0.797 | 0.351 | 0.027 | 0.713 | 0.958 |
| holdout | buy_hold | 1.296 | 0.279 | 2.288 | 0.241 | -0.027 | 0.487 | 0.931 |
| holdout | vol_sized_hold | 1.296 | 0.279 | 2.288 | 0.376 | 0.050 | 0.678 | 0.976 |
| holdout | sma_trend | 1.296 | 0.279 | 2.288 | 0.389 | -0.102 | 0.818 | 0.906 |
| full | buy_hold | 0.494 | 0.030 | 0.946 | 0.009 | -0.121 | 0.130 | 0.545 |
| full | vol_sized_hold | 0.494 | 0.030 | 0.946 | 0.062 | -0.101 | 0.215 | 0.734 |
| full | sma_trend | 0.494 | 0.030 | 0.946 | 0.250 | -0.043 | 0.523 | 0.918 |


## Model quality: holdout

AUC 0.5 = coin flip. Brier/log loss below their baseline (a constant forecast at the base rate) means the probabilities add information.

| ticker | model | n | auc | accuracy | base_rate | brier | brier_baseline | log_loss | log_loss_baseline |
|---|---|---|---|---|---|---|---|---|---|
| GLD | ml_all_features | 705 | 0.533 | 0.586 | 0.604 | 0.250 | 0.239 | 0.696 | 0.671 |
| GLD | ml_technical_only | 705 | 0.562 | 0.536 | 0.604 | 0.251 | 0.239 | 0.695 | 0.671 |
| SLV | ml_all_features | 705 | 0.454 | 0.487 | 0.563 | 0.264 | 0.246 | 0.723 | 0.685 |
| SLV | ml_technical_only | 705 | 0.446 | 0.472 | 0.563 | 0.267 | 0.246 | 0.730 | 0.685 |
| GDX | ml_all_features | 705 | 0.526 | 0.542 | 0.559 | 0.262 | 0.247 | 0.723 | 0.686 |
| GDX | ml_technical_only | 705 | 0.515 | 0.498 | 0.559 | 0.269 | 0.247 | 0.743 | 0.686 |
| NEM | ml_all_features | 705 | 0.506 | 0.485 | 0.570 | 0.264 | 0.245 | 0.725 | 0.683 |
| NEM | ml_technical_only | 705 | 0.511 | 0.518 | 0.570 | 0.267 | 0.245 | 0.732 | 0.683 |
| AEM | ml_all_features | 705 | 0.518 | 0.523 | 0.570 | 0.260 | 0.245 | 0.717 | 0.683 |
| AEM | ml_technical_only | 705 | 0.526 | 0.530 | 0.570 | 0.257 | 0.245 | 0.709 | 0.683 |
| WPM | ml_all_features | 705 | 0.532 | 0.563 | 0.557 | 0.254 | 0.247 | 0.704 | 0.687 |
| WPM | ml_technical_only | 705 | 0.554 | 0.521 | 0.557 | 0.251 | 0.247 | 0.695 | 0.687 |


## By ticker: holdout

| ticker | strategy | cagr | sharpe | max_drawdown | trades |
|---|---|---|---|---|---|
| GLD | strategy | 27.3% | 1.473 | -14.7% | 0 |
| GLD | buy_hold | 26.5% | 0.985 | -26.4% | 0 |
| GLD | vol_sized_hold | 21.3% | 0.920 | -22.7% | 0 |
| SLV | strategy | 22.9% | 1.185 | -13.5% | 0 |
| SLV | buy_hold | 32.0% | 0.763 | -55.2% | 0 |
| SLV | vol_sized_hold | 19.5% | 0.599 | -44.3% | 0 |
| GDX | strategy | 20.4% | 1.053 | -13.4% | 0 |
| GDX | buy_hold | 42.5% | 0.972 | -38.9% | 0 |
| GDX | vol_sized_hold | 24.5% | 0.819 | -28.8% | 0 |
| NEM | strategy | 21.5% | 1.060 | -17.0% | 0 |
| NEM | buy_hold | 45.2% | 1.000 | -36.6% | 0 |
| NEM | vol_sized_hold | 30.6% | 0.918 | -25.5% | 0 |
| AEM | strategy | 24.8% | 1.278 | -18.0% | 0 |
| AEM | buy_hold | 54.9% | 1.204 | -45.8% | 0 |
| AEM | vol_sized_hold | 35.8% | 1.059 | -38.1% | 0 |
| WPM | strategy | 20.5% | 1.040 | -12.4% | 0 |
| WPM | buy_hold | 40.1% | 0.940 | -37.4% | 0 |
| WPM | vol_sized_hold | 27.3% | 0.833 | -30.1% | 0 |


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
