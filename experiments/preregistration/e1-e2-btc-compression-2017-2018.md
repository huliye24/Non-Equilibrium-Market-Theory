# E1-E2 BTC compression pilot, 2017-2018

Status: preregistered pilot; research only; no trading permission.

## Question

Does the causal NEMT spectral-width observable identify a future price expansion
better than two simple volatility-compression baselines: Bollinger bandwidth and
normalized ATR?

This pilot tests the measurement claim, not strategy profitability. A negative or
null result is a valid result.

## Frozen data and provenance

- Venue/market/symbol: Binance spot BTCUSDT.
- Source: the immutable Emergenzix S3 candle-v2 snapshot selected by an explicit
  manifest key at run time. The report must record the manifest snapshot ID and
  SHA-256 of every Parquet object read.
- Decision timeframes: 15m, 1h, 4h.
- Observation interval: 2017-08-17 through 2018-12-31 UTC.
- Only closed, non-imputed, canonical 15-minute observations are eligible.
- A rolling feature, aggregation bucket, or forward label that crosses a source
  gap is excluded. Missing candles are never filled.

## Causal observables

At bar `t`, every observable uses bars at or before `t` only.

1. Spectral width: normalized second moment of the positive-frequency power
   spectrum of demeaned log returns in the trailing window.
2. Bollinger bandwidth: four trailing population standard deviations divided by
   the trailing mean close.
3. Normalized ATR: trailing mean true range divided by the current close.

The spectral measure is amplitude-normalized. Therefore it may measure frequency
concentration rather than low-volatility compression; the experiment is allowed
to falsify the proposed interpretation.

## Expansion label

Horizons are one day: 96 bars at 15m, 24 bars at 1h, and 6 bars at 4h. An
observation is positive when the high-low range over the next horizon, excluding
the decision bar, is at least 1.25 times the high-low range over the trailing
horizon, including the decision bar. Both ranges require a complete candle grid.

Revision note: the first pipeline diagnostic used `future range >= 3 * current
ATR`. It produced a 98.5%-99.6% positive prevalence on 15m and was rejected as a
saturated, non-discriminating label before interpreting any observable. The raw
diagnostic report SHA-256 was
`846561dfed4fcb91580dc1d208ec69d39b9403e81a02861132520cb4823b7f87`.
The range-ratio label above was frozen before the corrected run.

## Pilot walk-forward protocol

- Anchor: 2017-09-01 UTC.
- Training: 6 calendar months.
- Parameter selection: 2 calendar months.
- Unseen test: 2 calendar months.
- Step: 2 calendar months.
- Data end (exclusive): 2019-01-01 UTC.

This shortened protocol exists because the pilot history cannot support the
formal 18+3+3 protocol. No pilot result may be described as formal validation.

Candidate trailing windows are 32, 64, and 128 bars. Candidate lower-tail
thresholds are the 10th, 20th, and 30th percentiles estimated from training data
only. A signal is the first crossing from above to at-or-below the frozen
threshold. Selection maximizes selection-period F1, with precision and then a
canonical parameter ordering as deterministic tie-breakers.

## Reported metrics

For every observable, timeframe, and unseen window: event count, precision,
recall, F1, base expansion rate, precision lift over the base rate, false-positive
rate, and median lead bars among true positives. Aggregate summaries report
median precision lift and the number of unseen windows with positive lift.

No return, Sharpe ratio, order, position, leverage, or PnL is part of this pilot.

## Pilot interpretation

- Pipeline success: the pinned snapshot is verified, all three timeframes run,
  causal and gap tests pass, and a deterministic report is produced.
- Promising evidence: spectral width has positive precision lift in a majority of
  unseen windows and its median lift exceeds both baselines.
- Null evidence: spectral width does not exceed both baselines.
- Any conclusion remains exploratory until repeated under 18+3+3 and additional
  assets/market regimes.

