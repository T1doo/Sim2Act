"""Fake clock/selector tests; no launcher, product, transport or database."""

import sys
import tempfile
import unittest

from g0_bounded import supervised_select
from g0_guard import LIMITS, Boundary, Budget, DiskMonitor


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


class Selector:
    def __init__(self, clock, ready_after=None):
        self.clock, self.ready_after = clock, ready_after
        self.timeouts = []

    def select(self, timeout):
        self.timeouts.append(timeout)
        delay = timeout if self.ready_after is None else min(timeout, self.ready_after)
        self.clock.now += delay
        return [] if self.ready_after is None else ["ready"]


class DiskReportUnits(unittest.TestCase):
    def setUp(self):
        root = self.enterContext(tempfile.TemporaryDirectory(prefix="g0-fake-observer-"))
        self.clock = Clock()
        self.disk = DiskMonitor(root, self.clock)
        self.budget = Budget(0, self.clock)

    def tearDown(self):
        self.assertFalse(any(k == "sim2act" or k.startswith("sim2act.") for k in sys.modules))

    def step(self, selector):
        return supervised_select(selector, self.budget, self.disk, None, self.clock)

    def test_idle_selector_is_twenty_hz_not_configured_ten(self):
        selector = Selector(self.clock)
        for _ in range(21):
            self.assertEqual(self.step(selector), [])
        report = self.disk.report()
        self.assertEqual(selector.timeouts, [0.05] * 21)
        self.assertEqual(report["configured_interval_seconds"], 0.1)
        self.assertFalse(report["configured_interval_is_scheduled"])
        self.assertNotIn("interval_seconds", report)
        self.assertAlmostEqual(report["sample_completion_intervals"]["mean"], 0.05)
        self.assertAlmostEqual(report["observed_completion_rate_hz"], 20)
        self.assertEqual(report["sample_completion_intervals"]["count"], 20)

    def test_ready_events_sample_faster_and_are_returned_unchanged(self):
        selector = Selector(self.clock, ready_after=0.001)
        for _ in range(5):
            self.assertEqual(self.step(selector), ["ready"])
        report = self.disk.report()
        self.assertAlmostEqual(report["sample_completion_intervals"]["minimum"], 0.001)
        self.assertAlmostEqual(report["sample_completion_intervals"]["maximum"], 0.001)
        self.assertAlmostEqual(report["observed_completion_rate_hz"], 1000)

    def test_finalization_sample_records_real_gap_without_fixed_interval_claim(self):
        self.step(Selector(self.clock))
        self.clock.now = 0.75
        self.disk.sample()
        report = self.disk.report()
        self.assertEqual(report["sample_completion_intervals"]["maximum"], 0.75)
        self.assertEqual(report["scheduling_policy"], "EVERY_SUPERVISOR_ITERATION_AND_FINALIZATION")

    def test_zero_or_single_or_simultaneous_samples_have_no_invented_rate(self):
        self.assertIsNone(self.disk.report()["observed_completion_rate_hz"])
        self.disk.sample()
        report = self.disk.report()
        self.assertIsNone(report["sample_completion_intervals"]["mean"])
        self.disk.sample()
        report = self.disk.report()
        self.assertEqual(report["sample_completion_intervals"]["mean"], 0)
        self.assertIsNone(report["observed_completion_rate_hz"])

    def test_original_deadline_clamps_select_and_prevents_later_scan(self):
        selector = Selector(self.clock)
        self.clock.now = 479.98
        self.step(selector)
        self.assertAlmostEqual(selector.timeouts[-1], 0.02)
        with self.assertRaises(Boundary):
            self.step(selector)
        self.assertEqual(self.disk.samples, 1)
        self.assertEqual(LIMITS["directory_bytes"], 64 * 1024**2)

    def test_scan_failure_still_prevents_selector_and_propagates(self):
        selector = Selector(self.clock)
        error = Boundary("local scan failure")

        def fail(pid):
            raise error

        self.disk.sample = fail
        with self.assertRaises(Boundary) as caught:
            self.step(selector)
        self.assertIs(caught.exception, error)
        self.assertEqual(selector.timeouts, [])


if __name__ == "__main__":
    unittest.main()
