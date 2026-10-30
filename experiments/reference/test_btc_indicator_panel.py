import numpy as np
import pandas as pd

from btc_indicator_panel import features


def _frame(count=400):
    index = pd.date_range("2018-01-01", periods=count, freq="15min", tz="UTC")
    close = 100 + np.arange(count) * 0.01 + np.sin(np.arange(count) / 8)
    return pd.DataFrame({"open": close - .1, "high": close + .4, "low": close - .4,
                         "close": close, "volume": 10 + np.cos(np.arange(count) / 5)}, index=index)


def test_future_change_does_not_modify_past_features():
    left = _frame()
    right = left.copy()
    right.iloc[300:, right.columns.get_loc("close")] *= 2
    right.iloc[300:, right.columns.get_loc("high")] *= 2
    right.iloc[300:, right.columns.get_loc("low")] *= 2
    right.iloc[300:, right.columns.get_loc("open")] *= 2
    a, b = features(left, 64), features(right, 64)
    assert set(a) == set(b)
    for name in a:
        np.testing.assert_allclose(a[name][:300], b[name][:300], equal_nan=True)


def test_panel_contains_frozen_twenty_indicators():
    assert len(features(_frame(), 32)) == 20
