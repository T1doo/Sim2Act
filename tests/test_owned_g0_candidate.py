"""Synthetic SQLite ownership and dynamic-epoch checks; no model execution."""

# ruff: noqa: F811

import time

import pytest
from accounted_sqlite_fixture import seed_cold
from sqlalchemy import select, update
from test_cold_accounted_sqlite import sql_facts  # noqa: F401

from sim2act import natural_live_admission as gate
from sim2act import pb_natural_specs as pb
from sim2act._immutable_settlement import UnsupportedPlan
from sim2act._owned_g0_candidate import MockCandidate, prewrite
from sim2act.db import grants, runs
from sim2act.errors import DomainError


def prepared(f):
    seed_cold(f)
    candidate = MockCandidate()
    platform = gate._limits(f.contract)
    call = dict(meta=dict(deadline=time.time() + 30), wire=b"synthetic request", values=[1])
    plan = candidate.prepare(f.worker, f.cold_bound, call, platform)
    assert plan is not None
    return candidate, plan, call, platform


def test_plan_private_data_and_read_scope_complete_inputs(sql_facts):
    f = sql_facts
    candidate, plan, call, platform = prepared(f)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with prewrite(candidate, plan, f.worker, c, f.cold_job, call, platform) as scope:
            assert scope.private["call"] is not call
            assert scope.private["call"]["values"] is not call["values"]
            scope.call(lambda: c.execute(select(runs.c.id)).all())
            assert scope.sql_calls == 1
            scope.hold("public_return", {"large": ["synthetic" * 1000] * 200})
            scope.check()
        assert not scope.active
        with pytest.raises(DomainError):
            scope.check()
    assert candidate.selected == 1


def test_changed_inputs_before_writer_not_accepted(sql_facts):
    f = sql_facts
    candidate, plan, call, platform = prepared(f)
    call["values"].append(2)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError, match="before writer"):
            with prewrite(candidate, plan, f.worker, c, f.cold_job, call, platform):
                pytest.fail("Changed precomputed input entered business execution")
    assert candidate.selected == 0


@pytest.mark.parametrize("change", ["private", "original", "returned", "stop", "transaction_write"])
def test_scope_changes_reject_and_sql_writes_rollback(sql_facts, change):
    f = sql_facts
    candidate, plan, call, platform = prepared(f)
    before = None
    with f.store.tx() as c:
        before = c.execute(select(grants.c.revoked).order_by(grants.c.id)).scalars().all()
    with pytest.raises(DomainError):
        with f.store.tx() as c, pb._source_reads(f.store, c):
            with prewrite(candidate, plan, f.worker, c, f.cold_job, call, platform) as scope:
                output = scope.hold("output", {"values": [1]})
                if change == "private":
                    scope.private["call"]["values"].append(2)
                elif change == "original":
                    call["values"].append(2)
                elif change == "returned":
                    output["values"].append(2)
                elif change == "stop":
                    f.worker.stop.set()
                else:
                    c.execute(update(grants).values(revoked=True))
                scope.check()
    with f.store.tx() as c:
        assert c.execute(select(grants.c.revoked).order_by(grants.c.id)).scalars().all() == before


def test_unknown_changed_public_function_is_not_qualified(monkeypatch):
    from sim2act import pa_spec_apps as spec

    monkeypatch.setattr(spec, "bound", lambda *a: None)
    with pytest.raises(UnsupportedPlan):
        MockCandidate()


def test_same_source_other_function_does_not_qualify_target_slot(monkeypatch):
    from sim2act import pa_spec_apps as spec

    monkeypatch.setattr(spec, "receipts", spec.commit_guard)
    with pytest.raises(UnsupportedPlan, match="target slot"):
        MockCandidate()


def test_mutated_current_top_level_is_observed(sql_facts):
    f = sql_facts
    candidate, plan, call, platform = prepared(f)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with prewrite(candidate, plan, f.worker, c, f.cold_job, call, platform):
                f.cold_job["fence"] += 1


def test_added_sql_callback_is_rejected_without_calling_it(sql_facts):
    from sqlalchemy import event

    f = sql_facts
    candidate, plan, call, platform = prepared(f)

    def unknown(*args):
        pytest.fail("Unqualified SQL callback invoked")

    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with prewrite(candidate, plan, f.worker, c, f.cold_job, call, platform) as scope:
                event.listen(c, "before_cursor_execute", unknown)
                try:
                    scope.check()
                finally:
                    event.remove(c, "before_cursor_execute", unknown)


def test_constructor_before_default_tampering_is_not_a_baseline(monkeypatch):
    from sim2act import pa_spec_apps as spec

    fn = spec.receipts.__wrapped__
    altered = dict(fn.__kwdefaults__, allow_pending=True)
    monkeypatch.setattr(fn, "__kwdefaults__", altered)
    with pytest.raises(UnsupportedPlan, match="declared default"):
        MockCandidate()
