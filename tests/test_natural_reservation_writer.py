"""Reservation writer ordering with real SQLite commits and no model sender.

Natural recipe/journal hooks are explicit unit stubs here; the original full
P-B controller test remains the business-contract acceptance gate.
"""

import copy
import json
import threading
import time
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from test_foundation import enqueue

from sim2act import natural_spec_runtime as natural
from sim2act import pa_trial_dispatch as trial
from sim2act import text_workflows as flow
from sim2act.db import attempts, reservations, runs
from sim2act.errors import DomainError
from sim2act.worker import Worker


def setup_reservation(env, monkeypatch):
    store, settings = env[:2]
    worker = Worker(store, settings)
    rid = enqueue(env, "natural-reservation-writer")
    run = store.claim(worker.id, settings.lease_seconds)
    assert run["id"] == rid
    state = dict(lock=threading.Lock(), renewal_lock=threading.Lock(),
        lease_until=run["lease_until"], deadline=run["created_at"] + settings.run_seconds)
    meta = dict(created_at=run["created_at"], deadline=state["deadline"])
    monkeypatch.setattr(natural, "reservation_settings", lambda *_: settings)
    monkeypatch.setattr(natural, "reservation_check", lambda *_: None)
    monkeypatch.setattr(natural, "reserve_node", lambda *_: None)
    from sim2act import natural_source_archives
    monkeypatch.setattr(natural_source_archives, "record_request", lambda *_: None)
    return worker, run, state, meta


def test_quota_wait_allows_renewal_and_reservation_excludes_own_background_writer(
        env, monkeypatch, tmp_path):
    worker, run, state, meta = setup_reservation(env, monkeypatch)
    store = worker.store
    worker.pa_trial = SimpleNamespace(contract_fingerprint="unit-journal", approval_key="unit-approval")
    monkeypatch.setattr(trial, "preflight", lambda *_, **__: None)
    monkeypatch.setattr(trial, "reserved", lambda *_: None)
    waiting, acquired = threading.Event(), threading.Event()
    background, errors, evidence = [], [], []

    class ObservedLock:
        def __init__(self):
            self.lock = threading.Lock()

        def __enter__(self):
            if threading.current_thread().name == "reservation-heartbeat":
                waiting.set()
            self.lock.acquire()

        def __exit__(self, *_):
            self.lock.release()

    state["renewal_lock"] = ObservedLock()
    original_heartbeat = store.heartbeat

    def heartbeat(*args, **kwargs):
        assert threading.current_thread() is not threading.main_thread(), (
            "guarded renewal must stay outside the reservation proof observer"
        )
        return original_heartbeat(*args, **kwargs)

    monkeypatch.setattr(store, "heartbeat", heartbeat)

    def quota_wait(*_, **__):
        # The actual guarded heartbeat must commit while quota waiting is open.
        def beat():
            try:
                renewed = flow.renew_sync(worker, run, state, deadline=meta["deadline"])
                evidence.append(dict(phase="quota-wait", committed_lease=renewed))
            except BaseException as exc:
                errors.append(exc)
        thread = threading.Thread(target=beat)
        thread.start()
        thread.join(5)
        assert not thread.is_alive() and not errors
        assert evidence and evidence[-1]["phase"] == "quota-wait"

    monkeypatch.setattr(trial, "wait_unreserved", quota_wait)

    def reservation_check(*_):
        def beat():
            try:
                with state["renewal_lock"]:
                    acquired.set()
                    with store.engine.connect() as c:
                        saved = c.execute(select(attempts.c.status).where(
                            attempts.c.run_id == run["id"])).scalars().all()
                    assert saved == ["STARTED"], "background writer overtook reservation commit"
                    renewed = store.heartbeat(worker.id, run["id"], run["fence"],
                        worker.s.lease_seconds)
                    flow.publish_sync_renewal(worker, run, state, renewed)
                    evidence.append(dict(phase="after-reservation-commit", committed_lease=renewed))
            except BaseException as exc:
                errors.append(exc)
        thread = threading.Thread(target=beat, name="reservation-heartbeat")
        background.append(thread)
        thread.start()
        assert waiting.wait(5) and not acquired.is_set()

    monkeypatch.setattr(natural, "reservation_check", reservation_check)
    context = copy.deepcopy(run["context"])
    aid = worker.reserve(run["id"], run["fence"], context, request_tools=[],
        natural_spec_request=meta, _natural_heartbeat_state=state)
    for thread in background:
        thread.join(5)
        assert not thread.is_alive()
    assert acquired.is_set() and not errors
    assert context["requests"] == 1 and len(evidence) == 2
    with store.tx() as c:
        assert c.execute(select(attempts.c.id).where(attempts.c.run_id == run["id"])).scalars().all() == [aid]
        assert c.execute(select(reservations.c.id).where(reservations.c.run_id == run["id"])).scalars().all() == [aid]
        saved = c.execute(select(runs).where(runs.c.id == run["id"])).mappings().one()
    assert saved["status"] == "RUNNING" and saved["fence"] == run["fence"]
    assert worker.s.lease_seconds == 30 and worker.s.run_seconds == 300
    (tmp_path / "reservation-writer-proof.json").write_text(json.dumps(dict(
        unit_stubs=["natural recipe/journal hooks", "quota wait scheduling"],
        actual_sqlite_reservation_attempt=aid, ordered_commits=evidence,
        original_lease_seconds=30, original_run_seconds=300, real_model_calls=0), indent=2))


@pytest.mark.parametrize("case", ["fatal", "stop", "expired"])
def test_state_changed_while_waiting_for_writer_is_rejected_before_renewal_or_reservation(
        env, monkeypatch, case):
    worker, run, state, meta = setup_reservation(env, monkeypatch)
    fatal = DomainError("VERSION_CONFLICT", "unit sticky heartbeat failure")

    class ChangeOnAcquisition:
        def __enter__(self):
            if case == "fatal":
                state["fatal_heartbeat"] = fatal
            elif case == "stop":
                worker.stop.set()
            else:
                state["lease_until"] = time.time() - 1

        def __exit__(self, *_):
            pass

    state["renewal_lock"] = ChangeOnAcquisition()

    def forbidden(*_, **__):
        raise AssertionError("renewal must not run after failed writer admission")

    monkeypatch.setattr(worker.store, "heartbeat", forbidden)
    with pytest.raises(DomainError) as caught:
        worker.reserve(run["id"], run["fence"], copy.deepcopy(run["context"]), request_tools=[],
            natural_spec_request=meta, _natural_heartbeat_state=state)
    assert caught.value is fatal if case == "fatal" else caught.value.code == "BUDGET_EXHAUSTED"
    with worker.store.tx() as c:
        assert not c.execute(select(attempts.c.id).where(attempts.c.run_id == run["id"])).all()
        assert not c.execute(select(reservations.c.id).where(reservations.c.run_id == run["id"])).all()


def test_wrong_request_family_rejected_before_wait_or_database(env, monkeypatch):
    worker = Worker(env[0], env[1])
    from sim2act import natural_trial_runs

    def forbidden(*_):
        raise AssertionError("wrong-family admission reached database")

    monkeypatch.setattr(natural_trial_runs, "check_worker", forbidden)
    with pytest.raises(DomainError, match="Natural heartbeat has the wrong request family"):
        worker.reserve("wrong-run", 1, {}, _natural_heartbeat_state={})
