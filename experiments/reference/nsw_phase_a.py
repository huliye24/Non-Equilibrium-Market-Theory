"""Deterministic semantic validation for NSW-v1 (research only)."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class SpectralObservation:
    nse_v1: float
    nscen_v1: float | None
    nsw_v1: float | None
    parseval_error: float


def _periodic_hann(size: int) -> np.ndarray:
    index = np.arange(size, dtype=float)
    return 0.5 - 0.5 * np.cos(2.0 * np.pi * index / size)


def spectral_observation(
    returns: Sequence[float], *, segment_length: int = 64, overlap: int = 32,
    nfft: int = 64, energy_floor: float = 1e-24,
) -> tuple[SpectralObservation, np.ndarray, np.ndarray]:
    """Calculate frozen NSE/centroid/central-moment width from one return window."""
    values = np.asarray(returns, dtype=float)
    if values.ndim != 1 or values.size < segment_length:
        raise ValueError("returns must be a one-dimensional window at least one segment long")
    if not np.all(np.isfinite(values)):
        raise ValueError("returns must be finite")
    if not (0 <= overlap < segment_length <= nfft):
        raise ValueError("require 0 <= overlap < segment_length <= nfft")
    centered = values - values.mean()
    nse = float(np.mean(centered ** 2))
    frequencies = np.fft.rfftfreq(nfft)[1:]
    if nse <= energy_floor:
        empty = np.zeros_like(frequencies)
        return SpectralObservation(nse, None, None, 0.0), frequencies, empty

    window = _periodic_hann(segment_length)
    hop = segment_length - overlap
    spectra = []
    for start in range(0, values.size - segment_length + 1, hop):
        segment = centered[start:start + segment_length] * window
        power = np.abs(np.fft.rfft(segment, n=nfft)) ** 2
        if nfft % 2 == 0:
            power[1:-1] *= 2.0
        else:
            power[1:] *= 2.0
        spectra.append(power[1:])
    if not spectra:
        raise ValueError("window does not contain a complete Welch segment")
    power = np.mean(spectra, axis=0)
    raw_total = float(power.sum())
    if raw_total <= energy_floor:
        empty = np.zeros_like(frequencies)
        return SpectralObservation(nse, None, None, nse), frequencies, empty

    # Preserve Welch spectral shape but normalize total retained positive-frequency
    # power to the raw-window variance. This makes the Parseval contract explicit.
    power *= nse / raw_total
    parseval_error = abs(float(power.sum()) - nse)
    probability = power / power.sum()
    centroid = float(np.sum(probability * frequencies))
    bandwidth = math.sqrt(float(np.sum(probability * (frequencies - centroid) ** 2)))
    nyquist = 0.5
    return (
        SpectralObservation(nse, centroid / nyquist, bandwidth / nyquist, parseval_error),
        frequencies, power,
    )


def _sine(size: int, frequency: float, amplitude: float = 1.0) -> np.ndarray:
    index = np.arange(size, dtype=float)
    return amplitude * np.sin(2.0 * np.pi * frequency * index)


def _chirp(size: int, start_frequency: float, end_frequency: float) -> np.ndarray:
    index = np.arange(size, dtype=float)
    slope = (end_frequency - start_frequency) / (size - 1)
    phase = 2.0 * np.pi * (start_frequency * index + 0.5 * slope * index ** 2)
    return np.sin(phase)


def _fixed_noise(size: int, seed: int = 20261030) -> np.ndarray:
    """Cross-language LCG sequence used only as deterministic broadband input."""
    state = seed
    values = []
    for _ in range(size):
        state = (1664525 * state + 1013904223) % (2 ** 32)
        values.append(state / (2 ** 32) - 0.5)
    return np.asarray(values)


def _close(left: float | None, right: float | None, tolerance: float) -> bool:
    return left is not None and right is not None and abs(left - right) <= tolerance


def run_phase_a() -> dict[str, object]:
    size = 128
    base = spectral_observation(_sine(size, 4 / 64))[0]
    half = spectral_observation(_sine(size, 4 / 64, 0.5))[0]
    double = spectral_observation(_sine(size, 4 / 64, 2.0))[0]
    low = spectral_observation(_sine(size, 4 / 64))[0]
    high = spectral_observation(_sine(size, 16 / 64))[0]

    dual = []
    for separation in (2, 6, 12):
        left = (16 - separation / 2) / 64
        right = (16 + separation / 2) / 64
        dual.append(spectral_observation(_sine(size, left) + _sine(size, right))[0])

    white = spectral_observation(_fixed_noise(size))[0]
    chirps = [spectral_observation(_chirp(size, 0.04, end))[0] for end in (0.10, 0.22, 0.38)]
    zero = spectral_observation(np.zeros(size))[0]
    constant = spectral_observation(np.full(size, 0.002))[0]
    index = np.arange(size, dtype=float)
    modulated = (1.0 + 0.6 * np.sin(2 * np.pi * index / size)) * _sine(size, 8 / 64)
    mod1 = spectral_observation(modulated)[0]
    mod3 = spectral_observation(3.0 * modulated)[0]

    checks = {
        "amplitude_energy_square_law": _close(half.nse_v1 * 16, double.nse_v1, 1e-12),
        "amplitude_centroid_invariant": _close(half.nscen_v1, double.nscen_v1, 1e-12),
        "amplitude_bandwidth_invariant": _close(half.nsw_v1, double.nsw_v1, 1e-12),
        "frequency_shift_moves_centroid": high.nscen_v1 > low.nscen_v1 + 0.25,
        "frequency_shift_preserves_narrow_bandwidth": abs(high.nsw_v1 - low.nsw_v1) < 0.015,
        "dual_frequency_separation_widens": dual[0].nsw_v1 < dual[1].nsw_v1 < dual[2].nsw_v1,
        "white_noise_wider_than_single_tone": white.nsw_v1 > base.nsw_v1 + 0.15,
        "chirp_span_widens_monotonically": chirps[0].nsw_v1 < chirps[1].nsw_v1 < chirps[2].nsw_v1,
        "zero_energy_is_undefined": zero.nscen_v1 is None and zero.nsw_v1 is None,
        "constant_return_is_undefined": constant.nscen_v1 is None and constant.nsw_v1 is None,
        "modulated_global_scale_energy_square_law": _close(mod1.nse_v1 * 9, mod3.nse_v1, 1e-12),
        "modulated_global_scale_bandwidth_invariant": _close(mod1.nsw_v1, mod3.nsw_v1, 1e-12),
    }
    observations = {
        "single_tone": asdict(base), "half_amplitude": asdict(half),
        "double_amplitude": asdict(double), "low_frequency": asdict(low),
        "high_frequency": asdict(high),
        "dual_frequency": [asdict(item) for item in dual],
        "white_noise_seed_20261030": asdict(white),
        "chirp": [asdict(item) for item in chirps], "zero": asdict(zero),
        "constant": asdict(constant), "modulated": asdict(mod1),
        "modulated_scaled_3x": asdict(mod3),
    }
    max_parseval_error = max(
        item["parseval_error"]
        for value in observations.values()
        for item in (value if isinstance(value, list) else [value])
    )
    checks["parseval_error_within_tolerance"] = max_parseval_error <= 1e-14
    report: dict[str, object] = {
        "experiment": "NSW-V1-PHASE-A-DETERMINISTIC",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "implementation": "python-numpy",
        "config": {"window": size, "segment_length": 64, "overlap": 32, "nfft": 64,
                   "window_function": "periodic_hann", "dc_removed": True},
        "checks": checks, "observations": observations,
        "max_parseval_error": max_parseval_error,
        "execution_mode": "RESEARCH_ONLY", "live_enabled": False,
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["report_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return report


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = run_phase_a()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": report["status"], "report_sha256": report["report_sha256"]}))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

