# NEB million-grid GPU campaign

Status: frozen before cloud execution; research only; no trading permission.

## Atomic definitions

For log return `r_t = log(C_t/C_{t-1})`, energy window `N`, and epsilon
`1e-12`:

`E_t(N) = mean((r - mean(r))^2)` and `X_t(N) = log(E_t(N)+epsilon)`.

For baseline window `M`:

`B_t = median(X[t-M+1:t])`,
`S_t = 1.4826 * median(abs(X-B_t))`, and
`Z_t = (X_t-B_t)/max(S_t, epsilon)`.

Compression uses a trailing minimum over `K` bars. Activation requires the
previous `K`-bar minimum to be at or below a frozen low threshold, the current
Z value to be at or above a trigger threshold, and positive `k`-bar slope.

## Stage A: exhaustive structural coarse grid

- `N`: 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256
- `M`: 64, 96, 128, 192, 256, 384, 512, 768, 1024
- low quantile: .05, .10, .15, .20, .25, .30
- trigger quantile: .35, .40, .45, .50, .55, .60
- `K`: 4, 8, 12, 16, 24, 32, 48
- slope `k`: 1, 2, 3, 4, 6, 8, 12, 16
- relative range labels: 1.15, 1.25, 1.50, 2.00
- timeframes: 15m, 1h, 4h

The grid contains 2,395,008 metric evaluations (199,584 structural parameter
sets × four labels × three timeframes; unavailable warm-up rows are excluded).
The engine records the exact realized count rather than relying on this rounded
planning figure.

Coarse objective is computed from precision lift, recall, F1, event coverage,
and penalties for fewer than 30 events. It is used only to select a region.

## Stage B: dense stable-region evaluation

The top 10 percent of Stage A by each timeframe/label enters complete scoring:
PR-AUC, ROC-AUC, Brier ratio, calibration bins, block-bootstrap intervals, and
neighbourhood stability. A single isolated maximum cannot win.

## Stage C: NSW incremental value

Stable NEB regions scan NSW windows 32, 48, 64, 96, 128, 192, 256; baseline
windows 128, 256, 512, 1024; Hann/rectangular windows; variance bandwidth,
spectral entropy and low-frequency concentration; and NSW weights 0, .05, .10,
.15, .20, .30, .40, .50. Weight zero is retained as the nested NEB control.

## Time isolation

Each rolling fold uses 18 months training, 3 months parameter selection and 3
months untouched test, stepping forward 3 months. Parameter search sees only
training/selection data. Final test rows are appended after selection and never
used to change the same fold.

## Operations

The job writes resumable stage checkpoints, a heartbeat, GPU/CPU parity sample,
and final hashes. Only a successful final gate sends a completion message. A
failure sends a sanitized failure notification. `live_enabled=false` and no
order/exchange-private API is present.
