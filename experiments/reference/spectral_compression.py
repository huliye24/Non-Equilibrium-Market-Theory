"""Causal E1-E2 compression-observable pilot.

The module is execution-free.  It reads a pinned public-market-data snapshot and
produces research evidence only; it has no exchange or order integration.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

UTC = timezone.utc
STEP = timedelta(minutes=15)
TIMEFRAMES = {"15m": 1, "1h": 4, "4h": 16}
HORIZONS = {"15m": 96, "1h": 24, "4h": 6}
WINDOWS = (32, 64, 128)
QUANTILES = (0.10, 0.20, 0.30)
OBSERVABLES = ("spectral_width", "bollinger_bandwidth", "normalized_atr")


@dataclass(frozen=True)
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float


def _months(value: datetime, count: int) -> datetime:
    absolute = value.year * 12 + value.month - 1 + count
    return value.replace(year=absolute // 12, month=absolute % 12 + 1)


def _consecutive(bars: Sequence[Bar], left: int, right: int, step: timedelta) -> bool:
    if left < 0 or right >= len(bars) or left > right:
        return False
    expected = step.total_seconds()
    return all(
        (bars[index].timestamp - bars[index - 1].timestamp).total_seconds() == expected
        for index in range(left + 1, right + 1)
    )


def aggregate(bars: Sequence[Bar], factor: int) -> list[Bar]:
    """Aggregate complete UTC-aligned buckets without bridging gaps."""
    if factor == 1:
        return list(bars)
    seconds = int(STEP.total_seconds()) * factor
    groups: dict[int, list[Bar]] = {}
    for bar in bars:
        key = int(bar.timestamp.timestamp()) // seconds * seconds
        groups.setdefault(key, []).append(bar)
    result: list[Bar] = []
    for key in sorted(groups):
        group = sorted(groups[key], key=lambda item: item.timestamp)
        start = datetime.fromtimestamp(key, UTC)
        if len(group) != factor or group[0].timestamp != start:
            continue
        if not _consecutive(group, 0, factor - 1, STEP):
            continue
        result.append(Bar(start, group[0].open, max(x.high for x in group),
                          min(x.low for x in group), group[-1].close))
    return result


def _true_ranges(bars: Sequence[Bar]) -> np.ndarray:
    values = np.full(len(bars), np.nan)
    for index in range(1, len(bars)):
        values[index] = max(
            bars[index].high - bars[index].low,
            abs(bars[index].high - bars[index - 1].close),
            abs(bars[index].low - bars[index - 1].close),
        )
    return values


def observables(bars: Sequence[Bar], window: int) -> dict[str, np.ndarray]:
    """Return trailing-only observables; discontinuous windows remain NaN."""
    size = len(bars)
    spectral = np.full(size, np.nan)
    bollinger = np.full(size, np.nan)
    atr_ratio = np.full(size, np.nan)
    closes = np.asarray([bar.close for bar in bars], dtype=float)
    true_ranges = _true_ranges(bars)
    step = STEP * round((bars[1].timestamp - bars[0].timestamp) / STEP) if size > 1 else STEP
    for index in range(window, size):
        left = index - window + 1
        if not _consecutive(bars, left - 1, index, step):
            continue
        close_window = closes[left:index + 1]
        returns = np.diff(np.log(closes[left - 1:index + 1]))
        returns -= returns.mean()
        power = np.abs(np.fft.rfft(returns)) ** 2
        frequencies = np.fft.rfftfreq(returns.size)
        power, frequencies = power[1:], frequencies[1:]
        total_power = float(power.sum())
        if total_power > 0:
            spectral[index] = math.sqrt(float(np.sum(power * frequencies ** 2)) / total_power) / 0.5
        mean = float(close_window.mean())
        if mean > 0:
            bollinger[index] = 4.0 * float(close_window.std(ddof=0)) / mean
        atr = float(np.nanmean(true_ranges[left:index + 1]))
        if closes[index] > 0 and math.isfinite(atr):
            atr_ratio[index] = atr / closes[index]
    return {
        "spectral_width": spectral,
        "bollinger_bandwidth": bollinger,
        "normalized_atr": atr_ratio,
    }


def labels(bars: Sequence[Bar], horizon: int) -> tuple[np.ndarray, np.ndarray]:
    result = np.full(len(bars), np.nan)
    leads = np.full(len(bars), np.nan)
    step = bars[1].timestamp - bars[0].timestamp
    for index in range(horizon - 1, len(bars) - horizon):
        if not _consecutive(bars, index - horizon + 1, index + horizon, step):
            continue
        trailing = bars[index - horizon + 1:index + 1]
        future = bars[index + 1:index + horizon + 1]
        reference = max(x.high for x in trailing) - min(x.low for x in trailing)
        target = 1.25 * reference
        result[index] = float(max(x.high for x in future) - min(x.low for x in future) >= target)
        if result[index] == 1.0:
            for lead in range(1, horizon + 1):
                partial = future[:lead]
                if max(x.high for x in partial) - min(x.low for x in partial) >= target:
                    leads[index] = float(lead)
                    break
    return result, leads


def _metrics(values: np.ndarray, truth: np.ndarray, leads: np.ndarray,
             threshold: float) -> dict[str, float | int | None]:
    valid = np.isfinite(values) & np.isfinite(truth)
    signal = np.zeros(len(values), dtype=bool)
    below = valid & (values <= threshold)
    signal[1:] = below[1:] & ~below[:-1]
    tp = int(np.sum(signal & (truth == 1)))
    fp = int(np.sum(signal & (truth == 0)))
    positives = int(np.sum(valid & (truth == 1)))
    negatives = int(np.sum(valid & (truth == 0)))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / positives if positives else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    base = positives / (positives + negatives) if positives + negatives else 0.0
    signal_leads = leads[signal & (truth == 1) & np.isfinite(leads)]
    return {
        "events": tp + fp, "true_positives": tp, "false_positives": fp,
        "precision": precision, "recall": recall, "f1": f1,
        "base_expansion_rate": base,
        "precision_lift": precision - base,
        "false_positive_rate": fp / negatives if negatives else 0.0,
        "median_lead_bars": float(np.median(signal_leads)) if signal_leads.size else None,
    }


def _slice(bars: Sequence[Bar], start: datetime, end: datetime) -> np.ndarray:
    return np.asarray([start <= bar.timestamp < end for bar in bars], dtype=bool)


def evaluate_timeframe(bars: Sequence[Bar], timeframe: str) -> dict[str, Any]:
    feature_cache = {window: observables(bars, window) for window in WINDOWS}
    truth, leads = labels(bars, HORIZONS[timeframe])
    anchor, data_end = datetime(2017, 9, 1, tzinfo=UTC), datetime(2019, 1, 1, tzinfo=UTC)
    records: list[dict[str, Any]] = []
    train_start = anchor
    while _months(train_start, 10) <= data_end:
        selection_start, test_start, test_end = _months(train_start, 6), _months(train_start, 8), _months(train_start, 10)
        train_mask = _slice(bars, train_start, selection_start)
        select_mask = _slice(bars, selection_start, test_start)
        test_mask = _slice(bars, test_start, test_end)
        for name in OBSERVABLES:
            candidates: list[tuple[float, float, int, float, dict[str, Any]]] = []
            for window in WINDOWS:
                values = feature_cache[window][name]
                training = values[train_mask & np.isfinite(values)]
                if training.size == 0:
                    continue
                for quantile in QUANTILES:
                    threshold = float(np.quantile(training, quantile))
                    metric = _metrics(values[select_mask], truth[select_mask],
                                      leads[select_mask], threshold)
                    candidates.append((float(metric["f1"]), float(metric["precision"]), -window,
                                       -quantile, {"window": window, "quantile": quantile,
                                                   "threshold": threshold}))
            if not candidates:
                raise ValueError(f"no selectable candidates for {timeframe}/{name}")
            selected = max(candidates)[-1]
            values = feature_cache[selected["window"]][name]
            metric = _metrics(values[test_mask], truth[test_mask], leads[test_mask],
                              selected["threshold"])
            records.append({
                "train_start": train_start.isoformat(),
                "selection_start": selection_start.isoformat(),
                "test_start": test_start.isoformat(),
                "test_end_exclusive": test_end.isoformat(),
                "observable": name, "selected": selected, "metrics": metric,
            })
        train_start = _months(train_start, 2)
    summary = {}
    for name in OBSERVABLES:
        rows = [row for row in records if row["observable"] == name]
        lifts = [float(row["metrics"]["precision_lift"]) for row in rows]
        summary[name] = {
            "windows": len(rows),
            "positive_lift_windows": sum(value > 0 for value in lifts),
            "median_precision_lift": float(np.median(lifts)) if lifts else 0.0,
            "total_events": sum(int(row["metrics"]["events"]) for row in rows),
        }
    return {"bars": len(bars), "windows": records, "summary": summary}


def load_s3_snapshot(bucket: str, manifest_key: str, start: datetime, end: datetime) -> tuple[list[Bar], dict[str, Any]]:
    """Read and hash-check eligible 15m Parquet objects from a pinned manifest."""
    import boto3
    import pyarrow.parquet as parquet

    s3 = boto3.client("s3", region_name="cn-northwest-1")
    manifest_raw = s3.get_object(Bucket=bucket, Key=manifest_key)["Body"].read()
    manifest = json.loads(manifest_raw)
    rows: list[Bar] = []
    used: list[dict[str, Any]] = []
    for item in manifest["objects"]:
        if item.get("timeframe") != "15m":
            continue
        first, last = datetime.fromisoformat(item["first_at"]), datetime.fromisoformat(item["last_at"])
        if last < start or first >= end:
            continue
        payload = s3.get_object(Bucket=bucket, Key=item["key"])["Body"].read()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"object hash mismatch: {item['key']}")
        table = parquet.read_table(io.BytesIO(payload)).to_pylist()
        for row in table:
            timestamp = row.get("open_time") or row.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)
            if start <= timestamp < end and row.get("is_closed", True) and not row.get("is_imputed", False):
                rows.append(Bar(timestamp, float(row["open"]), float(row["high"]),
                                float(row["low"]), float(row["close"])))
        used.append({"key": item["key"], "sha256": digest, "rows": item["rows"]})
    rows.sort(key=lambda item: item.timestamp)
    if len({bar.timestamp for bar in rows}) != len(rows):
        raise ValueError("duplicate canonical timestamps")
    return rows, {"bucket": bucket, "manifest_key": manifest_key,
                  "snapshot_id": manifest["snapshot_id"], "objects": used}


def run(bucket: str, manifest_key: str) -> dict[str, Any]:
    base, provenance = load_s3_snapshot(
        bucket, manifest_key, datetime(2017, 8, 17, tzinfo=UTC), datetime(2019, 1, 1, tzinfo=UTC)
    )
    results = {}
    for timeframe, factor in TIMEFRAMES.items():
        results[timeframe] = evaluate_timeframe(aggregate(base, factor), timeframe)
    report = {
        "experiment": "E1-E2-BTC-COMPRESSION-2017-2018-PILOT",
        "status": "EXPLORATORY", "execution_mode": "RESEARCH_ONLY",
        "live_enabled": False, "provenance": provenance, "results": results,
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["report_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--manifest-key", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = run(args.bucket, args.manifest_key)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "report_sha256": report["report_sha256"],
                      "snapshot_id": report["provenance"]["snapshot_id"]}, sort_keys=True))


if __name__ == "__main__":
    main()

