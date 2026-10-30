"""BTC 4h A/B/C pyramiding and stop-ratchet micro experiment."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


GRID = tuple(itertools.product(
    (1.5, 2.0, 2.5, 3.0, 3.5),
    (5, 10, 20, 30, 40),
    (0.5, 1.0, 1.5, 2.0),
    (0.0, 10.0, 20.0, 30.0),
    (1, 4),
))


@dataclass(frozen=True)
class Trail:
    atr_multiple: float
    structure_bars: int
    breakeven_r: float
    buffer_bps: float
    cadence: int


def aggregate_4h(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.resample("4h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    count = raw.close.resample("4h", label="left", closed="left").count()
    return frame[count == 16].dropna()


def indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    previous = out.close.shift(1)
    tr = pd.concat((out.high - out.low, (out.high - previous).abs(),
                    (out.low - previous).abs()), axis=1).max(axis=1)
    out["n"] = tr.rolling(120).mean().shift(1)
    out["entry_high"] = out.high.rolling(120).max().shift(1)
    out["exit_low"] = out.low.rolling(60).min().shift(1)
    return out


def _fill_price(reference: float, side: str, slippage=0.0002) -> float:
    return reference * (1 + slippage if side == "buy" else 1 - slippage)


def simulate(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, arm: str,
             trail: Trail | None = None) -> dict:
    fee = 0.0005
    equity = cash = 10_000.0
    qty = avg = stop = initial_entry = initial_stop = initial_qty = position_cost = 0.0
    best_close = 0.0
    adds = tightenings = bars_held = 0
    pending_entry = pending_exit = pending_add = False
    trades, curve, max_open_risk = [], [], 0.0
    risk_weights = 1.75 if arm in ("B", "C") else 1.0
    rows = df[(df.index >= start - pd.Timedelta(days=30)) & (df.index < end)]
    active = False

    def close_position(reference: float, reason: str, timestamp) -> None:
        nonlocal cash, qty, avg, stop, initial_entry, initial_stop, initial_qty, position_cost
        nonlocal best_close, adds, bars_held, pending_add, pending_exit
        fill = _fill_price(reference, "sell")
        proceeds = qty * fill * (1 - fee)
        pnl = proceeds - position_cost
        initial_risk = max(1e-12, initial_qty * (initial_entry - initial_stop))
        trades.append({"exit": str(timestamp), "reason": reason, "pnl": pnl,
                       "r": pnl / initial_risk, "adds": adds})
        cash += proceeds
        qty = avg = stop = initial_entry = initial_stop = initial_qty = position_cost = 0.0
        best_close = 0.0
        adds = bars_held = 0
        pending_add = pending_exit = False

    for timestamp, bar in rows.iterrows():
        if timestamp >= start:
            active = True
        if not active:
            continue

        # Previously confirmed close instructions execute before this bar path.
        if qty > 0 and pending_exit:
            close_position(float(bar.open), "channel", timestamp)
            pending_exit = False
        if qty == 0 and pending_entry and np.isfinite(bar.n):
            entry = _fill_price(float(bar.open), "buy")
            distance = 2 * float(bar.n)
            budget = equity * 0.01 / risk_weights
            initial_qty = min(budget / max(distance + entry * fee * 2, 1e-12), cash / (entry * (1 + fee)))
            if initial_qty > 0:
                cost = initial_qty * entry * (1 + fee)
                cash -= cost
                position_cost = cost
                qty, avg = initial_qty, entry
                initial_entry, initial_stop, stop = entry, entry - distance, entry - distance
                best_close = entry
                adds = bars_held = 0
            pending_entry = False
        if qty > 0 and pending_add and adds < 2:
            entry = _fill_price(float(bar.open), "buy")
            fraction = (0.5, 0.25)[adds]
            open_stop_risk = qty * max(0.0, avg - stop)
            remaining_risk = max(0.0, equity * 0.01 - open_stop_risk)
            add_risk_per_unit = max(0.0, entry - stop) + entry * fee * 2
            risk_quantity = remaining_risk / max(add_risk_per_unit, 1e-12)
            add_qty = min(
                initial_qty * fraction,
                risk_quantity,
                cash / (entry * (1 + fee)),
            )
            if add_qty > 0:
                cost = add_qty * entry * (1 + fee)
                cash -= cost
                position_cost += cost
                avg = (avg * qty + entry * add_qty) / (qty + add_qty)
                qty += add_qty
                adds += 1
            pending_add = False

        # Existing and newly opened positions are protected inside this bar.
        if qty > 0 and float(bar.low) <= stop:
            reference = min(stop, float(bar.open))
            close_position(reference, "stop", timestamp)

        if qty > 0:
            bars_held += 1
            best_close = max(best_close, float(bar.close))
            initial_r = max(1e-12, initial_entry - initial_stop)
            r_multiple = (float(bar.close) - initial_entry) / initial_r
            if arm in ("B", "C") and adds < 2 and r_multiple >= (1.0, 2.0)[adds]:
                pending_add = True

            if arm == "C" and trail and bars_held % trail.cadence == 0:
                candidates = [stop]
                if r_multiple >= trail.breakeven_r:
                    candidates.append(avg * (1 + trail.buffer_bps / 10_000))
                if np.isfinite(bar.n):
                    candidates.append(best_close - trail.atr_multiple * float(bar.n))
                history = df.loc[:timestamp].iloc[:-1].tail(trail.structure_bars)
                if len(history) == trail.structure_bars:
                    candidates.append(float(history.low.min()))
                valid = [value for value in candidates if np.isfinite(value) and value < float(bar.close)]
                new_stop = max(valid) if valid else stop
                if new_stop > stop:
                    stop = new_stop
                    tightenings += 1

            pending_exit = bool(float(bar.close) < float(bar.exit_low)) if np.isfinite(bar.exit_low) else False
            open_risk = qty * max(0.0, avg - stop)
            max_open_risk = max(max_open_risk, open_risk / max(equity, 1e-12))
        elif np.isfinite(bar.entry_high):
            pending_entry = bool(float(bar.close) > float(bar.entry_high))

        mark = cash + qty * float(bar.close)
        equity = mark
        curve.append(mark)

    if qty > 0:
        close_position(float(rows.iloc[-1].close), "period_end", rows.index[-1])
        curve.append(cash)
    series = np.asarray(curve or [10_000.0])
    peaks = np.maximum.accumulate(series)
    drawdown = float(np.max((peaks - series) / peaks))
    return {"arm": arm, "net_return": float(cash / 10_000 - 1), "max_drawdown": drawdown,
            "trades": len(trades), "average_r": float(np.mean([x["r"] for x in trades])) if trades else 0.0,
            "additions": int(sum(x["adds"] for x in trades)), "stop_tightenings": tightenings,
            "max_open_stop_risk": max_open_risk, "trade_log": trades}


def run(path: Path) -> dict:
    z = np.load(path, allow_pickle=False)
    raw = pd.DataFrame({k: z[k] for k in ("open", "high", "low", "close", "volume")},
                       index=pd.to_datetime(z["timestamp_ns"], utc=True))
    frame = indicators(aggregate_4h(raw))
    select_start, test_start, test_end = (pd.Timestamp(x, tz="UTC") for x in
        ("2019-03-01", "2019-06-01", "2019-09-01"))
    scored = []
    for values in GRID:
        trail = Trail(*values)
        result = simulate(frame, select_start, test_start, "C", trail)
        scored.append((result["net_return"] - result["max_drawdown"], values, result))
    _, winner_values, winner_select = max(scored, key=lambda row: (row[0], tuple(-x for x in row[1])))
    winner = Trail(*winner_values)
    selection = {arm: simulate(frame, select_start, test_start, arm, winner if arm == "C" else None)
                 for arm in ("A", "B", "C")}
    test = {arm: simulate(frame, test_start, test_end, arm, winner if arm == "C" else None)
            for arm in ("A", "B", "C")}
    report = {"experiment": "BTC-STOP-RATCHET-MICRO-V1", "status": "EXPLORATORY_ONE_FOLD",
              "execution_mode": "RESEARCH_ONLY", "live_enabled": False,
              "snapshot": json.loads(str(z["metadata"]))["snapshot_id"], "grid_candidates": len(GRID),
              "winner": asdict(winner), "winner_selection": winner_select,
              "selection": selection, "test": test,
              "test_deltas": {"B_minus_A_return": test["B"]["net_return"] - test["A"]["net_return"],
                              "C_minus_B_return": test["C"]["net_return"] - test["B"]["net_return"],
                              "B_minus_A_drawdown": test["B"]["max_drawdown"] - test["A"]["max_drawdown"],
                              "C_minus_B_drawdown": test["C"]["max_drawdown"] - test["B"]["max_drawdown"]}}
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.input)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({"status": report["status"], "winner": report["winner"],
                      "test_deltas": report["test_deltas"], "sha256": report["sha256"]}))


if __name__ == "__main__":
    main()
