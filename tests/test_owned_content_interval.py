"""Memory observer folding, not cached DB authorization or a full model run."""

import sys
import time

import pytest
from sqlalchemy import select
from test_cold_accounted_sqlite import sql_facts  # noqa: F401
from test_model_settlement_interval import received  # noqa: F401
from test_owned_g0_candidate import prepared

from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime
from sim2act import pb_natural_specs as pb
from sim2act._owned_g0_candidate import MockCandidate, _received_attempt, prewrite
from sim2act.db import runs
from sim2act.errors import DomainError
from sim2act.worker import Worker


@pytest.mark.parametrize("private_driver", [False, True])
@pytest.mark.parametrize("claim", ["flag", "foreign_frame"])
def test_unknown_callee_flag_aba_cannot_fold_content(sql_facts, private_driver, claim):
    f = sql_facts
    candidate, plan, call, platform = prepared(f)
    manager = candidate.connection(f.worker, plan) if private_driver else f.store.tx()
    with pytest.raises(DomainError):
        with manager as value:
            c = value[0] if private_driver else value
            with pb._source_reads(f.store, c):
                with prewrite(candidate, plan, f.worker, c, f.cold_job, call, platform) as scope:
                    def unknown():
                        scope.reduced = True  # A flag is not a fixed callee frame.
                        if claim == "foreign_frame":
                            scope.call_frame = sys._getframe()
                        scope.private["call"]["values"].append(2)
                        try:
                            c.execute(select(runs.c.id)).all()
                        finally:
                            scope.private["call"]["values"].pop()
                    scope.call(unknown)
    if private_driver:
        assert candidate.transactions[-1]["outcome"] == "ROLLED_BACK"


@pytest.mark.parametrize("field", ["original", "private", "current", "held"])
def test_normal_return_still_checks_complete_content(sql_facts, field):
    f = sql_facts
    candidate, plan, call, platform = prepared(f)
    with pytest.raises(DomainError):
        with candidate.connection(f.worker, plan) as (c, _), pb._source_reads(f.store, c):
            with prewrite(candidate, plan, f.worker, c, f.cold_job, call, platform) as scope:
                held = scope.hold("new-result", {"items": [1]})
                def unknown():
                    if field == "original":
                        call["values"].append(2)
                    elif field == "private":
                        scope.private["call"]["values"].append(2)
                    elif field == "current":
                        scope.current["context"] = {"changed": True}
                    else:
                        held["items"].append(2)
                scope.call(unknown)
    assert candidate.transactions[-1]["outcome"] == "ROLLED_BACK"


@pytest.mark.parametrize("private_driver", [False, True])
def test_full_data_request_cannot_be_disabled_outside_fixed_call(sql_facts, private_driver):
    f = sql_facts
    candidate, plan, call, platform = prepared(f)
    with pytest.raises(DomainError):
        manager = candidate.connection(f.worker, plan) if private_driver else f.store.tx()
        with manager as value:
            c = value[0] if private_driver else value
            with pb._source_reads(f.store, c):
                with prewrite(candidate, plan, f.worker, c, f.cold_job, call, platform) as scope:
                    scope.reduced = True
                    call["values"].append(2)
                    scope.check(full_code=False, full_data=False)
    if private_driver:
        assert candidate.transactions[-1]["outcome"] == "ROLLED_BACK"


def test_real_fixed_reader_under_private_writer_lifetime(received, sql_facts):
    """One original SELECT; real locks/driver/token, zero Worker/model calls."""
    f = sql_facts
    prepared(f)  # Reuse an original valid compiler input only.
    received_worker, job, aid, deadline, state = received
    worker = object.__new__(Worker)  # Identity shell; never construct/run a Worker.
    for key, value in vars(received_worker).items():
        setattr(worker, key, value)
    worker.goal_planner_transport = None
    worker._journal_trial_store = worker.store
    worker._journal_trial_binding = worker.pa_trial
    worker._journal_trial_drift = False
    candidate = MockCandidate()
    worker._owned_g0_candidate = candidate
    state["sync_contention_recovery"] = True
    original_run = dict(job)
    platform = gate._limits(worker.pa_trial.contract)
    call = dict(call_run=original_run, aid=aid,
        meta=dict(deadline=deadline, operation_id="synthetic-memory-observer"),
        values=["synthetic" * 1000] * 200)
    plan = candidate.prepare(worker, f.cold_bound, call, platform)
    assert plan is not None
    with runtime._model_settlement_writer(worker, job, deadline, state,
            attempt_id=aid, _original_run=original_run) as token:
        with candidate.connection(worker, plan) as (c, selected), pb._source_reads(worker.store, c):
            assert selected is plan
            with prewrite(candidate, plan, worker, c, job, call, platform,
                    _writer_epoch=token) as scope:
                private_call = scope.private["call"]
                row = scope.call(_received_attempt, c, private_call["aid"], scope.current["id"])
                assert row["id"] == aid and row["status"] == "RECEIVED"
                assert scope.sql_calls == 1
                assert scope.call_frame is None and not scope.reduced
                scope.hold("received", row)
                assert scope.writer_current() and time.time() < scope.end
            assert not scope.active
    assert not scope.writer_current()
    assert candidate.timings[-1]["reduced_sql"] is True
    assert candidate.timings[-1]["folded_data"] is True
    assert candidate.timings[-1]["folded_sql_checks"] == 2
    assert candidate.transactions[-1]["outcome"] == "COMMITTED"
