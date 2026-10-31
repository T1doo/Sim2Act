import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import insert, select, update
from test_natural_live_admission import started
from test_pb_spec_production_controller import prepare_pb

from sim2act import model_settlement as settlement
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime
from sim2act.db import attempts, events, runs
from sim2act.errors import DomainError
from sim2act.spec_production import ProductionTrialBinding


def test_old_caps_serialized_contract_is_never_upgraded(env, tmp_path):
    data, selected = prepare_pb(env, tmp_path)
    raw = selected.contract.model_dump()
    assert type(gate.parse_contract(raw).caps) is gate.SQLiteSettlementCaps
    raw["caps"] = gate.TrialCaps().model_dump()
    parsed = gate.parse_contract(raw)
    assert type(parsed.caps) is gate.TrialCaps and parsed.model_dump() == raw
    data[2].close()


@pytest.fixture
def received(env, tmp_path):
    data, selected = prepare_pb(env, tmp_path)
    job = started(data, selected.contract)
    worker = SimpleNamespace(store=data[0], s=data[1], id=job["worker_id"],
        stop=threading.Event(), pa_trial=ProductionTrialBinding(selected.contract,
            selected.approval_key, selected.account_id))
    deadline = job["created_at"] + 300
    aid = "attempt_" + "a" * 32
    with worker.store.tx() as c:
        c.execute(insert(attempts).values(id=aid, run_id=job["id"], status="RECEIVED",
            parameters={"natural_spec": dict(fence=job["fence"],
                run_version=job["version"], deadline=deadline)}))
    state = dict(lock=threading.Lock(), lease_until=job["lease_until"], deadline=deadline)
    yield worker, job, aid, deadline, state
    data[2].close()


def test_one_finite_committed_interval_then_shortening(received):
    worker, job, aid, deadline, state = received
    with settlement.interval(worker, job, aid, deadline, state):
        with worker.store.tx() as c:
            lease = c.execute(select(runs.c.lease_until).where(runs.c.id == job["id"])).scalar_one()
        assert 110 < lease - time.time() <= 120
        assert lease <= deadline and state["lease_until"] == lease
        settlement.checkpoint(worker)
    with worker.store.tx() as c:
        normal = c.execute(select(runs.c.lease_until).where(runs.c.id == job["id"])).scalar_one()
        kinds = c.execute(select(events.c.kind).where(events.c.run_id == job["id"])).scalars().all()
    assert 0 < normal - time.time() <= 30 and state["lease_until"] == normal
    assert kinds.count(settlement.RESERVED) == kinds.count(settlement.RELEASED) == 1
    with pytest.raises(DomainError, match="already reserved"):
        with settlement.interval(worker, job, aid, deadline, state):
            pytest.fail("No second interval for one attempt")


@pytest.mark.parametrize("damage", ["expired", "cancelled", "owner", "version", "stop"])
def test_never_revives_changed_or_expired_owner(received, damage):
    worker, job, aid, deadline, state = received
    fields = {"expired": {"lease_until": time.time()-1}, "cancelled": {"cancel_intent": True},
        "owner": {"worker_id": "other"}, "version": {"version": job["version"]+1}, "stop": {}}
    with worker.store.tx() as c:
        if fields[damage]:
            c.execute(update(runs).where(runs.c.id == job["id"]).values(**fields[damage]))
    if damage == "stop":
        worker.stop.set()
    with pytest.raises(DomainError):
        with settlement.interval(worker, job, aid, deadline, state):
            pytest.fail("Invalid owner admitted")
    with worker.store.tx() as c:
        assert c.execute(select(events.c.id).where(events.c.kind == settlement.RESERVED)).first() is None


def test_stop_during_interval_fails_and_keeps_terminal_lease_zero(received):
    worker, job, aid, deadline, state = received
    with pytest.raises(DomainError, match="Finite model settlement"):
        with settlement.interval(worker, job, aid, deadline, state):
            worker.stop.set()
            with worker.store.tx() as c:
                c.execute(update(runs).where(runs.c.id == job["id"]).values(status="CANCELLED", lease_until=0))
            settlement.checkpoint(worker)
    with worker.store.tx() as c:
        assert c.execute(select(runs.c.lease_until).where(runs.c.id == job["id"])).scalar_one() == 0
    assert not hasattr(worker, "_settlement_interval")


def test_cleanup_failure_never_rejects_an_already_committed_result(received, monkeypatch):
    worker, job, aid, deadline, state = received
    original = worker.store.event
    def event(c, run_id, kind, data):
        if kind == settlement.RELEASED:
            raise DomainError("VERSION_CONFLICT", "Synthetic release failure")
        return original(c, run_id, kind, data)
    monkeypatch.setattr(worker.store, "event", event)
    with settlement.interval(worker, job, aid, deadline, state):
        with worker.store.tx() as c:
            c.execute(update(attempts).where(attempts.c.id == aid).values(status="VERIFIED"))
    assert worker.stop.is_set() and isinstance(state["fatal_heartbeat"], DomainError)
    with worker.store.tx() as c:
        assert c.execute(select(attempts.c.status).where(attempts.c.id == aid)).scalar_one() == "VERIFIED"


def test_monotonic_budget_survives_wall_clock_rollback(received, monkeypatch):
    worker, job, aid, deadline, state = received
    with pytest.raises(DomainError, match="Finite model settlement"):
        with settlement.interval(worker, job, aid, deadline, state):
            limit = worker._settlement_interval[0]
            monkeypatch.setattr(settlement, "time", SimpleNamespace(
                time=lambda: job["created_at"] - 3600, monotonic=lambda: limit + .1))
            settlement.checkpoint(worker)


def test_reservation_cannot_cross_original_lease_during_event(received, monkeypatch):
    worker, job, aid, deadline, state = received
    original = worker.store.event
    def event(c, run_id, kind, data):
        result = original(c, run_id, kind, data)
        if kind == settlement.RESERVED:
            monkeypatch.setattr(settlement, "time", SimpleNamespace(
                time=lambda: job["lease_until"] + .1, monotonic=time.monotonic))
        return result
    monkeypatch.setattr(worker.store, "event", event)
    with pytest.raises(DomainError, match="expired before commit"):
        with settlement.interval(worker, job, aid, deadline, state):
            pytest.fail("Expired original interval extended")
    with worker.store.tx() as c:
        assert c.execute(select(events.c.id).where(events.c.kind == settlement.RESERVED)).first() is None


def test_writer_reentry_rejects_before_reservation_without_deadlock(received, monkeypatch):
    worker, job, aid, deadline, state = received
    @contextmanager
    def booking(*args):
        with pytest.raises(DomainError, match="cannot reenter"):
            with runtime._model_settlement_writer(worker, job, deadline, None, attempt_id=aid):
                pytest.fail("Reentrant writer entered")
        yield
    monkeypatch.setattr(settlement, "interval", booking)
    with runtime._model_settlement_writer(worker, job, deadline, None, attempt_id=aid):
        pass
    assert worker._settlement_lock.acquire(blocking=False)
    worker._settlement_lock.release()


def test_reservation_commit_callback_cannot_spend_original_owner_interval(received,monkeypatch):
    from sqlalchemy import event
    worker,job,aid,deadline,state=received
    original=worker.store.event
    def booked(c,rid,kind,data):
        value=original(c,rid,kind,data)
        if kind==settlement.RESERVED:event.listen(c,'commit',lambda _:worker.stop.set())
        return value
    monkeypatch.setattr(worker.store,'event',booked)
    with pytest.raises(DomainError,match='expired before commit'):
        with settlement.interval(worker,job,aid,deadline,state):
            pytest.fail('Stopped booking must not publish the extended lease')
    assert state['lease_until']==job['lease_until'] and not hasattr(worker,'_settlement_interval')
    with worker.store.tx() as c:
        assert c.execute(select(events.c.id).where(events.c.kind==settlement.RESERVED)).first() is None
        assert c.execute(select(runs.c.lease_until).where(runs.c.id==job['id'])).scalar_one()==job['lease_until']
