"""Point-in-time walk-forward research interface for ASDE.

This module is deliberately dependency-free and offline.  It selects no live
orders and owns no account arithmetic: callers must inject the audited ledger
used by their execution system.  All features for bar ``t`` are built from
bars strictly before ``t``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import isfinite
from statistics import fmean, median
from typing import Callable, Mapping, Protocol, Sequence

from asde import Scenario, enumerate_decisions


EVIDENCE_LEVEL = "CONJECTURE / UNVALIDATED"


@dataclass(frozen=True)
class Observation:
    timestamp: str
    market: str
    close: float
    volume: float


@dataclass(frozen=True)
class Preregistration:
    market: str
    start_timestamp: str
    initial_capital: float
    train_size: int
    validation_size: int
    test_size: int
    fee_rate: float
    slippage_rate: float
    horizon: int = 1
    min_state_samples: int = 3
    trend_lookback: int = 3
    volatility_lookback: int = 5
    liquidity_lookback: int = 5
    tail_probability: float = 0.05
    result_metrics: tuple[str, ...] = (
        "final_equity", "max_drawdown", "tail_loss", "brier_score"
    )


@dataclass(frozen=True)
class MarketState:
    trend: str
    volatility: str
    liquidity: str

    @property
    def key(self) -> str:
        return f"{self.trend}|{self.volatility}|{self.liquidity}"


@dataclass(frozen=True)
class LedgerSnapshot:
    equity: float
    drawdown: float
    metadata: dict[str, object] = field(default_factory=dict)


class AuditedLedger(Protocol):
    """Adapter contract implemented by the audited Emergenzix ledger."""

    def reset(self, initial_capital: float) -> None:
        """Reset to the preregistered capital."""

    def apply_period(
        self,
        *,
        timestamp: str,
        market: str,
        allocation: float,
        asset_return: float,
        fee_rate: float,
        slippage_rate: float,
    ) -> LedgerSnapshot:
        """Book one period and return audited equity/drawdown state."""


@dataclass(frozen=True)
class CandidateLog:
    allocation: float
    feasible: bool
    expected_log_growth: float
    worst_case_return: float
    reason: str


@dataclass(frozen=True)
class PeriodResult:
    timestamp: str
    market: str
    state: str
    scenario_probabilities: dict[str, float]
    selected_allocation: float
    realized_scenario: str
    equity: float
    drawdown: float
    candidates: tuple[CandidateLog, ...]
    fallback_reason: str = ""


@dataclass(frozen=True)
class RunSummary:
    label: str
    final_equity: float
    max_drawdown: float
    tail_loss: float
    brier_score: float
    periods: tuple[PeriodResult, ...]


@dataclass(frozen=True)
class WalkForwardReport:
    evidence_level: str
    preregistration: dict[str, object]
    runs: dict[str, RunSummary]
    warnings: tuple[str, ...]


def _validate(observations: Sequence[Observation], config: Preregistration) -> None:
    required = config.train_size + config.validation_size + config.test_size + 1
    if len(observations) < required:
        raise ValueError(f"need at least {required} observations")
    if config.initial_capital <= 0 or not isfinite(config.initial_capital):
        raise ValueError("initial_capital must be positive and finite")
    sizes = (config.train_size, config.validation_size, config.test_size)
    if any(size <= 0 for size in sizes):
        raise ValueError("split sizes must be positive")
    if config.horizon != 1:
        raise ValueError("reference implementation supports one-step replanning only")
    if config.min_state_samples <= 0:
        raise ValueError("min_state_samples must be positive")
    if any(value < 0 or not isfinite(value)
           for value in (config.fee_rate, config.slippage_rate)):
        raise ValueError("costs must be finite and nonnegative")
    if not 0 < config.tail_probability <= 1:
        raise ValueError("tail_probability must lie in (0, 1]")
    timestamps = [row.timestamp for row in observations]
    if timestamps != sorted(timestamps) or len(set(timestamps)) != len(timestamps):
        raise ValueError("timestamps must be unique and increasing")
    markets = {row.market for row in observations}
    if markets != {config.market}:
        raise ValueError("observations must match the preregistered market")
    if observations[0].timestamp != config.start_timestamp:
        raise ValueError("observations must start at the preregistered timestamp")
    required_metrics = {"final_equity", "max_drawdown", "tail_loss", "brier_score"}
    if not required_metrics.issubset(config.result_metrics):
        raise ValueError("all required result metrics must be preregistered")
    if any(row.close <= 0 or row.volume < 0 or
           not isfinite(row.close) or not isfinite(row.volume)
           for row in observations):
        raise ValueError("prices/volumes must be finite and valid")


def _returns(observations: Sequence[Observation]) -> list[float]:
    return [observations[i].close / observations[i - 1].close - 1
            for i in range(1, len(observations))]


def _state_at(
    observations: Sequence[Observation],
    returns: Sequence[float],
    index: int,
    config: Preregistration,
) -> MarketState:
    """Build state for observation index using only indices smaller than it."""
    end = index - 1
    trend_start = max(0, end - config.trend_lookback + 1)
    vol_start = max(0, end - config.volatility_lookback + 1)
    past_returns = list(returns[vol_start:end])
    trend_returns = list(returns[trend_start:end])
    if not past_returns or not trend_returns:
        return MarketState("flat", "unknown", "unknown")
    trend_mean = fmean(trend_returns)
    trend = "up" if trend_mean > 0 else "down" if trend_mean < 0 else "flat"
    abs_returns = [abs(value) for value in returns[:end]]
    current_vol = fmean(abs(value) for value in past_returns)
    volatility = "high" if current_vol > median(abs_returns) else "low"
    volume_start = max(0, index - config.liquidity_lookback)
    past_volumes = [row.volume for row in observations[volume_start:index]]
    prior_volumes = [row.volume for row in observations[:index]]
    liquidity = "high" if fmean(past_volumes) >= median(prior_volumes) else "low"
    return MarketState(trend, volatility, liquidity)


def _scenario_name(value: float) -> str:
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "flat"


def _estimate_probabilities(
    states: Sequence[MarketState],
    returns: Sequence[float],
    state: MarketState,
    history_end: int,
    min_samples: int,
    uniform: bool,
    ignore_state: bool,
) -> tuple[dict[str, float], int]:
    labels = ("down", "flat", "up")
    eligible = [i for i in range(history_end)
                if ignore_state or states[i].key == state.key]
    support = len(eligible)
    if support < min_samples:
        return {}, support
    if uniform:
        return {label: 1 / 3 for label in labels}, support
    counts = {label: 1.0 for label in labels}  # Laplace smoothing, frozen.
    for i in eligible:
        counts[_scenario_name(returns[i])] += 1
    total = sum(counts.values())
    return {label: counts[label] / total for label in labels}, support


def _scenario_returns(history: Sequence[float]) -> dict[str, float]:
    buckets = {"down": [], "flat": [], "up": []}
    for value in history:
        buckets[_scenario_name(value)].append(value)
    scale = median(abs(value) for value in history) if history else 0.0
    return {
        "down": fmean(buckets["down"]) if buckets["down"] else -scale,
        "flat": fmean(buckets["flat"]) if buckets["flat"] else 0.0,
        "up": fmean(buckets["up"]) if buckets["up"] else scale,
    }


def _tail_loss(periods: Sequence[PeriodResult], probability: float) -> float:
    if len(periods) < 2:
        return 0.0
    changes = [periods[i].equity / periods[i - 1].equity - 1
               for i in range(1, len(periods))]
    count = max(1, int(len(changes) * probability))
    return -fmean(sorted(changes)[:count])


def _run(
    observations: Sequence[Observation],
    config: Preregistration,
    ledger: AuditedLedger,
    *,
    label: str,
    mode: str,
    uniform: bool = False,
    ignore_state: bool = False,
    cost_multiplier: float = 1.0,
    rolling: bool = True,
) -> RunSummary:
    returns = _returns(observations)
    states = [_state_at(observations, returns, i + 1, config)
              for i in range(len(returns))]
    first_validation = config.train_size
    first_test = first_validation + config.validation_size
    last_test = first_test + config.test_size
    ledger.reset(config.initial_capital)
    periods: list[PeriodResult] = []
    brier_terms: list[float] = []
    frozen_history_end = config.train_size

    for return_index in range(first_validation, last_test):
        observation_index = return_index + 1
        state = states[return_index]
        history_end = return_index if rolling else frozen_history_end
        probabilities, support = _estimate_probabilities(
            states, returns, state, history_end, config.min_state_samples,
            uniform, ignore_state,
        )
        realized = _scenario_name(returns[return_index])
        fallback = ""
        candidates: tuple[CandidateLog, ...] = ()

        if mode == "cash":
            allocation = 0.0
        elif mode == "buy_hold":
            allocation = 1.0
        elif mode == "trend":
            allocation = 1.0 if state.trend == "up" else 0.0
        elif not probabilities:
            allocation = 0.0
            fallback = f"no-trade: state support {support} < {config.min_state_samples}"
        else:
            scenario_values = _scenario_returns(returns[:history_end])
            decisions = enumerate_decisions(
                [Scenario(name, scenario_values[name], probabilities[name])
                 for name in ("down", "flat", "up")],
                round_trip_cost=(config.fee_rate + config.slippage_rate) * cost_multiplier,
            )
            candidates = tuple(CandidateLog(**asdict(item)) for item in decisions)
            allocation = decisions[0].allocation if decisions[0].feasible else 0.0

        if probabilities:
            brier_terms.append(sum(
                (probabilities[name] - float(name == realized)) ** 2
                for name in ("down", "flat", "up")
            ) / 3)
        snapshot = ledger.apply_period(
            timestamp=observations[observation_index].timestamp,
            market=observations[observation_index].market,
            allocation=allocation,
            asset_return=returns[return_index],
            fee_rate=config.fee_rate * cost_multiplier,
            slippage_rate=config.slippage_rate * cost_multiplier,
        )
        periods.append(PeriodResult(
            timestamp=observations[observation_index].timestamp,
            market=observations[observation_index].market,
            state=state.key,
            scenario_probabilities=probabilities,
            selected_allocation=allocation,
            realized_scenario=realized,
            equity=snapshot.equity,
            drawdown=snapshot.drawdown,
            candidates=candidates,
            fallback_reason=fallback,
        ))

    return RunSummary(
        label=label,
        final_equity=periods[-1].equity,
        max_drawdown=max((row.drawdown for row in periods), default=0.0),
        tail_loss=_tail_loss(periods, config.tail_probability),
        brier_score=fmean(brier_terms) if brier_terms else float("nan"),
        periods=tuple(periods),
    )


def run_walk_forward(
    observations: Sequence[Observation],
    config: Preregistration,
    ledger_factory: Callable[[], AuditedLedger],
) -> WalkForwardReport:
    """Run frozen splits, baselines, and preregistered ablations.

    ``ledger_factory`` must return a fresh adapter to the externally audited
    account/guarantee/liquidation ledger.  This interface never grants PAPER or
    LIVE permission.
    """
    _validate(observations, config)
    specifications = (
        ("asde", "asde", {}),
        ("cash", "cash", {}),
        ("buy_hold", "buy_hold", {}),
        ("fixed_trend", "trend", {}),
        ("ablation_no_state", "asde", {"ignore_state": True}),
        ("ablation_no_rolling", "asde", {"rolling": False}),
        ("ablation_uniform_probability", "asde", {"uniform": True}),
        ("ablation_double_cost", "asde", {"cost_multiplier": 2.0}),
    )
    runs = {
        label: _run(observations, config, ledger_factory(), label=label, mode=mode, **options)
        for label, mode, options in specifications
    }
    return WalkForwardReport(
        evidence_level=EVIDENCE_LEVEL,
        preregistration=asdict(config),
        runs=runs,
        warnings=(
            "Estimated probabilities may be miscalibrated.",
            "Finite scenarios may omit tail events.",
            "Structural change can invalidate historical state frequencies.",
            "Research output grants no PAPER or LIVE permission.",
        ),
    )


def run_frozen_battery(
    datasets: Mapping[str, Sequence[Observation]],
    config_factory: Callable[[str, Sequence[Observation]], Preregistration],
    ledger_factory: Callable[[], AuditedLedger],
) -> dict[str, WalkForwardReport]:
    """Run cross-year/cross-market datasets without selecting winners.

    The caller preregisters every dataset and must return a configuration with
    identical model/cost parameters except for ``market`` and
    ``start_timestamp``.  Every result, including failures, remains in the
    returned mapping.
    """
    if len(datasets) < 2:
        raise ValueError("a frozen battery requires at least two datasets")
    reports: dict[str, WalkForwardReport] = {}
    frozen_signature: tuple[object, ...] | None = None
    for name, observations in datasets.items():
        config = config_factory(name, observations)
        signature = (
            config.initial_capital, config.train_size, config.validation_size,
            config.test_size, config.fee_rate, config.slippage_rate,
            config.horizon, config.min_state_samples, config.trend_lookback,
            config.volatility_lookback, config.liquidity_lookback,
            config.tail_probability, config.result_metrics,
        )
        if frozen_signature is None:
            frozen_signature = signature
        elif signature != frozen_signature:
            raise ValueError("battery parameters must remain frozen")
        reports[name] = run_walk_forward(observations, config, ledger_factory)
    return reports
