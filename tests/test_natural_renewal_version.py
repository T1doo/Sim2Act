"""A still-live fence does not authorize an earlier Run version to renew."""

import threading
import time
from types import SimpleNamespace

import pytest
from sqlalchemy import event, select, update
from test_foundation import enqueue

from sim2act.db import heartbeats, runs
from sim2act.errors import DomainError
from sim2act.natural_spec_runtime import renew


@pytest.mark.parametrize("with_state", [False, True])
def test_natural_renewal_refuses_changed_version_without_publishing(env, with_state):
    store, settings = env[:2]
    rid = enqueue(env, "natural-renewal-version")
    original = store.claim("original-worker", 30)
    worker = SimpleNamespace(store=store, s=settings, id="original-worker", stop=threading.Event())
    deadline = original["created_at"] + settings.run_seconds
    state = dict(lock=threading.Lock(), renewal_lock=threading.Lock(),
                 lease_until=original["lease_until"], deadline=deadline)
    # A committed command can change the Run version without replacing its
    # worker/fence. Neither a numeric lease nor that old fence proves continuity.
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(version=original["version"] + 1))
    before = state.copy()
    with pytest.raises(DomainError, match="Heartbeat Run version changed"):
        renew(worker, original, deadline, _heartbeat_state=state if with_state else None)
    with store.engine.connect() as c:
        saved = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert c.execute(select(heartbeats.c.id).where(heartbeats.c.id == worker.id)).first() is None
    assert saved["lease_until"] == original["lease_until"]
    assert saved["version"] == original["version"] + 1
    assert saved["worker_id"] == worker.id and saved["fence"] == original["fence"]
    assert state == before and "sync_renewal" not in state


def test_natural_renewal_of_current_version_commits_before_publication(env):
    store, settings = env[:2]
    rid = enqueue(env, "natural-renewal-current-version")
    original = store.claim("original-worker", 30)
    worker = SimpleNamespace(store=store, s=settings, id="original-worker", stop=threading.Event())
    deadline = original["created_at"] + settings.run_seconds
    state = dict(lock=threading.Lock(), lease_until=original["lease_until"], deadline=deadline)
    renew(worker, original, deadline, _heartbeat_state=state)
    with store.engine.connect() as c:
        saved = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
    assert time.time() < saved["lease_until"] <= time.time() + 30
    assert saved["lease_until"] == state["lease_until"] == state["sync_renewal"]["lease_until"]
    assert saved["version"] == original["version"]


def test_real_pause_stops_original_natural_background_renewal(env, tmp_path):
    """Real HTTP command and original ten-second heartbeat, no fake clock."""
    from sim2act import text_workflows
    import json

    store, settings, client = env[:3]
    rid = enqueue(env, "natural-background-real-pause")
    original = store.claim("original-worker", 30)
    worker = SimpleNamespace(store=store, s=settings, id="original-worker", stop=threading.Event())
    assert settings.lease_seconds == 30
    state = dict(lock=threading.Lock(), lease_until=original["lease_until"],
                 deadline=None, sync_contention_recovery=True)
    entered, release = threading.Event(), threading.Event()
    errors = []
    def advance(*_):
        entered.set()
        assert release.wait(15)
        return False
    def process():
        try:text_workflows.process_job(worker, original, advance, _heartbeat_state=state)
        except BaseException as exc:errors.append(exc)
    thread = threading.Thread(target=process)
    began = time.monotonic();thread.start()
    try:
        assert entered.wait(3)
        reply = client.post(f"/api/runs/{rid}/commands",
                            json={"command": "pause", "version": original["version"]})
        assert reply.status_code == 200
        with store.engine.connect() as c:
            paused = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        assert paused["status"] == "PAUSE_REQUESTED"
        assert paused["version"] == original["version"] + 1
        assert paused["worker_id"] == worker.id and paused["fence"] == original["fence"]
        until = time.monotonic() + 13
        while time.monotonic() < until:
            with state["lock"]:fatal = state.get("fatal_heartbeat")
            if fatal is not None:break
            threading.Event().wait(.02)
        assert isinstance(fatal, DomainError) and fatal.message == "Heartbeat Run version changed"
        with store.engine.connect() as c:
            after = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        assert after == paused and after["lease_until"] == original["lease_until"]
        assert "sync_renewal" not in state
        (tmp_path / "real-pause-background.json").write_text(json.dumps(dict(
            status="PASS", elapsed_seconds=time.monotonic()-began,
            heartbeat_cadence_seconds=settings.lease_seconds/3,
            pause_http=reply.status_code, old_version=original["version"],
            new_version=after["version"], fence_unchanged=True, lease_unchanged=True,
            background_error=fatal.message, clock_replaced=False,
            provider_calls=0),indent=2)+"\n")
    finally:
        release.set();thread.join(3)
    assert not thread.is_alive() and not errors


@pytest.mark.parametrize("version", [True, False, 0, -1, 1.0, "1"])
def test_non_exact_expected_version_cannot_write_liveness(env, version):
    store = env[0];rid = enqueue(env, "invalid-heartbeat-version")
    original = store.claim("original-worker", 30)
    with pytest.raises(DomainError, match="Invalid expected heartbeat Run version"):
        store.heartbeat("original-worker", rid, original["fence"], _expected_version=version)
    with store.engine.connect() as c:
        assert c.execute(select(heartbeats.c.id).where(heartbeats.c.id == "original-worker")).first() is None
        assert c.execute(select(runs.c.lease_until).where(runs.c.id == rid)).scalar_one() == original["lease_until"]


def test_version_change_between_guard_and_renewal_cas_rolls_back(env):
    store = env[0];rid = enqueue(env, "heartbeat-version-cas")
    original = store.claim("original-worker", 30)
    changed = []
    def before(connection, cursor, statement, parameters, context, many):
        if not changed and statement.startswith("UPDATE runs SET lease_until="):
            changed.append(True)
            cursor.execute("UPDATE runs SET version=version+1 WHERE id=?", (rid,))
    event.listen(store.engine, "before_cursor_execute", before)
    try:
        with pytest.raises(DomainError, match="Heartbeat ownership interval expired or changed"):
            store.heartbeat("original-worker", rid, original["fence"],
                            _expected_version=original["version"])
    finally:event.remove(store.engine, "before_cursor_execute", before)
    assert changed == [True]
    with store.engine.connect() as c:
        saved = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert saved["lease_until"] == original["lease_until"]
        assert saved["version"] == original["version"]
        assert c.execute(select(heartbeats.c.id).where(heartbeats.c.id == "original-worker")).first() is None
