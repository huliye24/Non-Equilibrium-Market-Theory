"""Tests for the causal right-side entry research state machine."""

from datetime import datetime, timedelta, timezone
import unittest

from right_side_entry_state import (
    ClosedBar,
    RightSideConfig,
    RightSideState,
    classify_right_side_entry,
)


START = datetime(2025, 1, 1, tzinfo=timezone.utc)


def bar(index: int, open_: float, high: float, low: float, close: float, volume: float) -> ClosedBar:
    return ClosedBar(START + timedelta(hours=4 * index), open_, high, low, close, volume)


def successful_path() -> list[ClosedBar]:
    return [
        bar(0, 98.0, 99.0, 97.5, 98.5, 100),
        bar(1, 98.5, 99.5, 98.0, 99.0, 100),
        bar(2, 99.0, 100.0, 98.8, 99.5, 100),
        bar(3, 99.5, 102.0, 99.4, 101.0, 120),
        bar(4, 101.0, 102.2, 100.4, 101.4, 110),
        bar(5, 101.4, 102.1, 100.6, 101.2, 90),
        bar(6, 101.2, 101.4, 99.8, 100.5, 80),
        bar(7, 100.5, 103.5, 100.4, 103.0, 180),
    ]


class RightSideEntryStateTests(unittest.TestCase):
    def test_states_advance_in_order_and_expose_protective_stop(self) -> None:
        bars = successful_path()
        config = RightSideConfig(stability_bars=2, volume_lookback=3)

        candidate = classify_right_side_entry(bars[:4], 100.0, 2.0, config=config)
        stabilizing = classify_right_side_entry(bars[:6], 100.0, 2.0, config=config)
        retest = classify_right_side_entry(bars[:7], 100.0, 2.0, config=config)
        confirmed = classify_right_side_entry(bars, 100.0, 2.0, config=config)

        self.assertEqual(candidate.state, RightSideState.BREAKOUT_CANDIDATE)
        self.assertEqual(stabilizing.state, RightSideState.STABILIZING)
        self.assertEqual(retest.state, RightSideState.RETEST_HELD)
        self.assertEqual(confirmed.state, RightSideState.REACCELERATION)
        self.assertTrue(confirmed.entry_eligible_next_open)
        self.assertAlmostEqual(confirmed.retest_low or 0.0, 99.8)
        self.assertAlmostEqual(confirmed.protective_stop or 0.0, 99.3)
        self.assertIsNone(confirmed.fixed_profit_target)

    def test_false_breakout_fails_before_entry(self) -> None:
        bars = successful_path()[:4] + [bar(4, 101.0, 101.2, 98.7, 99.0, 150)]
        result = classify_right_side_entry(bars, 100.0, 2.0)
        self.assertEqual(result.state, RightSideState.FAILED)
        self.assertFalse(result.entry_eligible_next_open)

    def test_vertical_move_cannot_skip_retest(self) -> None:
        bars = successful_path()[:6] + [
            bar(6, 101.2, 104.0, 101.0, 103.5, 200),
            bar(7, 103.5, 106.0, 103.0, 105.5, 220),
        ]
        result = classify_right_side_entry(
            bars,
            100.0,
            2.0,
            config=RightSideConfig(stability_bars=2, volume_lookback=3),
        )
        self.assertEqual(result.state, RightSideState.STABILIZING)
        self.assertFalse(result.entry_eligible_next_open)

    def test_future_bar_does_not_change_as_of_decision(self) -> None:
        bars = successful_path()
        as_of = bars[6].closed_at
        result = classify_right_side_entry(
            bars,
            100.0,
            2.0,
            as_of=as_of,
            config=RightSideConfig(stability_bars=2, volume_lookback=3),
        )
        self.assertEqual(result.state, RightSideState.RETEST_HELD)
        self.assertEqual(result.observed_at, as_of)

    def test_rejects_out_of_order_bars(self) -> None:
        bars = successful_path()
        with self.assertRaisesRegex(ValueError, "strictly ordered"):
            classify_right_side_entry([bars[1], bars[0]], 100.0, 2.0)


if __name__ == "__main__":
    unittest.main()
