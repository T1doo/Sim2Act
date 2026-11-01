"""Actual main/control commits through Store, not a fake delegate."""
import threading
import time

import pytest
from sqlalchemy import select

from sim2act import _lease_control as control
from sim2act.db import runs
from sim2act.errors import DomainError
from test_foundation import enqueue


def owner(env, *, seconds=30):
    store, settings = env[:2]
    from dataclasses import replace
    settings = replace(settings, lease_seconds=seconds)
    runtime = store._enable_authoritative_leases(settings, create=True)
    rid = enqueue(env, "actual-controlled-main")
    stop = threading.Event()
    row = store.claim("real-fenced-worker", settings.lease_seconds, _owner_stop=stop)
    if control.CONTEXT not in row["context"]:
        row = runtime.bind_claim(row, owner_stop=stop)
    assert row["id"] == rid
    return store, runtime, row, stop


def test_real_renewals_allow_commit_past_historical_anchor_while_main_writer_held(env):
    store, runtime, row, stop = owner(env, seconds=1)
    done = threading.Event()
    failures, publications = [], []
    def renew():
        while not done.wait(.12):
            try:
                publications.append(runtime.heartbeat(row["worker_id"], row["id"], row["fence"], row["version"], 1))
            except BaseException as error:
                failures.append(error)
                return
    thread = threading.Thread(target=renew)
    thread.start()
    try:
        with store.tx() as c:
            store.guard(c, row["id"], row["fence"])
            store.event(c, row["id"], "RENEWED_REAL_WRITER_EFFECT", {"value": 30})
            assert not done.wait(1.4)
            assert time.time() > row["lease_until"] and len(publications) >= 3 and not failures
            store.guard(c, row["id"], row["fence"])
    finally:
        done.set(); thread.join(3)
    assert not thread.is_alive() and not failures
    with store.engine.connect() as c:
        assert c.exec_driver_sql("SELECT count(*) FROM events WHERE kind='RENEWED_REAL_WRITER_EFFECT'").scalar_one() == 1
        assert c.exec_driver_sql("SELECT lease_until FROM runs WHERE id=?", (row["id"],)).scalar_one() == row["lease_until"]


def test_normal_command_publishes_durable_cancel_before_waiting_for_main_writer(env):
    store, runtime, row, stop = owner(env)
    errors, replies = [], []
    def cancel():
        try: replies.append(store.command(row["principal_id"], row["id"], "cancel", row["version"]))
        except BaseException as error: errors.append(error)
    thread = threading.Thread(target=cancel)
    try:
        with pytest.raises(DomainError):
            with store.tx() as c:
                store.guard(c, row["id"], row["fence"])
                store.event(c, row["id"], "CANCELLED_WRITER_EFFECT", {})
                thread.start()
                deadline = time.monotonic()+3
                while True:
                    with runtime.authority.connection() as authority:
                        intent = authority.execute("SELECT intent FROM leases WHERE run_id=?", (row["id"],)).fetchone()[0]
                    if intent == "cancel": break
                    assert time.monotonic() < deadline
                    time.sleep(.01)
    finally:
        thread.join(5)
    assert not thread.is_alive() and not errors and replies == ["CANCEL_REQUESTED"]
    assert store.claim("recovery-worker", 30) is None
    assert runtime.committed_run(row["id"])["status"] == "CANCELLED"
    with store.engine.connect() as c:
        assert c.exec_driver_sql("SELECT count(*) FROM events WHERE kind='CANCELLED_WRITER_EFFECT'").scalar_one() == 0


def test_expired_owner_reconciles_and_new_claim_never_reissues_old_session(env):
    store, runtime, row, stop = owner(env, seconds=1)
    time.sleep(1.05)
    fresh = store.claim("replacement-worker", 1)
    assert fresh["id"] == row["id"] and fresh["fence"] > row["fence"]
    assert control.CONTEXT not in fresh["context"]
    with pytest.raises(DomainError):
        runtime.session(row)
    with pytest.raises(DomainError):
        with store.tx() as c:
            store.guard(c, row["id"], row["fence"])


@pytest.mark.parametrize("failure", ["stop", "expiry", "storage"])
def test_original_final_callback_cannot_authorize_late_commit(env, failure):
    store, runtime, row, stop = owner(env, seconds=1 if failure == "expiry" else 30)
    path = runtime.authority.path
    moved = path.with_suffix(".owned-temporary-unavailable")
    def clock():
        if failure == "stop":
            stop.set()
        elif failure == "expiry":
            time.sleep(1.05)
        else:
            path.rename(moved)
    try:
        with pytest.raises((DomainError, ValueError, OSError)):
            with store.tx(_commit_clock_check=clock) as c:
                store.guard(c, row["id"], row["fence"])
                store.event(c, row["id"], "LATE_CALLBACK_EFFECT", {})
    finally:
        if moved.exists(): moved.rename(path)
    with store.engine.connect() as c:
        assert c.exec_driver_sql("SELECT count(*) FROM events WHERE kind='LATE_CALLBACK_EFFECT'").scalar_one() == 0
        assert c.exec_driver_sql("SELECT count(*) FROM local_lease_control_receipts").scalar_one() == 0


def test_reopen_retires_expired_owner_without_replaying_committed_effect(env):
    from sim2act.db import Store
    store, runtime, row, stop = owner(env, seconds=1)
    with store.tx() as c:
        store.guard(c, row["id"], row["fence"])
        store.event(c, row["id"], "DURABLE_NO_REPLAY", {})
    store.engine.dispose()
    time.sleep(1.05)
    cold = Store(env[1].database_url, test_only=True)
    try:
        from dataclasses import replace
        selected = cold._enable_authoritative_leases(replace(env[1], lease_seconds=1), create=False)
        with pytest.raises(DomainError): selected.session(row)
        fresh = cold.claim("fresh-process-equivalent-owner", 1)
        assert fresh["id"] == row["id"] and fresh["fence"] > row["fence"]
        with cold.engine.connect() as c:
            assert c.exec_driver_sql("SELECT count(*) FROM events WHERE kind='DURABLE_NO_REPLAY'").scalar_one() == 1
    finally:
        cold.engine.dispose()


def test_refused_project_scope_cannot_publish_a_stop_intent(env):
    from sqlalchemy import update
    from sim2act.db import projects
    store, runtime, row, stop = owner(env)
    with store.tx() as c:
        c.execute(update(projects).where(projects.c.id == row["project_id"]).values(owner_id=env[4]))
    with pytest.raises(DomainError):
        store.command(row["principal_id"], row["id"], "cancel", row["version"])
    with runtime.authority.connection() as c:
        assert c.execute("SELECT intent FROM leases WHERE run_id=?", (row["id"],)).fetchone() == (None,)


@pytest.mark.parametrize("damage", ["marker-null", "marker-list", "claim-null", "header-null", "boolean-fence", "boolean-version"])
def test_saved_json_claim_shapes_fail_with_controlled_domain_error(env, damage):
    from sim2act.natural_spec_runtime import _counter_lease_context
    from sqlalchemy import update
    from sim2act.db import events
    store, runtime, row, stop = owner(env)
    with store.tx() as c:
        actual = dict(row)
        actual["context"] = dict(row["context"])
        if damage.startswith("marker"):
            actual["context"][control.CONTEXT] = None if damage == "marker-null" else []
        else:
            value = dict(header=[row[k] for k in control.HEADER], marker=row["context"][control.CONTEXT])
            if damage == "claim-null": value = None
            elif damage == "header-null": value["header"] = None
            elif damage == "boolean-fence": value["header"][5] = True
            else: value["header"][6] = True
            c.execute(update(events).where(events.c.run_id == row["id"], events.c.kind == "LOCAL_LEASE_CONTROL_CLAIM").values(data=value))
        with pytest.raises(DomainError):
            _counter_lease_context(c, actual)


def test_actual_store_guard_fences_and_acknowledges_its_main_transaction(env):
    store, runtime, row, stop = owner(env)
    with store.tx() as c:
        actual = store.guard(c, row["id"], row["fence"])
        assert actual == row
        store.event(c, row["id"], "CONTROLLED_SYNTHETIC_EFFECT", {"value": 30})
    with runtime.authority.connection() as c:
        assert c.execute("SELECT state FROM commits").fetchall() == [("ACKED",)]
        saved = c.execute("SELECT pending_commit,acked_commit FROM leases WHERE run_id=?", (row["id"],)).fetchone()
        assert saved[0] == saved[1] and saved[0] is not None
    with store.engine.connect() as c:
        assert c.exec_driver_sql("SELECT count(*) FROM local_lease_control_receipts").scalar_one() == 1


def test_cancel_before_final_commit_rolls_back_real_effect_and_receipt(env):
    store, runtime, row, stop = owner(env)
    with pytest.raises(DomainError):
        with store.tx() as c:
            store.guard(c, row["id"], row["fence"])
            store.event(c, row["id"], "MUST_ROLL_BACK", {"value": 30})
            runtime.authority.command(row, "cancel")
    with store.engine.connect() as c:
        assert c.exec_driver_sql("SELECT count(*) FROM events WHERE kind='MUST_ROLL_BACK'").scalar_one() == 0
        assert c.exec_driver_sql("SELECT count(*) FROM local_lease_control_receipts").scalar_one() == 0

