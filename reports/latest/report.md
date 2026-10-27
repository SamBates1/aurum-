# Aurum research report

**Generated:** 2026-10-27T18:49:17+00:00 · **commit:** `9cfc518` · **config:** `2c9c656d1a4b`


## Setup
* Universe: GLD, SLV, GDX, NEM, AEM, WPM. Out-of-sample period starts 2013-10-18 (after 756 training days).
* **Development:** 2013-10-18 → 2023-12-31. **Untouched holdout:** 2024-01-01 → 2026-10-27.
* Decisions at the close, filled at the next open. Costs per ticker (one-way bps): {'GLD': 3, 'SLV': 5, 'GDX': 5, 'NEM': 8, 'AEM': 10, 'WPM': 10}.
* Cash and the Sharpe risk-free rate use the 3-month T-bill, lagged 2 business days.
* All parameters were fixed in `config.yaml` before this run; nothing below was tuned on the holdout.


## Portfolio results: holdout

Equal sleeves across tickers (each capped at 20%), after costs.

| strategy | cagr | volatility | sharpe | sortino | max_drawdown | calmar | time_in_market | trades | costs_per_year |
|---|---|---|---|---|---|---|---|---|---|
| strategy | 20.8% | 17.2% | 0.937 | 1.250 | -17.2% | 1.215 | 77.1% | 78 | 0.3% |
| buy_hold | 43.4% | 35.8% | 1.067 | 1.483 | -38.0% | 1.143 | 100.0% | 0 | 0.0% |
| vol_sized_hold | 27.8% | 25.1% | 0.934 | 1.274 | -29.5% | 0.942 | 100.0% | 0 | 0.0% |
| sma_trend | 22.2% | 19.5% | 0.909 | 1.211 | -20.0% | 1.110 | 82.6% | 38 | 0.2% |
| momentum | 13.6% | 14.7% | 0.653 | 0.841 | -22.0% | 0.620 | 33.6% | 27 | 0.1% |
| technical_only | 19.1% | 15.0% | 0.955 | 1.247 | -15.7% | 1.212 | 70.8% | 127 | 0.4% |
| ml_only | 18.1% | 7.9% | 1.611 | 2.394 | -5.2% | 3.514 | 48.9% | 182 | 0.6% |
| ml_no_macro | 15.0% | 7.0% | 1.410 | 2.090 | -5.4% | 2.747 | 43.2% | 214 | 0.7% |
| cash | 4.4% | 0.0% | – | – | 0.0% | – | 0.0% | 0 | 0.0% |


## Portfolio results: development

Equal sleeves across tickers (each capped at 20%), after costs.

| strategy | cagr | volatility | sharpe | sortino | max_drawdown | calmar | time_in_market | trades | costs_per_year |
|---|---|---|---|---|---|---|---|---|---|
| strategy | 0.9% | 8.4% | -0.000 | -0.001 | -21.5% | 0.042 | 46.3% | 566 | 0.7% |
| buy_hold | 6.0% | 30.1% | 0.303 | 0.437 | -43.0% | 0.140 | 100.0% | 0 | 0.0% |
| vol_sized_hold | 3.4% | 14.3% | 0.221 | 0.316 | -25.8% | 0.134 | 100.0% | 0 | 0.0% |
| sma_trend | -0.2% | 9.2% | -0.110 | -0.150 | -24.7% | -0.008 | 48.6% | 325 | 0.4% |
| momentum | -0.6% | 5.8% | -0.293 | -0.388 | -15.0% | -0.041 | 24.5% | 283 | 0.3% |
| technical_only | 1.7% | 9.1% | 0.090 | 0.129 | -20.4% | 0.082 | 49.4% | 613 | 0.7% |
| ml_only | -0.4% | 6.0% | -0.239 | -0.329 | -16.7% | -0.022 | 35.6% | 957 | 1.1% |
| ml_no_macro | 0.5% | 5.8% | -0.102 | -0.141 | -20.7% | 0.024 | 36.2% | 834 | 0.9% |
| cash | 1.3% | 0.1% | – | – | -0.0% | 3522.615 | 0.0% | 0 | 0.0% |


## Uncertainty (stationary block bootstrap, 90% intervals)

Descriptive intervals, not a formal significance test. Overlapping labels and many comparisons mean a single good number can easily be luck.

| period | vs | sharpe | sharpe_p05 | sharpe_p95 | sharpe_diff | diff_p05 | diff_p95 | share_resamples_better |
|---|---|---|---|---|---|---|---|---|
| development | buy_hold | -0.000 | -0.539 | 0.566 | -0.303 | -0.649 | 0.021 | 0.058 |
| development | vol_sized_hold | -0.000 | -0.539 | 0.566 | -0.222 | -0.559 | 0.092 | 0.109 |
| development | sma_trend | -0.000 | -0.539 | 0.566 | 0.110 | -0.209 | 0.421 | 0.730 |
| holdout | buy_hold | 0.937 | 0.123 | 1.807 | -0.130 | -0.490 | 0.240 | 0.257 |
| holdout | vol_sized_hold | 0.937 | 0.123 | 1.807 | 0.004 | -0.338 | 0.368 | 0.474 |
| holdout | sma_trend | 0.937 | 0.123 | 1.807 | 0.029 | -0.187 | 0.251 | 0.567 |
| full | buy_hold | 0.315 | -0.119 | 0.766 | -0.172 | -0.434 | 0.095 | 0.158 |
| full | vol_sized_hold | 0.315 | -0.119 | 0.766 | -0.120 | -0.347 | 0.113 | 0.207 |
| full | sma_trend | 0.315 | -0.119 | 0.766 | 0.071 | -0.135 | 0.284 | 0.711 |


## Model quality: holdout

AUC 0.5 = coin flip. Brier/log loss below their baseline (a constant forecast at the base rate) means the probabilities add information.

| ticker | model | n | auc | accuracy | base_rate | brier | brier_baseline | log_loss | log_loss_baseline |
|---|---|---|---|---|---|---|---|---|---|
| GLD | ml_all_features | 703 | 0.533 | 0.586 | 0.605 | 0.250 | 0.239 | 0.696 | 0.671 |
| GLD | ml_technical_only | 703 | 0.562 | 0.536 | 0.605 | 0.251 | 0.239 | 0.695 | 0.671 |
| SLV | ml_all_features | 703 | 0.457 | 0.488 | 0.565 | 0.263 | 0.246 | 0.721 | 0.685 |
| SLV | ml_technical_only | 703 | 0.448 | 0.474 | 0.565 | 0.267 | 0.246 | 0.728 | 0.685 |
| GDX | ml_all_features | 703 | 0.530 | 0.545 | 0.560 | 0.261 | 0.246 | 0.721 | 0.686 |
| GDX | ml_technical_only | 703 | 0.518 | 0.504 | 0.560 | 0.269 | 0.246 | 0.742 | 0.686 |
| NEM | ml_all_features | 703 | 0.508 | 0.485 | 0.572 | 0.264 | 0.245 | 0.724 | 0.683 |
| NEM | ml_technical_only | 703 | 0.511 | 0.509 | 0.572 | 0.267 | 0.245 | 0.732 | 0.683 |
| AEM | ml_all_features | 703 | 0.516 | 0.526 | 0.570 | 0.260 | 0.245 | 0.717 | 0.683 |
| AEM | ml_technical_only | 703 | 0.528 | 0.528 | 0.570 | 0.256 | 0.245 | 0.708 | 0.683 |
| WPM | ml_all_features | 703 | 0.531 | 0.560 | 0.559 | 0.253 | 0.247 | 0.703 | 0.686 |
| WPM | ml_technical_only | 703 | 0.552 | 0.522 | 0.559 | 0.251 | 0.247 | 0.695 | 0.686 |


## By ticker: holdout

| ticker | strategy | cagr | sharpe | max_drawdown | trades |
|---|---|---|---|---|---|
| GLD | strategy | 25.6% | 1.071 | -19.2% | 17 |
| GLD | buy_hold | 26.8% | 0.996 | -26.4% | 0 |
| GLD | vol_sized_hold | 21.6% | 0.932 | -22.7% | 0 |
| SLV | strategy | 25.1% | 0.783 | -35.3% | 12 |
| SLV | buy_hold | 33.7% | 0.793 | -53.9% | 0 |
| SLV | vol_sized_hold | 20.5% | 0.626 | -43.3% | 0 |
| GDX | strategy | 21.5% | 1.004 | -15.5% | 17 |
| GDX | buy_hold | 43.4% | 0.986 | -38.9% | 0 |
| GDX | vol_sized_hold | 25.0% | 0.834 | -28.8% | 0 |
| NEM | strategy | 13.3% | 0.549 | -16.2% | 10 |
| NEM | buy_hold | 45.6% | 1.005 | -36.6% | 0 |
| NEM | vol_sized_hold | 30.8% | 0.924 | -25.5% | 0 |
| AEM | strategy | 23.4% | 0.919 | -23.3% | 14 |
| AEM | buy_hold | 55.4% | 1.212 | -45.8% | 0 |
| AEM | vol_sized_hold | 36.1% | 1.068 | -38.1% | 0 |
| WPM | strategy | 16.8% | 0.762 | -15.7% | 8 |
| WPM | buy_hold | 40.9% | 0.955 | -37.4% | 0 |
| WPM | vol_sized_hold | 27.8% | 0.848 | -30.1% | 0 |


![portfolio_equity.png](portfolio_equity.png)


![equity_by_ticker.png](equity_by_ticker.png)


![cost_sensitivity.png](cost_sensitivity.png)


![calibration.png](calibration.png)


![fold_auc.png](fold_auc.png)


![feature_importance.png](feature_importance.png)


![regimes.png](regimes.png)


## Known limitations
* **Survivorship:** the universe was chosen today. Miners that failed or were acquired before today are absent.
* **Macro vintages:** FRED values are the latest revision, lagged for publication delay. Market-based series
  (TIPS yields, breakevens, T-bills) are rarely revised, but this is not a true point-in-time (ALFRED) dataset.
* **Sentiment and fundamentals** have no free point-in-time history, so they are excluded from all backtests
  and carry zero weight in live decisions by default.
* **Execution:** fills at the next open with a flat cost assumption; real spreads widen in stress and large
  orders move prices. See the cost-sensitivity chart.
* **Multiple comparisons:** several strategies and tickers are compared; the best of many will look good by chance.
