import numpy as np
import pandas as pd

from btc_stop_ratchet_micro import GRID, Trail, indicators, simulate


def bars() -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=500, freq="4h", tz="UTC")
    close = np.r_[np.full(200, 100.0), np.linspace(100, 180, 300)]
    frame = pd.DataFrame({"open": close, "high": close, "low": close - 1,
                          "close": close, "volume": 1.0}, index=index)
    return indicators(frame)


def test_grid_is_frozen_at_800_candidates():
    assert len(GRID) == 800


def test_stop_ratchet_never_has_more_open_risk_than_static_pyramid_on_trend():
    frame = bars()
    start, end = frame.index[150], frame.index[-1] + pd.Timedelta(hours=4)
    static = simulate(frame, start, end, "B")
    dynamic = simulate(frame, start, end, "C", Trail(2.0, 10, 1.0, 10.0, 1))
    assert dynamic["stop_tightenings"] > 0
    assert static["max_open_stop_risk"] <= 0.01 + 1e-12
    assert dynamic["max_open_stop_risk"] <= 0.01 + 1e-12
    assert dynamic["max_open_stop_risk"] <= static["max_open_stop_risk"] + 1e-12


def test_no_arm_creates_live_execution_state():
    frame = bars()
    result = simulate(frame, frame.index[150], frame.index[-1], "A")
    assert "orders" not in result
    assert "live_enabled" not in result
