# BTC 20-indicator expansion probability panel

Status: first cloud run complete; exploratory; statistical acceptance pending.

## Reproduction identity

- Manifest snapshot: `60f9df4c93b56098acf1ab73ac8cf75e41e3b76f257f8e3660f6b502d9a2b2b9`.
- Eligible source rows extracted: 82,725 Binance BTCUSDT 15-minute candles.
- Verified Parquet objects: 29 (2017-08 through 2019-12).
- Matrix: 2 chronological groups × 3 timeframes × 20 indicators = 120 rows.
- GPU: NVIDIA A10G, CuPy batched FFT for NSW; report SHA-256
  `40f19933335f5e2f7dc7ea3da11483b44b4a40a335c5c025a655db120c1bf3a6`.
- Independent NumPy rerun report SHA-256:
  `5f0dfff9a73e853cb13bc0f5e2a3c36b76b8231619f5739b52574358713500a4`.
- CPU/GPU comparison: identical parameter choices and maximum metric absolute
  difference `0.0`.
- Local tests: 2/2 causal/panel tests passed.

## Leading unseen results

The figures below are probability-ranking results, not trades or returns.

| Group | Timeframe | Highest PR-AUC | PR-AUC | Base rate | Top-decile lift |
| --- | --- | --- | ---: | ---: | ---: |
| 2017-2018 | 15m | Bollinger bandwidth | 0.53 | 0.331 | +0.27 |
| 2017-2018 | 1h | Bollinger bandwidth | 0.53 | 0.330 | +0.30 |
| 2017-2018 | 4h | NSE-v1 | 0.43 | 0.331 | +0.09 |
| 2019 | 15m | Donchian width | 0.62 | 0.343 | +0.44 |
| 2019 | 1h | Donchian width | 0.62 | 0.344 | +0.44 |
| 2019 | 4h | NSE-v1 | 0.46 | 0.342 | +0.20 |

NSE-v1 and realized volatility have the same ranking in this run because NSE-v1
is the return variance and realized volatility is its square root. This is not
independent evidence from two distinct factors. NSW-v1 was not the leading
indicator in any group/timeframe.

## Interpretation boundary

The run establishes that the data path, 20-indicator calculation, chronological
selection, probability scoring, GPU execution and CPU parity work end to end.
It does not yet satisfy the complete preregistered statistical report: block
bootstrap intervals, multiple-comparison adjustment and median event lead time
remain to be added. No candidate is promoted until those fields are complete.

Execution mode is `RESEARCH_ONLY`; `live_enabled=false`. No order, position,
leverage, fee, PnL or exchange credential is involved.
