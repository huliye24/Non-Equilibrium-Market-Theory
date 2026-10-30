from datetime import datetime, timedelta, timezone

import numpy as np

from spectral_compression import Bar, aggregate, labels, observables

UTC = timezone.utc


def _bars(count: int, *, gap_at: int | None = None) -> list[Bar]:
    start = datetime(2018, 1, 1, tzinfo=UTC)
    result = []
    for index in range(count):
        offset = index + (1 if gap_at is not None and index >= gap_at else 0)
        close = 100.0 + index * 0.1 + np.sin(index / 5.0)
        result.append(Bar(start + timedelta(minutes=15 * offset), close - 0.1,
                          close + 0.3, close - 0.3, close))
    return result


def test_future_prices_do_not_change_historical_observables() -> None:
    bars = _bars(100)
    changed = bars[:80] + [Bar(x.timestamp, x.open * 2, x.high * 2, x.low * 2, x.close * 2) for x in bars[80:]]
    left, right = observables(bars, 32), observables(changed, 32)
    for name in left:
        np.testing.assert_allclose(left[name][:80], right[name][:80], equal_nan=True)


def test_gap_invalidates_rolling_feature_and_forward_label() -> None:
    bars = _bars(100, gap_at=50)
    feature = observables(bars, 32)["spectral_width"]
    truth, leads = labels(bars, 6)
    assert np.isnan(feature[50:82]).all()
    assert np.isnan(truth[44:50]).all()
    assert np.isnan(leads[44:50]).all()


def test_aggregate_omits_incomplete_bucket() -> None:
    bars = _bars(12)
    del bars[5]
    hourly = aggregate(bars, 4)
    assert [bar.timestamp.hour for bar in hourly] == [0, 2]

