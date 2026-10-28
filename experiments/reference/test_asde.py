"""Run with: python -m unittest discover -s experiments/reference -p 'test_*.py'"""
import unittest
from asde import Scenario, enumerate_decisions, illustrative_scenarios


class ASDETests(unittest.TestCase):
    def test_scenarios_valid(self):
        rows = enumerate_decisions(illustrative_scenarios())
        self.assertEqual(len(rows), 4)
        self.assertTrue(rows[0].feasible)

    def test_zero_allocation_neutral(self):
        row = enumerate_decisions([Scenario("crash", -1, 1)], [0])[0]
        self.assertEqual(row.worst_case_return, 0)
        self.assertEqual(row.expected_log_growth, 0)

    def test_loss_limit_blocks_risky_allocation(self):
        rows = enumerate_decisions([Scenario("crash", -0.5, 1)], [0, 1], max_loss=0.1)
        self.assertTrue(rows[0].feasible)
        self.assertFalse(rows[1].feasible)

    def test_invalid_probabilities_fail(self):
        with self.assertRaises(ValueError):
            enumerate_decisions([Scenario("bad", 0.1, 0.5)])

    def test_cost_discourages_trade(self):
        rows = enumerate_decisions([Scenario("flat", 0, 1)], [0, 1], round_trip_cost=0.01)
        self.assertEqual(rows[0].allocation, 0)

    def test_invalid_allocation_fail(self):
        with self.assertRaises(ValueError):
            enumerate_decisions([Scenario("flat", 0, 1)], [1.1])


if __name__ == "__main__":
    unittest.main()
