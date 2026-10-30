# BTC 4h stop-ratchet micro experiment result

Status: exploratory one-fold result; not strategy promotion or order permission.

## Provenance

- code commit: `9a256d1`;
- immutable snapshot: `60f9df4c93b56098acf1ab73ac8cf75e41e3b76f257f8e3660f6b502d9a2b2b9`;
- valid artifact: `s3://emergenzix-research-382309211832-cn-northwest-1-an/experiments/btc-stop-ratchet-micro/20261030-v2/report.json`;
- report SHA-256: `a631cca59f05fa71b6bdb935206d9c7c17bf272c4dc5cb5a009921e0a0847b50`;
- CPU wall time: 34.28 seconds; 800 C-arm parameter candidates.

The earlier S3 `20261030-v1` artifact is invalid for inference: static-stop
pyramiding could exceed the common planned risk budget. It is retained only as
an audit record and was replaced methodologically, not overwritten, by v2.

## Frozen C winner from selection

- ATR multiple 3.5;
- structure lookback 20 completed 4h bars;
- break-even activation 1R;
- cost buffer 0 bps;
- stop update every 4 completed bars.

## Unseen test: 2019-06-01 through 2019-09-01 UTC

| Arm | Net return | Max drawdown | Trades | Average net R | Adds | Tightenings | Max observed open stop risk/equity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A static, no pyramid | -1.04% | 10.97% | 3 | -0.350 | 0 | 0 | 0.983% |
| B static + pyramid | -1.07% | 9.12% | 3 | -0.637 | 3 | 0 | 1.008% |
| C ratchet + pyramid | +7.83% | 2.53% | 3 | +4.757 | 3 | 9 | 0.993% |

- `B-A`: -0.03 percentage-point return; -1.85 percentage-point drawdown.
- `C-B`: +8.90 percentage-point return; -6.59 percentage-point drawdown.

The add-time stop-risk cap is 1% of then-current equity. B's later observed
1.008% ratio is denominator drift after the decision, not an add-time cap
override. A future engine should report both decision-time budget compliance
and subsequent mark-to-market ratio drift explicitly.

## Interpretation limit

This is one three-month unseen slice with only three completed trades per arm.
The positive C result is driven materially by one large trend and is not enough
to establish a stable benefit. It does show that the event ordering, stop
ratchet, parameter selection, risk cap, and A/B/C reporting pipeline work. The
next valid question is replication over all 18+3+3 folds, not promotion of the
selected 3.5 ATR parameter. Partial exits were not tested.
