# NSW-v1 Phase A deterministic semantic validation

Status: Python PASS; MATLAB execution blocked by online-license authentication.

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

## MATLAB status

The independent MATLAB R2023b files were copied to the research node at:

```text
/home/ubuntu/strokera-matlab-lab/experiments/nsw_phase_a/
```

Server file hashes:

- `nsw_observation.m`:
  `40a900cf506aa355c8ae12ed452e83fc1154d1c07b707d1e3711fa50eb7444ec`
- `run_nsw_phase_a.m`:
  `d74021529ba6f9d0189edd51223effee2199074b7e3010913bba31abc0856a9b`

SSH connectivity and the MATLAB R2023b installation were verified. Batch mode
cannot check out a license, and the documented online-license flow closes after
the saved MathWorks credentials are submitted. Consequently MATLAB code has not
been executed and no cross-language PASS is claimed.

When the online license is restored, run:

```matlab
cd('/home/ubuntu/strokera-matlab-lab/experiments/nsw_phase_a')
run_nsw_phase_a('nsw_phase_a_matlab.json')
```

Then compare the MATLAB JSON with the Python golden report using
`compare_nsw_phase_a.py`. The frozen cross-language tolerance is `1e-11`.

## Gate decision

Phase A is not complete because independent MATLAB execution remains pending.
Do not begin the stochastic synthetic experiment or BTC experiment yet. Restoring
the MathWorks online license and observing a cross-language PASS is the only next
action allowed by this phase gate.

