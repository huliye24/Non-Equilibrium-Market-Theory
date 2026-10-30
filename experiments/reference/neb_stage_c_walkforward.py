"""Exact Stage-C NEB+spectral walk-forward scorer.

All feature transforms are causal.  Candidate choice uses train/select only;
the three-month test slice is scored once after the winner is frozen.
Research-only: this module has no exchange or order dependencies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from neb_gpu_campaign import TFS, aggregate, energy_z, folds, labels

SPECTRAL_WINDOWS = (32, 48, 64, 96, 128, 192, 256)
BASELINES = (128, 256, 512, 1024)
WEIGHTS = (0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50)
METHODS = ("variance_bandwidth", "spectral_entropy", "low_frequency_concentration")
WINDOW_FUNCTIONS = ("hann", "rectangular")


def atomic_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True))
    tmp.replace(path)


def _spectral_features(close: np.ndarray, width: int, window_function: str, use_gpu: bool) -> dict[str, np.ndarray]:
    """Return causal spectral observables aligned to close bars."""
    out = {name: np.full(len(close), np.nan, dtype=np.float32) for name in METHODS}
    returns = np.diff(np.log(close.astype(np.float64)))
    if len(returns) < width:
        return out
    xp = np
    if use_gpu:
        import cupy as cp
        xp = cp
    taper = np.hanning(width) if window_function == "hann" else np.ones(width)
    freqs = np.fft.rfftfreq(width)[1:]
    fn = max(float(freqs[-1]), 1e-12)
    batch = 4096
    for start in range(0, len(returns) - width + 1, batch):
        stop = min(start + batch, len(returns) - width + 1)
        idx = np.arange(start, stop)[:, None] + np.arange(width)[None, :]
        x = xp.asarray(returns[idx])
        x = (x - x.mean(axis=1, keepdims=True)) * xp.asarray(taper)
        power = xp.abs(xp.fft.rfft(x, axis=1))[:, 1:] ** 2
        total = power.sum(axis=1)
        valid = total > 1e-24
        p = power / xp.maximum(total[:, None], 1e-24)
        f = xp.asarray(freqs)
        centroid = (p * f).sum(axis=1)
        variance = xp.sqrt((p * (f - centroid[:, None]) ** 2).sum(axis=1)) / fn
        entropy = -(p * xp.log(xp.maximum(p, 1e-24))).sum(axis=1) / np.log(len(freqs))
        low = p[:, freqs <= (0.2 * fn)].sum(axis=1)
        values = (variance, entropy, low)
        rows = np.arange(start, stop) + width
        for name, value in zip(METHODS, values):
            value = xp.where(valid, value, xp.nan)
            if use_gpu:
                value = xp.asnumpy(value)
            out[name][rows] = np.asarray(value, dtype=np.float32)
    return out


def _rolling_robust_z(values: np.ndarray, baseline: int) -> np.ndarray:
    series = pd.Series(values)
    median = series.rolling(baseline).median()
    mad = (series - median).abs().rolling(baseline).median()
    return ((series - median) / (1.4826 * mad).clip(lower=1e-12)).to_numpy(dtype=np.float32)


def spectral_cache(df: pd.DataFrame, use_gpu: bool) -> dict[tuple[int, int, str, str], np.ndarray]:
    cache = {}
    close = df.close.to_numpy(dtype=np.float64)
    for width in SPECTRAL_WINDOWS:
        for window_function in WINDOW_FUNCTIONS:
            raw = _spectral_features(close, width, window_function, use_gpu)
            for baseline in BASELINES:
                for method in METHODS:
                    z = _rolling_robust_z(raw[method], baseline)
                    # High normalized score always means greater spectral concentration.
                    cache[(width, baseline, method, window_function)] = -z if method != "low_frequency_concentration" else z
    return cache


def _ap(y: np.ndarray, score: np.ndarray) -> float:
    order = np.argsort(-score, kind="stable")
    yy = y[order]
    positives = int(yy.sum())
    if positives == 0:
        return float("nan")
    precision = np.cumsum(yy) / (np.arange(len(yy)) + 1)
    return float((precision * yy).sum() / positives)


def _auc(y: np.ndarray, score: np.ndarray) -> float:
    order = np.argsort(score, kind="stable")
    ranks = np.empty(len(score), dtype=np.float64)
    ranks[order] = np.arange(1, len(score) + 1)
    pos = y == 1
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    if not n_pos or not n_neg:
        return float("nan")
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def _rank_map(train: np.ndarray, values: np.ndarray) -> np.ndarray:
    reference = np.sort(train[np.isfinite(train)])
    if not len(reference):
        return np.full(len(values), np.nan, dtype=np.float32)
    return (np.searchsorted(reference, values, side="right") / len(reference)).astype(np.float32)


def _purge_label_boundary(mask: np.ndarray, horizon: int) -> np.ndarray:
    """Drop rows whose forward label would cross the end of this slice."""
    clean = mask.copy()
    positions = np.flatnonzero(mask)
    if len(positions):
        clean[positions[-min(horizon, len(positions)):]] = False
    return clean


def _neb_margin(df: pd.DataFrame, seed: pd.Series, train: np.ndarray) -> np.ndarray:
    n, m, k, slope_k = (int(seed[x]) for x in ("n", "m", "k", "slope_k"))
    z = energy_z(df.close, n, m).astype(np.float64)
    low = pd.Series(z).shift(1).rolling(k).min().to_numpy()
    slope = (z - np.roll(z, slope_k)) / slope_k
    slope[:slope_k] = np.nan
    valid = train & np.isfinite(z) & np.isfinite(low) & np.isfinite(slope)
    low_threshold = np.quantile(z[train & np.isfinite(z)], float(seed.ql))
    trigger = np.quantile(z[train & np.isfinite(z)], float(seed.qt))
    scale = max(float(np.nanmedian(np.abs(z[valid] - np.nanmedian(z[valid])))) * 1.4826, 1e-6)
    # Positive only when all three Stage-A activation conditions have margin.
    return np.minimum.reduce(((low_threshold - low) / scale, (z - trigger) / scale, slope / scale)).astype(np.float32)


def _metrics(y: np.ndarray, score: np.ndarray) -> dict:
    valid = np.isfinite(y) & np.isfinite(score)
    y = (y[valid] > 0.5).astype(np.int8)
    score = score[valid]
    base = float(y.mean()) if len(y) else float("nan")
    cutoff = np.quantile(score, 0.90) if len(score) else float("nan")
    top = score >= cutoff
    precision = float(y[top].mean()) if top.any() else float("nan")
    return {"rows": int(len(y)), "events": int(y.sum()), "base_rate": base,
            "pr_auc": _ap(y, score), "roc_auc": _auc(y, score),
            "top10_precision": precision, "top10_lift": precision - base}


def score_timeframe(df: pd.DataFrame, timeframe: str, stable: pd.DataFrame, use_gpu: bool,
                    heartbeat: Path, max_folds: int = 0, seed_limit: int = 100) -> tuple[list[dict], int]:
    horizon = TFS[timeframe][2]
    spectra = spectral_cache(df, use_gpu)
    fold_masks = folds(df.index)
    if max_folds:
        fold_masks = fold_masks[:max_folds]
    results, evaluations = [], 0
    for fold_id, (train, select, test) in enumerate(fold_masks):
        select_label_mask = _purge_label_boundary(select, horizon)
        test_label_mask = _purge_label_boundary(test, horizon)
        for rho, group in stable[stable.timeframe == timeframe].groupby("rho"):
            truth = labels(df, horizon, float(rho))
            candidates = group.head(seed_limit).reset_index(drop=True)
            best = None
            for seed_id, seed in candidates.iterrows():
                margin = _neb_margin(df, seed, train)
                base_rank_select = _rank_map(margin[train], margin[select_label_mask])
                base_rank_test = _rank_map(margin[train], margin[test_label_mask])
                y_select, y_test = truth[select_label_mask], truth[test_label_mask]
                for key, spectral in spectra.items():
                    sr_select = _rank_map(spectral[train], spectral[select_label_mask])
                    sr_test = _rank_map(spectral[train], spectral[test_label_mask])
                    valid_select = np.isfinite(y_select) & np.isfinite(base_rank_select) & np.isfinite(sr_select)
                    if valid_select.sum() < 30:
                        continue
                    ys = (y_select[valid_select] > 0.5).astype(np.int8)
                    for weight in WEIGHTS:
                        selection_score = base_rank_select[valid_select] + weight * sr_select[valid_select]
                        selection_ap = _ap(ys, selection_score)
                        evaluations += 1
                        identity = (selection_ap, -weight, -seed_id, key)
                        if best is None or identity > best[0]:
                            best = (identity, seed_id, seed, key, weight, selection_ap,
                                    base_rank_test + weight * sr_test, y_test)
            if best is None:
                continue
            _, seed_id, seed, key, weight, selection_ap, test_score, y_test = best
            test_metrics = _metrics(y_test, test_score)
            frozen_margin = _neb_margin(df, seed, train)
            control_metrics = _metrics(y_test, _rank_map(frozen_margin[train], frozen_margin[test_label_mask]))
            width, baseline, method, window_function = key
            results.append({"timeframe": timeframe, "fold": fold_id, "rho": float(rho),
                            "train_start": str(df.index[train][0]), "train_end": str(df.index[train][-1]),
                            "select_start": str(df.index[select][0]), "select_end": str(df.index[select][-1]),
                            "test_start": str(df.index[test][0]), "test_end": str(df.index[test][-1]),
                            "seed_id": int(seed_id), "neb_n": int(seed.n), "neb_m": int(seed.m),
                            "neb_ql": float(seed.ql), "neb_qt": float(seed.qt), "neb_k": int(seed.k),
                            "neb_slope_k": int(seed.slope_k), "nsw_window": width, "nsw_baseline": baseline,
                            "spectral_method": method, "window_function": window_function,
                            "nsw_weight": float(weight), "selection_pr_auc": selection_ap,
                            "test": test_metrics, "control": control_metrics,
                            "delta_pr_auc": test_metrics["pr_auc"] - control_metrics["pr_auc"],
                            "delta_top10_lift": test_metrics["top10_lift"] - control_metrics["top10_lift"]})
        atomic_json(heartbeat, {"stage": "C_WALK_FORWARD", "timeframe": timeframe,
                                "completed_folds": fold_id + 1, "total_folds": len(fold_masks),
                                "candidate_evaluations": evaluations, "updated_at": time.time()})
    return results, evaluations


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--stage-b", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeframes", nargs="+", choices=tuple(TFS), required=True)
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("--max-folds", type=int, default=0)
    parser.add_argument("--seed-limit", type=int, default=100)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    z = np.load(args.input, allow_pickle=False)
    raw = pd.DataFrame({k: z[k] for k in ("open", "high", "low", "close", "volume")},
                       index=pd.to_datetime(z["timestamp_ns"], utc=True))
    stable = pd.read_csv(args.stage_b)
    all_results, evaluations = [], 0
    for timeframe in args.timeframes:
        rule, count, _ = TFS[timeframe]
        frame = raw if count == 1 else aggregate(raw, rule, count)
        rows, count_evaluations = score_timeframe(frame, timeframe, stable, args.gpu,
                                                  args.output_dir / "heartbeat.json",
                                                  args.max_folds, args.seed_limit)
        all_results.extend(rows)
        evaluations += count_evaluations
        pd.DataFrame(all_results).to_json(args.output_dir / "stage-c-walk-forward.jsonl", orient="records", lines=True)
    deltas = np.array([row["delta_pr_auc"] for row in all_results], dtype=float)
    summary = {"schema": "neb-stage-c-walk-forward/1.0", "status": "STAGE_C_WALK_FORWARD_COMPLETE",
               "execution_mode": "RESEARCH_ONLY", "live_enabled": False,
               "snapshot": json.loads(str(z["metadata"]))["snapshot_id"],
               "timeframes": args.timeframes, "fold_results": len(all_results),
               "candidate_evaluations": evaluations,
               "positive_delta_folds": int((deltas > 0).sum()),
               "median_delta_pr_auc": float(np.nanmedian(deltas)) if len(deltas) else None}
    canonical = json.dumps(summary, sort_keys=True, separators=(",", ":"))
    summary["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    atomic_json(args.output_dir / "summary.json", summary)
    atomic_json(args.output_dir / "heartbeat.json", {"stage": "COMPLETE", "updated_at": time.time(), **summary})
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
