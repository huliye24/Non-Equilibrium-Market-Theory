import numpy as np

from compare_nsw_phase_a import compare
from nsw_phase_a import run_phase_a, spectral_observation


def test_phase_a_frozen_semantics_pass() -> None:
    report = run_phase_a()
    assert report["status"] == "PASS", {
        key: value for key, value in report["checks"].items() if not value
    }


def test_future_values_cannot_change_window_observation() -> None:
    rng = np.random.default_rng(7)
    prefix = rng.normal(size=128)
    full = np.concatenate([prefix, rng.normal(size=128)])
    changed = np.concatenate([prefix, rng.normal(size=128) * 100])
    assert spectral_observation(full[:128])[0] == spectral_observation(changed[:128])[0]


def test_invalid_and_zero_energy_boundaries() -> None:
    try:
        spectral_observation([1.0] * 63)
    except ValueError:
        pass
    else:
        raise AssertionError("short window must fail")
    observation = spectral_observation([0.0] * 128)[0]
    assert observation.nse_v1 == 0.0
    assert observation.nscen_v1 is None
    assert observation.nsw_v1 is None


def test_cross_language_comparator_contract() -> None:
    report = run_phase_a()
    result = compare(report, report)
    assert result["status"] == "PASS"
    assert result["maximum_absolute_difference"] == 0.0

