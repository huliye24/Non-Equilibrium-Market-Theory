import numpy as np
import pandas as pd

from neb_stage_c_walkforward import _metrics, _rank_map, _spectral_features


def test_spectral_features_are_causal_and_finite():
    close = 100 * np.exp(np.cumsum(0.001 * np.sin(np.arange(400) / 7)))
    original = _spectral_features(close, 32, "hann", False)
    changed = close.copy()
    changed[300:] *= np.linspace(1, 2, 100)
    future_changed = _spectral_features(changed, 32, "hann", False)
    for name in original:
        np.testing.assert_allclose(original[name][:300], future_changed[name][:300], equal_nan=True)
        assert np.isfinite(original[name][100:250]).all()


def test_rank_mapping_uses_only_reference_values():
    train = np.array([1.0, 2.0, 3.0, np.nan])
    np.testing.assert_allclose(_rank_map(train, np.array([0.0, 2.0, 4.0])), [0.0, 2 / 3, 1.0])


def test_metrics_detect_incremental_ranking():
    y = np.array([0, 0, 1, 1], dtype=float)
    weak = _metrics(y, np.array([0.0, 1.0, 2.0, 3.0]))
    bad = _metrics(y, np.array([3.0, 2.0, 1.0, 0.0]))
    assert weak["pr_auc"] > bad["pr_auc"]
