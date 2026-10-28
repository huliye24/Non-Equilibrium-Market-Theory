# Right-side entry state machine 001

Status: **IMPLEMENTED_RESEARCH_CANDIDATE**
Trading status: **not backtested, not promoted, not connected to orders**

## Research question

Can the system preserve the long right tail while avoiding the most fragile moment of a breakout by requiring the completed-bar path:

`STABILIZING → RETEST_HELD → REACCELERATION`?

This is a right-side entry hypothesis: price first proves the breakout, the market accepts the new area, a retest survives, and only then is an entry eligible at the next bar open.

## Causal state contract

All decisions use completed bars only. A point-in-time `as_of` boundary excludes every later bar.

1. `BREAKOUT_CANDIDATE`: first completed close above the predeclared breakout level.
2. `STABILIZING`: the breakout has not failed for the required number of completed bars.
3. `RETEST_HELD`: price revisits the breakout area within an ATR tolerance and closes at or above the level.
4. `REACCELERATION`: after the held retest, a completed close exceeds the post-breakout path high and volume is at least the predeclared ratio of trailing completed-bar volume.
5. `FAILED`: a completed close falls below the breakout level minus the ATR failure buffer, or confirmation takes too long.

The state machine cannot jump from breakout directly to reacceleration. A vertical move without a held retest remains unqualified.

## Risk and exit boundary

- Entry timing: next bar open after `REACCELERATION`; no same-close fill.
- Initial protective stop: `retest_low - stop_buffer × ATR`.
- Fixed profit target: none.
- Exit research remains separate; this state machine must not silently change the validated exit arm.
- Volume is confirmation of reacceleration, not a standalone direction signal.
- NEMT is not a hard gate here because experiment 003 did not prove incremental value.

## Frozen first-pass parameters

| Parameter | Default |
|---|---:|
| stability bars | 2 |
| retest tolerance | 0.25 ATR |
| failure buffer | 0.25 ATR |
| stop buffer | 0.25 ATR |
| reacceleration volume ratio | 1.20 |
| maximum confirmation window | 12 bars |

These are starting hypotheses, not optimized production settings.

## Next three experiments (not run in this change)

### Execution and delivery contract

The three experiments will run on the two existing AWS servers, not on the local workstation. Before execution, record each server's region, CPU, memory, GPU, storage, software/runtime versions and assigned role. Use the non-GPU server for data preparation, orchestration, integrity checks and report assembly; use the GPU server only for workloads that actually benefit from GPU acceleration. The same immutable code revision, frozen configuration, dataset manifest and result schema must be used across both machines.

Every run must preserve raw inputs, configuration, logs, trade-level records, aggregate results, figures and checksums in a timestamped experiment directory. Failed arms and null results must remain in the record. A run is not complete merely because a process exits successfully: the artifacts must pass data-integrity, causal-boundary and reproducibility checks.

Each experiment must produce:

1. a paper-style PDF containing method, equations, dataset and cost assumptions, figures, tables, limitations and conclusions;
2. a Markdown report containing the complete machine-readable result summary, artifact paths, commit/image identifiers and reproducibility commands;
3. a concise Telegram summary plus the PDF and Markdown report, sent through the existing Hong Kong server Telegram path only after artifact verification.

Telegram delivery is reporting only. It must not place orders, expose credentials or enable LIVE execution. The final combined report must compare all three experiments and state explicitly what was accepted, rejected or left unresolved.

### Experiment 1 — immediate breakout versus right-side confirmation

Freeze assets, data, costs, sizing, protective risk and the current winning exit. Compare immediate breakout entry with the full state path. Measure net profit, large-winner retention, entry MAE, stop distance, drawdown, stop-loss clusters, deleted-winner robustness and missed opportunity. Win rate is descriptive only.

### Experiment 2 — stabilization and retest definitions

Freeze the winning entry family from experiment 1. Compare stabilization duration, ATR retest tolerance and time expiry using walk-forward/out-of-sample evaluation. Reject definitions whose gains come from one historical winner or parameter cliffs.

### Experiment 3 — preserving the long tail after a better entry

Freeze the winning right-side entry. Compare the validated slow channel exit with structure failure and price-plus-NEMT-decay exits. No fixed take-profit. Examine MFE capture, post-exit continuation, holding time, maximum drawdown and profit after deleting the largest winners.

## Promotion rule

No state enters Emergenzix monitoring or execution until the three experiments are reproducible, out-of-sample evidence is positive, winner concentration is disclosed, and the research result is explicitly approved. PAPER monitoring must precede any execution discussion.
