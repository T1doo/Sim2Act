"""Reject the proposed borrowed-view comparator; no production replacement."""
import threading

from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts
from test_cold_legacy_base_segment import legacy

from sim2act import natural_live_admission as gate


def test_borrowed_values_can_accept_what_original_snapshots_reject(sql_facts):
    with legacy(sql_facts, True) as (_, s):
        left, right = {'value': 1}, {'value': 1}
        s.graph.add('snapshot-boundary-left', left)
        s.graph.add('snapshot-boundary-right', right)
        changed, restore, done = threading.Event(), threading.Event(), threading.Event()
        def mutate():
            left['value'] = right['value'] = 2
            changed.set()
            if restore.wait(5):
                left['value'] = right['value'] = 1
            done.set()
        # The old expression completes its actual snapshot before raw capture.
        actual = gate._trial_pure_data(left)
        thread = threading.Thread(target=mutate)
        thread.start()
        try:
            assert changed.wait(5)
            saved = gate._trial_pure_data(right)
            original = gate._trial_typed_equal(actual, saved)
            borrowed = gate._trial_typed_equal(left, right)
            left_only = gate._trial_typed_equal(left, saved)
        finally:
            restore.set()
            thread.join(5)
        assert done.is_set() and not thread.is_alive()
        assert original is False and borrowed is True and left_only is True
        # Full fresh late encoding sees the original complete frontier again;
        # it does not prove the two comparison algorithms were equivalent.
        s.graph.check(s.graph.store, s.c)


def test_borrowing_only_saved_side_also_loses_its_capture(sql_facts):
    with legacy(sql_facts, True) as (_, s):
        left, right = {'value': 1}, {'value': 2}
        s.graph.add('right-snapshot-left', left)
        s.graph.add('right-snapshot-right', right)
        actual = gate._trial_pure_data(left)
        saved = gate._trial_pure_data(right)
        changed, restore, done = threading.Event(), threading.Event(), threading.Event()
        def mutate():
            right['value'] = 1
            changed.set()
            if restore.wait(5):
                right['value'] = 2
            done.set()
        thread = threading.Thread(target=mutate)
        thread.start()
        try:
            assert changed.wait(5)
            original = gate._trial_typed_equal(actual, saved)
            borrowed_right = gate._trial_typed_equal(actual, right)
        finally:
            restore.set()
            thread.join(5)
        assert done.is_set() and not thread.is_alive()
        assert original is False and borrowed_right is True
        s.graph.check(s.graph.store, s.c)
