"""Run with: python -m unittest discover -s experiments/reference -p 'test_*.py'."""
import math
import unittest

from asde_walk_forward import (
    LedgerSnapshot,
    Observation,
    Preregistration,
    run_frozen_battery,
    run_walk_forward,
)


class ConservationLedger:
    """Test double standing in for the separately audited Emergenzix ledger."""

    calls = []

    def reset(self, initial_capital):
        self.equity = initial_capital
        self.peak = initial_capital

    def apply_period(self, *, timestamp, market, allocation, asset_return,
                     fee_rate, slippage_rate):
        start = self.equity
        pnl = start * allocation * asset_return
        costs = start * allocation * (fee_rate + slippage_rate)
        self.equity = start + pnl - costs
        assert math.isclose(self.equity, start + pnl - costs)
        self.peak = max(self.peak, self.equity)
        drawdown = 1 - self.equity / self.peak
        self.calls.append((timestamp, market, allocation, fee_rate, slippage_rate))
        return LedgerSnapshot(self.equity, drawdown, {"conservation_checked": True})


def rows(count=22):
    prices = [100.0]
    pattern = (0.02, 0.01, -0.005, 0.015, -0.01)
    for index in range(count - 1):
        prices.append(prices[-1] * (1 + pattern[index % len(pattern)]))
    return [Observation(f"2026-01-{index + 1:02d}", "BTCUSDT", price, 1000 + index)
            for index, price in enumerate(prices)]


def config(**overrides):
    values = dict(market="BTCUSDT", start_timestamp="2026-01-01",
                  initial_capital=1000, train_size=10, validation_size=4,
                  test_size=5, fee_rate=0.001, slippage_rate=0.001,
                  min_state_samples=1)
    values.update(overrides)
    return Preregistration(**values)


class WalkForwardTests(unittest.TestCase):
    def setUp(self):
        ConservationLedger.calls = []

    def test_all_baselines_and_ablations_are_preserved(self):
        report = run_walk_forward(rows(), config(), ConservationLedger)
        self.assertEqual(set(report.runs), {
            "asde", "cash", "buy_hold", "fixed_trend", "ablation_no_state",
            "ablation_no_rolling", "ablation_uniform_probability",
            "ablation_double_cost",
        })
        self.assertEqual(report.evidence_level, "CONJECTURE / UNVALIDATED")
        self.assertEqual(len(report.runs["asde"].periods), 9)

    def test_outputs_audit_candidates_equity_drawdown_tail_and_brier(self):
        report = run_walk_forward(rows(), config(), ConservationLedger)
        run = report.runs["asde"]
        self.assertTrue(math.isfinite(run.brier_score))
        self.assertGreaterEqual(run.max_drawdown, 0)
        self.assertGreaterEqual(run.tail_loss, 0)
        self.assertTrue(any(period.candidates for period in run.periods))
        self.assertTrue(all(period.equity > 0 for period in run.periods))

    def test_sparse_state_falls_back_to_no_trade(self):
        report = run_walk_forward(rows(), config(min_state_samples=99), ConservationLedger)
        periods = report.runs["asde"].periods
        self.assertTrue(all(period.selected_allocation == 0 for period in periods))
        self.assertTrue(all(period.fallback_reason.startswith("no-trade") for period in periods))

    def test_costs_are_identical_for_main_and_baselines(self):
        run_walk_forward(rows(), config(), ConservationLedger)
        normal = {(fee, slip) for _, _, _, fee, slip in ConservationLedger.calls}
        self.assertIn((0.001, 0.001), normal)
        self.assertIn((0.002, 0.002), normal)  # only the named double-cost ablation

    def test_market_and_time_order_are_frozen(self):
        bad = rows()
        bad[5] = Observation(bad[5].timestamp, "ETHUSDT", bad[5].close, bad[5].volume)
        with self.assertRaises(ValueError):
            run_walk_forward(bad, config(), ConservationLedger)
        with self.assertRaises(ValueError):
            run_walk_forward(list(reversed(rows())), config(), ConservationLedger)

    def test_start_timestamp_is_preregistered(self):
        with self.assertRaises(ValueError):
            run_walk_forward(rows(), config(start_timestamp="2025-12-31"), ConservationLedger)

    def test_only_injected_ledger_books_equity(self):
        report = run_walk_forward(rows(), config(), ConservationLedger)
        expected_calls = 8 * (config().validation_size + config().test_size)
        self.assertEqual(len(ConservationLedger.calls), expected_calls)
        self.assertTrue(report.warnings[-1].endswith("no PAPER or LIVE permission."))

    def test_cross_market_battery_freezes_parameters_and_keeps_all_results(self):
        eth = [Observation(row.timestamp, "ETHUSDT", row.close, row.volume)
               for row in rows()]

        def frozen(name, observations):
            return config(market=observations[0].market)

        reports = run_frozen_battery(
            {"btc-2026": rows(), "eth-2026": eth}, frozen, ConservationLedger
        )
        self.assertEqual(set(reports), {"btc-2026", "eth-2026"})

        def changed(name, observations):
            return config(market=observations[0].market,
                          fee_rate=0.002 if name.startswith("eth") else 0.001)

        with self.assertRaises(ValueError):
            run_frozen_battery(
                {"btc-2026": rows(), "eth-2026": eth}, changed, ConservationLedger
            )


if __name__ == "__main__":
    unittest.main()
