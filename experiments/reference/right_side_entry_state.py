"""Causal research reference for a right-side breakout entry state machine.

This module only classifies completed bars. It does not place orders or modify
the production signal stack.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from statistics import fmean
from typing import Optional, Sequence


class RightSideState(str, Enum):
    """Ordered states for confirmation after a completed-bar breakout."""

    WAITING_BREAKOUT = "WAITING_BREAKOUT"
    BREAKOUT_CANDIDATE = "BREAKOUT_CANDIDATE"
    STABILIZING = "STABILIZING"
    RETEST_HELD = "RETEST_HELD"
    REACCELERATION = "REACCELERATION"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ClosedBar:
    """One completed OHLCV bar."""

    closed_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class RightSideConfig:
    """Research parameters, intentionally small and interpretable."""

    stability_bars: int = 2
    volume_lookback: int = 20
    reacceleration_volume_ratio: float = 1.20
    retest_tolerance_atr: float = 0.25
    failure_buffer_atr: float = 0.25
    stop_buffer_atr: float = 0.25
    max_wait_bars: int = 12


@dataclass(frozen=True)
class RightSideDecision:
    """Point-in-time state and auditable anchors."""

    state: RightSideState
    reason: str
    observed_at: Optional[datetime]
    breakout_at: Optional[datetime]
    breakout_level: float
    bars_since_breakout: int
    platform_low: Optional[float]
    retest_low: Optional[float]
    reference_volume: Optional[float]
    current_volume_ratio: Optional[float]
    entry_eligible_next_open: bool
    protective_stop: Optional[float]
    fixed_profit_target: Optional[float] = None


def _validate(
    bars: Sequence[ClosedBar],
    breakout_level: float,
    atr: float,
    config: RightSideConfig,
) -> None:
    if breakout_level <= 0 or atr <= 0:
        raise ValueError("breakout_level and atr must be positive")
    if config.stability_bars < 1 or config.volume_lookback < 1:
        raise ValueError("lookbacks must be positive")
    if config.max_wait_bars <= config.stability_bars:
        raise ValueError("max_wait_bars must exceed stability_bars")

    previous: Optional[datetime] = None
    for bar in bars:
        if bar.closed_at.tzinfo is None or bar.closed_at.utcoffset() is None:
            raise ValueError("closed_at must be timezone-aware")
        if previous is not None and bar.closed_at <= previous:
            raise ValueError("bars must be strictly ordered by closed_at")
        if not (bar.low <= min(bar.open, bar.close) <= max(bar.open, bar.close) <= bar.high):
            raise ValueError("invalid OHLC ordering")
        if bar.volume < 0:
            raise ValueError("volume cannot be negative")
        previous = bar.closed_at


def classify_right_side_entry(
    bars: Sequence[ClosedBar],
    breakout_level: float,
    atr: float,
    *,
    as_of: Optional[datetime] = None,
    config: RightSideConfig = RightSideConfig(),
) -> RightSideDecision:
    """Classify the latest completed-bar state without future information.

    A valid path cannot jump directly from breakout to entry. It must show
    stability, a held retest, and then price/volume reacceleration. Entry is
    only eligible at the next bar open after REACCELERATION.
    """

    _validate(bars, breakout_level, atr, config)
    if as_of is not None and (as_of.tzinfo is None or as_of.utcoffset() is None):
        raise ValueError("as_of must be timezone-aware")
    visible = [bar for bar in bars if as_of is None or bar.closed_at <= as_of]
    observed_at = visible[-1].closed_at if visible else None

    def decision(
        state: RightSideState,
        reason: str,
        breakout_at: Optional[datetime] = None,
        bars_since: int = 0,
        platform_low: Optional[float] = None,
        retest_low: Optional[float] = None,
        reference_volume: Optional[float] = None,
        volume_ratio: Optional[float] = None,
    ) -> RightSideDecision:
        stop = None
        eligible = state == RightSideState.REACCELERATION and retest_low is not None
        if eligible:
            stop = retest_low - config.stop_buffer_atr * atr
        return RightSideDecision(
            state=state,
            reason=reason,
            observed_at=observed_at,
            breakout_at=breakout_at,
            breakout_level=breakout_level,
            bars_since_breakout=bars_since,
            platform_low=platform_low,
            retest_low=retest_low,
            reference_volume=reference_volume,
            current_volume_ratio=volume_ratio,
            entry_eligible_next_open=eligible,
            protective_stop=stop,
        )

    breakout_index: Optional[int] = None
    for index, bar in enumerate(visible):
        if bar.close > breakout_level:
            breakout_index = index
            break
    if breakout_index is None:
        return decision(RightSideState.WAITING_BREAKOUT, "no completed close above breakout level")

    breakout_bar = visible[breakout_index]
    breakout_at = breakout_bar.closed_at
    breakout_high = breakout_bar.high
    platform_low = breakout_bar.low
    retest_low: Optional[float] = None
    state = RightSideState.BREAKOUT_CANDIDATE
    bars_since = 0
    tolerance = config.retest_tolerance_atr * atr
    failure_level = breakout_level - config.failure_buffer_atr * atr

    for index in range(breakout_index + 1, len(visible)):
        bar = visible[index]
        bars_since += 1
        platform_low = min(platform_low, bar.low)

        if bar.close < failure_level:
            return decision(
                RightSideState.FAILED,
                "completed close invalidated breakout",
                breakout_at,
                bars_since,
                platform_low,
                retest_low,
            )
        if bars_since > config.max_wait_bars:
            return decision(
                RightSideState.FAILED,
                "confirmation window expired",
                breakout_at,
                bars_since,
                platform_low,
                retest_low,
            )

        if state == RightSideState.BREAKOUT_CANDIDATE:
            breakout_high = max(breakout_high, bar.high)
            if bars_since >= config.stability_bars:
                state = RightSideState.STABILIZING
            continue

        if state == RightSideState.STABILIZING:
            if bar.low <= breakout_level + tolerance and bar.close >= breakout_level:
                retest_low = bar.low
                state = RightSideState.RETEST_HELD
            else:
                breakout_high = max(breakout_high, bar.high)
            continue

        if state == RightSideState.RETEST_HELD:
            if bar.low <= breakout_level + tolerance and bar.close >= breakout_level:
                retest_low = min(retest_low if retest_low is not None else bar.low, bar.low)
            lookback_start = max(0, index - config.volume_lookback)
            prior_volumes = [item.volume for item in visible[lookback_start:index]]
            reference_volume = fmean(prior_volumes) if prior_volumes else None
            volume_ratio = (
                bar.volume / reference_volume
                if reference_volume is not None and reference_volume > 0
                else None
            )
            volume_confirmed = (
                volume_ratio is not None
                and volume_ratio >= config.reacceleration_volume_ratio
            )
            if bar.close > breakout_high and volume_confirmed:
                return decision(
                    RightSideState.REACCELERATION,
                    "held retest followed by price and volume reacceleration",
                    breakout_at,
                    bars_since,
                    platform_low,
                    retest_low,
                    reference_volume,
                    volume_ratio,
                )

    reasons = {
        RightSideState.BREAKOUT_CANDIDATE: "breakout observed; waiting for stability",
        RightSideState.STABILIZING: "breakout held; waiting for a causal retest",
        RightSideState.RETEST_HELD: "retest held; waiting for reacceleration",
    }
    return decision(
        state,
        reasons[state],
        breakout_at,
        bars_since,
        platform_low,
        retest_low,
    )
