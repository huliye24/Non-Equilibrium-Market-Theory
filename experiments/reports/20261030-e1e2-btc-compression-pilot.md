# E1-E2 BTC compression pilot: 2017-2018

Status: completed exploratory pilot; not validated; no promotion.

## Reproduction identity

- Data: Binance spot BTCUSDT candle-v2, 2017-08-17 through 2018-12-31 UTC.
- Pinned S3 snapshot: `115066e53df85f6ea0a085169d3943b9e2812dbccfd49e0ae484c7f4f54bf46f`.
- Verified monthly Parquet objects: 17.
- Canonical observations: 47,802 at 15m; 11,946 complete 1h buckets;
  2,980 complete 4h buckets.
- Corrected report SHA-256:
  `9f1ce82d38f1e02ababe98cb9d4f6a13fd56a44e534275c69e7ee78e869fe7d5`.
- Execution host: Ningxia CPU research node. GPU was not required for this
  pilot-sized matrix.
- Tests: three causal/gap/aggregation tests passed before the corrected run.

The machine-readable report is
`20261030-e1e2-btc-2017-2018-pilot.json` in this directory.

## Protocol

The pilot compared lower-tail crossings of normalized spectral width,
Bollinger bandwidth, and normalized ATR. Candidate trailing windows were 32,
64, and 128 bars; candidate training-only thresholds were the 10th, 20th, and
30th percentiles. Each window used six months of training, two months of
selection, two unseen months of testing, and a two-month step.

An expansion meant that the next one-day high-low range was at least 1.25 times
the preceding one-day high-low range. This is a measurement experiment, not a
trading backtest; it has no orders, returns, fees, leverage, or PnL.

## Corrected unseen results

| Timeframe | Observable | Positive-lift windows | Windows | Median precision lift | Events |
| --- | --- | ---: | ---: | ---: | ---: |
| 15m | Spectral width | 2 | 4 | +0.13 pp | 889 |
| 15m | Bollinger bandwidth | 1 | 4 | -9.26 pp | 223 |
| 15m | Normalized ATR | 0 | 4 | -14.39 pp | 135 |
| 1h | Spectral width | 0 | 4 | -4.62 pp | 155 |
| 1h | Bollinger bandwidth | 2 | 4 | -0.97 pp | 61 |
| 1h | Normalized ATR | 2 | 4 | -7.86 pp | 22 |
| 4h | Spectral width | 0 | 4 | -9.04 pp | 55 |
| 4h | Bollinger bandwidth | 1 | 4 | -30.05 pp | 18 |
| 4h | Normalized ATR | 0 | 4 | -32.06 pp | 6 |

`pp` means percentage points relative to the unconditional expansion rate in
the same eligible observations.

## Failed diagnostic retained

The first pipeline run labelled an expansion when the next one-day range was at
least three times the current bar ATR. That label was positive for 98.5%-99.6%
of eligible 15m observations, so it could not discriminate predictors. No
indicator conclusion was taken from it. Its report SHA-256 is preserved in the
preregistration as a failed design diagnostic rather than silently discarded.

## Interpretation

This pilot does **not** support promoting the current spectral-width definition
to the standard market-monitor chart. Its 15m result was approximately neutral,
and its 1h and 4h unseen precision lifts were negative in every window. The two
simple volatility baselines were also unstable, so the result does not establish
that spectral width is worse in every formulation; it rejects this particular
lower-tail-crossing formulation on this pilot period.

The amplitude-normalized spectral second moment describes where return power is
located in frequency, not how small the return amplitude is. Calling a low value
"compression" without a separate energy/amplitude observable is therefore not
justified by this test.

## Decision and next experiment

- Promotion: rejected.
- Standard K-line chart: do not add.
- Research-mode chart: permitted only with an `EXPERIMENTAL` label and the exact
  formula/version.
- Next test: separate spectral shape from spectral energy, then test whether
  `low energy + concentrated spectrum` improves on Bollinger bandwidth and
  normalized ATR. Freeze that formulation before running additional years.
- Formal validation remains the 18+3+3 protocol over the full history and must
  not reuse this pilot's unseen windows for further tuning claims.

