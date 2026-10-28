"""ASDE: dependency-free, offline finite-scenario reference only.

No exchange API, network call, future data, actual orders, or learned BTC probabilities.
Weights are supplied by the caller; this module never claims their validity.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log
from typing import Sequence


@dataclass(frozen=True)
class Scenario:
    name: str
    return_fraction: float
    probability: float


@dataclass(frozen=True)
class Decision:
    allocation: float
    expected_log_growth: float
    worst_case_return: float
    feasible: bool
    reason: str


def enumerate_decisions(
    scenarios: Sequence[Scenario],
    allocations: Sequence[float] = (0.0, 0.25, 0.5, 1.0),
    round_trip_cost: float = 0.001,
    max_loss: float = 0.10,
) -> list[Decision]:
    """Rank feasible long-only spot allocations under explicit stress scenarios.

    This one-step toy excludes leverage, shorting and liquidation; no deployment use.
    round_trip_cost is a deterministic cost fraction of allocated equity.
    max_loss bounds worst-case one-step equity loss over the supplied scenarios only.
    """
    if not scenarios or not allocations:
        raise ValueError("nonempty scenarios and allocations required")
    if not isfinite(round_trip_cost) or round_trip_cost < 0:
        raise ValueError("invalid cost")
    if not isfinite(max_loss) or not 0 <= max_loss < 1:
        raise ValueError("invalid max_loss")
    if any(not isfinite(s.probability) or s.probability < 0 or
           not isfinite(s.return_fraction) or s.return_fraction < -1
           for s in scenarios):
        raise ValueError("invalid scenario")
    if abs(sum(s.probability for s in scenarios) - 1.0) > 1e-9:
        raise ValueError("probabilities must sum to one")
    if any(not isfinite(a) or not 0 <= a <= 1 for a in allocations):
        raise ValueError("allocations must lie in [0,1]")

    decisions = []
    for a in allocations:
        outcomes = [a * (s.return_fraction - round_trip_cost) for s in scenarios]
        worst = min(outcomes)
        feasible = worst >= -max_loss and all(1 + r > 0 for r in outcomes)
        utility = (sum(s.probability * log(1 + r)
                       for s, r in zip(scenarios, outcomes)) if feasible
                   else float("-inf"))
        decisions.append(Decision(a, utility, worst, feasible,
                                  "within supplied scenario limits" if feasible
                                  else "worst-case loss or ruin constraint"))
    return sorted(decisions, key=lambda d: (-int(d.feasible), -d.expected_log_growth, d.allocation))


def illustrative_scenarios(reference: float = 80_000.0) -> list[Scenario]:
    """Arbitrary example weights, NOT estimated market probabilities."""
    if not isfinite(reference) or reference <= 0:
        raise ValueError("invalid reference price")
    return [Scenario("down_76000", 76_000 / reference - 1, 1 / 3),
            Scenario("flat_80000", 80_000 / reference - 1, 1 / 3),
            Scenario("up_85000", 85_000 / reference - 1, 1 / 3)]


if __name__ == "__main__":
    for decision in enumerate_decisions(illustrative_scenarios()):
        print(decision)
