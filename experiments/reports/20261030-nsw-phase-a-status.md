# NSW-v1 Phase A deterministic semantic validation

Status: Python PASS; MATLAB PASS; cross-language comparison PASS.

## Scope

This phase uses deterministic synthetic returns only. It reads no market data,
runs no backtest, and creates no signal, order, position, or trading permission.
The frozen formulas are NSE-v1 (window variance), NSCEN-v1 (normalized spectral
centroid), and NSW-v1 (normalized second central moment around the centroid).

## Python result

- Implementation: NumPy, periodic Hann Welch, window 128, segment 64, overlap
  32, FFT 64, DC removed.
- Frozen semantic checks: 13/13 PASS.
- Unit tests: 4/4 PASS.
- Maximum Parseval absolute error: `8.881784197001252e-16`.
- Report SHA-256: `f46cd73fdee849133d90ea9597c6fa4ddd41cfa1b4fd4f15c9dcd5bb5e2b2ba6`.

Selected golden values:

| Input | NSE-v1 | NSCEN-v1 | NSW-v1 |
| --- | ---: | ---: | ---: |
| Single tone, 4/64 | 0.500000 | 0.125000 | 0.018042 |
| Single tone, 16/64 | 0.500000 | 0.500000 | 0.018042 |
| Dual tone, separation 2 | — | — | 0.033408 |
| Dual tone, separation 6 | — | — | 0.095470 |
| Dual tone, separation 12 | — | — | 0.188366 |
| Chirp end 0.10 | — | — | 0.031758 |
| Chirp end 0.22 | — | — | 0.080579 |
| Chirp end 0.38 | — | — | 0.149302 |

Zero and constant-return inputs correctly return an undefined centroid and
bandwidth rather than a misleading zero bandwidth.

## MATLAB and cross-language result

The independent MATLAB implementation was executed with the licensed MATLAB
Online engine, which self-reported `matlab-r2023b`. All 13 frozen semantic
checks passed. The MATLAB maximum Parseval absolute error was
`3.3306690738754696e-16`.

MATLAB observations were compared numerically with the immutable Python golden
report:

- Compared scalar values: 60.
- Frozen absolute tolerance: `1e-11`.
- Maximum observed absolute difference: `8.881784197001252e-16`.
- Cross-language result: PASS.
- Python report SHA-256:
  `f46cd73fdee849133d90ea9597c6fa4ddd41cfa1b4fd4f15c9dcd5bb5e2b2ba6`.

The same MATLAB files remain copied to the Ningxia research node at:

```text
/home/ubuntu/strokera-matlab-lab/experiments/nsw_phase_a/
```

Server file hashes:

- `nsw_observation.m`:
  `40a900cf506aa355c8ae12ed452e83fc1154d1c07b707d1e3711fa50eb7444ec`
- `run_nsw_phase_a.m`:
  `d74021529ba6f9d0189edd51223effee2199074b7e3010913bba31abc0856a9b`

SSH connectivity and the MATLAB R2023b installation were verified. That node's
non-interactive batch mode still cannot check out an online license, so this
phase was executed in MATLAB Online instead. This is an infrastructure
limitation only; it does not invalidate the independent MATLAB calculation.

When server-side batch licensing is restored, the reproducibility command is:

```matlab
cd('/home/ubuntu/strokera-matlab-lab/experiments/nsw_phase_a')
run_nsw_phase_a('nsw_phase_a_matlab.json')
```

The repository also contains `compare_nsw_phase_a.m`, which performs the frozen
recursive numeric comparison and writes the comparison artifact.

## Gate decision

Phase A is complete. Deterministic semantic behavior and Python/MATLAB numerical
agreement meet the preregistered gate. No stochastic synthetic or BTC experiment
was run as part of this micro-task.

