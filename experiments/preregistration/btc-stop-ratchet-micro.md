# BTC 4h rolling-position and stop-ratchet micro experiment

Status: frozen before execution. Research only; no order permission.

## Question and arms

Using the same causal BTCUSDT 4h Donchian opportunity, does decreasing
pyramiding add value, and does a stop that can only tighten add value beyond
pyramiding?

- A: no pyramiding, static 2N stop;
- B: decreasing pyramiding, static 2N stop;
- C: decreasing pyramiding, parameterized stop ratchet.

Partial exits are deliberately excluded. They require a later fourth arm.

## Frozen data and cycle

- immutable Binance BTCUSDT 15m snapshot
  `60f9df4c93b56098acf1ab73ac8cf75e41e3b76f257f8e3660f6b502d9a2b2b9`;
- deterministic complete UTC 4h aggregation;
- first 18+3+3 fold: train/warm-up 2017-09-01--2019-03-01, selection
  2019-03-01--2019-06-01, unseen test 2019-06-01--2019-09-01;
- the test interval is read only after the C parameters are frozen.

## Shared trading rules

- long-only spot model; no short, leverage, funding, or liquidation claim;
- entry: completed close above the previous 120-bar Donchian high;
- exit: completed close below the previous 60-bar Donchian low;
- signals execute at the next bar open with 5 bps fee and 2 bps adverse
  slippage per side;
- `N = SMA(TR, 120)` using only completed bars;
- initial stop is entry minus `2N`; gap-through stop fills from the adverse open;
- starting equity 10,000 USDT and maximum planned stop risk 1%.

A allocates the full risk budget initially. B and C reserve the same maximum
budget across weights `1 : 0.5 : 0.25`, adding at `+1R` and `+2R`. This avoids
quietly giving pyramiding a larger planned loss budget.

## C parameter grid

- ATR trail multiple: 1.5, 2.0, 2.5, 3.0, 3.5;
- structure lookback: 5, 10, 20, 30, 40 bars;
- break-even activation: 0.5R, 1.0R, 1.5R, 2.0R;
- cost buffer: 0, 10, 20, 30 bps;
- update cadence: every 1 or 4 completed bars.

At an eligible close, the next stop is the maximum of the existing stop,
break-even candidate, highest-close-minus-ATR candidate, and prior completed
structure low. Any candidate at or above current close is ignored. The ratchet
can never loosen. The selection winner maximizes net return minus maximum
drawdown, with deterministic parameter ordering for ties.

## Acceptance report

For selection and unseen test, report net return, maximum drawdown, trades,
average net R, additions, stop tightenings, and maximum open stop risk. Report
`B-A` and `C-B`; do not call either increment causal proof from one fold.
