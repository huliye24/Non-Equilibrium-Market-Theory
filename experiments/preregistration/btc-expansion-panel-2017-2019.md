# BTC expansion probability panel, 2017-2019

Status: preregistered; research only; no trading permission.

## Objective and independent groups

Estimate how well causal indicators rank the probability of a future one-day
BTCUSDT range expansion. Group A is `2017-08-17T04:00:00Z` through
`2019-01-01T00:00:00Z` (2017-2018). Group B is calendar 2019. The groups are
reported separately. Group B is never used to revise Group A parameters or
definitions, and results are not pooled into a single headline score.

The target is probabilistic. No indicator is required to predict every event.
Discrimination and calibration are both measured.

Within Group A, `2017-08-17T04:00:00Z` through `2018-06-30T23:59:59Z`
is the fitting/selection prefix and `2018-07-01T00:00:00Z` through year-end is
the untouched scoring suffix. Within Group B, January through June 2019 is the
fitting/selection prefix and July through December 2019 is the untouched scoring
suffix. These cutoffs are frozen before the 20-indicator run.

## Frozen data and label

- Binance spot BTCUSDT immutable candle-v2 15-minute S3 snapshot.
- Closed, non-imputed candles only; gaps invalidate crossing windows.
- Decision timeframes: 15m, 1h, 4h.
- Expansion label: next one-day high-low range is at least `1.25` times the
  preceding one-day high-low range, excluding the decision candle from the
  future range.
- No filling, backward filling, centered windows, or future-derived scaling.

## Frozen 20-indicator panel

The list is a broad candidate benchmark, not a claim that any indicator is
profitable or uniquely suited to crypto.

1. NSE-v1 (return energy / variance)
2. NSW-v1 (spectral width around the spectral centroid)
3. Bollinger bandwidth
4. normalized ATR
5. realized volatility
6. Parkinson high-low volatility
7. Garman-Klass volatility
8. Rogers-Satchell volatility
9. Donchian channel width
10. Keltner channel width
11. RSI
12. normalized MACD histogram
13. ADX
14. Kaufman efficiency ratio
15. rate of change
16. stochastic %K
17. on-balance-volume slope
18. Chaikin money flow
19. money flow index
20. relative volume (current volume divided by the preceding-window mean)

Price-only indicators remain eligible when volume fields are absent. Volume
indicators must use the canonical base-volume field and are marked unavailable,
not replaced with synthetic values, when it is absent.

## Parameters and probability estimation

- Trailing windows: 32, 64, 128 bars, selected using training data only.
- Each raw indicator is converted to an empirical percentile using the trailing
  training distribution. Both tails are evaluated when the economic direction
  is not fixed by definition.
- Probability mapping uses training-only isotonic calibration when its sample
  and class-count requirements are met; otherwise training-only quantile-bin
  frequencies are used. The selected calibrator is frozen before scoring the
  holdout slice.
- No 2019 observation may influence a Group A transform or parameter. Group B
  starts with a warm-up prefix but is evaluated only on timestamps in 2019.

## Metrics

Primary: average precision (PR-AUC), Brier score, and calibration table by
probability decile. Secondary: ROC-AUC, precision lift at the top 10% and 20%
of scores, recall, false-positive rate, median lead bars, coverage, and event
count. Bootstrap confidence intervals use non-overlapping one-day blocks.

The report must show the unconditional expansion rate. A high apparent hit rate
without lift over that base rate is not evidence of value. Each indicator is
reported individually; any combined model is a later, separately preregistered
experiment.

## Multiple-comparison and promotion rule

All 20 results remain visible. Benjamini-Hochberg false-discovery-rate adjusted
values are reported for exploratory comparisons. No indicator is promoted from
this two-group experiment alone. A candidate is merely `REPLICATION_WORTHY` if
it has positive top-decile precision lift and better Brier score than the base
rate forecast in both groups, without relying on fewer than 30 predicted events.

## Compute and safety boundary

The CPU research node verifies S3 hashes and materializes immutable feature
inputs. The A10G GPU may batch rolling features, parameter grids, calibration,
and bootstrap scoring. CPU/GPU parity is checked on a fixed sample. Outputs are
research artifacts only. No orders, positions, PnL, leverage, credentials, or
LIVE permission are present.

