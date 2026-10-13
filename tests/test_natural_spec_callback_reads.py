"""Exact event boundaries: row-cell observations, never a concurrent attack claim."""

import json
import sqlite3
import time

import pytest
from sql_private_barrier import PrivateReadBarrier
from sqlalchemy import select, update
from test_natural_spec_apps import enqueue, ready, setup, transport

from sim2act import pa_spec_apps as spec
from sim2act.db import attempts, grants, internal_instance_data, operations, runs
from sim2act.errors import DomainError
from sim2act.worker import Worker


class ObservedCells(PrivateReadBarrier):
    """Let SQLite evaluate cells and record actual values only while armed.

    The inherited guarded views evaluate a UDF per requested cell. This observer
    does not reject reads, so the production authorization failure still occurs.
    Synthetic source text is the protected sentinel; no customer data is used.
    """

    armed = False

    def _authorize(self, action, table, column, database, source):
        # Observation only: preserve real UPDATE ... response IS NULL CAS.
        # SELECTs still pass through the inherited value-evaluating TEMP views.
        return sqlite3.SQLITE_OK

    def _cell(self, table, rid, column, value):
        if self.armed and rid in self.rules[table][2]:
            self.evaluated.append(dict(table=table, row_id=rid, column=column,
                                       nonempty=bool(value),
                                       synthetic_sentinel="desk lamp" in str(value)))
        return value


@pytest.mark.parametrize("boundary", ["SPEC_STEP_VERIFIED", "SPEC_COMMITTED"])
@pytest.mark.parametrize("change", ["expiry", "injected_revoke"])
def test_event_authority_change_precedes_private_cell_evaluation(
    env, monkeypatch, tmp_path, boundary, change
):
    data = setup(env)
    store, settings = data[:2]
    origin, _, release, inst, _ = ready(data)
    clock = [time.time()]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    # Freeze the finite lifetime before the tested runtime Run is enqueued.
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == data[5])
                  .values(expires_at=clock[0] + 1))
    job = enqueue(data, release, inst)
    sent = []
    worker = Worker(store, settings, goal_planner_transport=transport(sent))
    run = store.claim(worker.id, settings.lease_seconds)
    assert run["id"] == job
    barrier = ObservedCells(store, {origin, job}, {data[5]})
    barrier.rules["attempts"] = (
        attempts, "run_id", {origin, job}, {"parameters", "response", "usage"}
    )
    original_event = store.event
    reached = []

    def event(c, rid, kind, value=None):
        result = original_event(c, rid, kind, value)
        if rid == job and kind == boundary and (
            boundary == "SPEC_COMMITTED" or value["step_id"] == "infer_pick"
        ):
            assert not reached
            reached.append(kind)
            if change == "expiry":
                clock[0] += 2
            else:
                c.execute(update(grants).where(grants.c.resource_id == data[5])
                          .values(revoked=True))
            # New runtime operations were created after the observer was set up.
            barrier.rules["operation_intents"][2].update(c.execute(
                select(operations.c.id).where(operations.c.run_id == job)).scalars())
            assert clock[0] < run["lease_until"]
            assert clock[0] < run["created_at"] + settings.run_seconds
            barrier.statements.clear()
            barrier.armed = True
        return result

    monkeypatch.setattr(store, "event", event)
    with barrier:
        # Calibrate real row evaluation against nonempty synthetic protected data.
        barrier.armed = True
        with store.engine.connect() as c:
            c.execute(select(attempts).where(attempts.c.run_id == origin)).mappings().all()
        calibration = list(barrier.evaluated)
        assert any(cell["synthetic_sentinel"] for cell in calibration)
        assert {cell["column"] for cell in calibration} == {"parameters", "response", "usage"}
        barrier.evaluated.clear()
        barrier.armed = False
        with pytest.raises(DomainError) as failure:
            for _ in range(4):
                spec.advance(worker, run)
        barrier.armed = False
        observed = list(barrier.evaluated)
        proof = dict(boundary=boundary, change=change, reached=reached,
                     error=failure.value.code, observed=observed, calibration=calibration,
                     lease_valid=clock[0] < run["lease_until"],
                     deadline_valid=clock[0] < run["created_at"] + settings.run_seconds,
                     sql=list(barrier.statements), real_model_requests=0)
        (tmp_path / "callback-private-cells.json").write_text(json.dumps(proof, indent=2))
    assert reached == [boundary]
    assert failure.value.code == "GRANT_REVOKED"
    with store.tx() as c:
        assert not c.execute(select(internal_instance_data).where(
            internal_instance_data.c.instance_id == inst["id"])).first()
        assert c.execute(select(runs.c.status).where(runs.c.id == job)).scalar_one() != "SUCCEEDED"
        if boundary == "SPEC_STEP_VERIFIED":
            assert c.execute(select(attempts.c.status).where(attempts.c.run_id == job)).scalar_one() == "REJECTED_KNOWN"
            assert c.execute(select(operations.c.receipt).where(
                operations.c.run_id == job, operations.c.call_id == "infer_pick"
            )).scalar_one() is None
    assert len(sent) == 1
    assert observed == [], "Authorization must be checked before private cells are evaluated"
