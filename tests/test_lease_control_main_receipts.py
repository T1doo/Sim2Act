"""Actual main/control handshake; execution remains explicitly unavailable."""

import json
import subprocess
import sys

import pytest
from sqlalchemy import event, select, text
from test_foundation import enqueue

from sim2act import _lease_control as control
from sim2act import _lease_control_runtime as adapter
from sim2act.db import runs
from sim2act.errors import DomainError


def claim(env):
    store, settings = env[:2]
    selected = store._enable_authoritative_leases(settings, create=True)
    rid = enqueue(env, "real-main-control-claim")
    original = store.claim("original-worker", settings.lease_seconds)
    assert original["id"] == rid
    bound = selected.bind_claim(original)
    return selected, original, bound


def test_handoff_uses_actual_committed_main_marker_and_keeps_history_anchor(env):
    selected, original, bound = claim(env)
    assert bound["lease_until"] == original["lease_until"]
    assert bound["cancel_intent"] is False
    session = selected.session(bound)
    assert session.renew() > original["lease_until"]
    with selected.store.engine.connect() as c:
        saved = dict(c.execute(select(runs).where(runs.c.id == original["id"])).mappings().one())
    assert saved == bound
    # No legacy guard may treat that historical numeric anchor as authority.
    with pytest.raises(DomainError, match="Authoritative lease execution is not enabled"):
        with selected.store.tx() as c:
            selected.store.guard(c, bound["id"], bound["fence"])


def test_forged_main_claim_header_cannot_activate_a_control_owner(env):
    store, settings = env[:2]
    selected = store._enable_authoritative_leases(settings, create=True)
    rid = enqueue(env, "forged-main-control-claim")
    original = store.claim("original-worker", 30)
    forged = dict(original, worker_id="foreign-worker")
    with pytest.raises(DomainError, match="Claim changed before authority handoff"):
        selected.bind_claim(forged)
    with selected.authority.connection() as c:
        assert c.execute("SELECT count(*) FROM leases").fetchone() == (0,)
    assert not adapter.marked(selected.committed_run(rid))


def test_activation_rechecks_competing_version_after_marker_commit(env):
    import sqlite3
    store, settings = env[:2]
    selected = store._enable_authoritative_leases(settings, create=True)
    rid = enqueue(env, "competing-main-control-claim")
    original = store.claim("original-worker", 30)
    competed = []
    def after_main_close(raw, record):
        if competed:
            return
        competed.append(True)
        with sqlite3.connect(str(selected.path)) as other:
            other.execute("UPDATE runs SET version=version+1 WHERE id=?", (rid,))
    event.listen(store.engine.pool, "checkin", after_main_close)
    try:
        with pytest.raises(DomainError, match="Main claim receipt changed before activation"):
            selected.bind_claim(original)
    finally:
        event.remove(store.engine.pool, "checkin", after_main_close)
    assert competed == [True]
    with selected.authority.connection() as c:
        assert c.execute("SELECT state FROM leases WHERE run_id=?", (rid,)).fetchone() == ("PENDING",)
    assert selected.authority.sessions == {}


def test_uncommitted_main_receipt_cannot_acknowledge_control(env):
    selected, original, bound = claim(env)
    receipt = selected.session(bound).prepare("e" * 64)
    with pytest.raises(DomainError, match="No durable main receipt"):
        with selected.store.tx() as c:
            c.execute(text("INSERT INTO " + adapter.RECEIPTS + " VALUES(:key,:control,:run,:nonce,:header,:receipt)"),
                dict(key=receipt["commit_id"], control=receipt["control_id"], run=bound["id"],
                     nonce=receipt["nonce"], header=control._wire(tuple(receipt["header"])),
                     receipt=json.dumps(receipt)))
            selected.recover_committed(c, receipt["commit_id"])
    with selected.authority.connection() as c:
        assert c.execute("SELECT state FROM commits WHERE commit_id=?", (receipt["commit_id"],)).fetchone() == ("PREPARED",)
        assert c.execute("SELECT acked_commit FROM leases WHERE run_id=?", (bound["id"],)).fetchone() == (None,)
    with selected.store.engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM " + adapter.RECEIPTS)).scalar_one() == 0


def test_runtime_identity_cannot_be_reissued_from_mutable_python_state(env, monkeypatch):
    selected, _, bound = claim(env)
    original = selected.uri
    with monkeypatch.context() as patch:
        patch.setattr(selected, "uri", original + "-foreign")
        patch.setattr(adapter, "_RUNTIME_STATES", {id(selected): (selected, tuple(vars(selected).items()))}, raising=False)
        with pytest.raises(ValueError, match="Lease runtime issuance or fields changed"):
            selected.committed_run(bound["id"])
    assert selected.committed_run(bound["id"])["id"] == bound["id"]
    from sim2act import _cold_source_owned_impl as native
    with pytest.raises(ValueError, match="Lease runtime issuance or fields changed"):
        native.install_lease_runtime(selected)


def test_preissuance_method_shadow_is_rejected_without_foreign_call(env):
    store, settings = env[:2]
    constructor = adapter.Runtime.__init__.__code__
    seen, foreign_calls = [], []
    def foreign(*args, **kwargs):
        foreign_calls.append(True)
    def injected(code, offset, result):
        if code is constructor:
            target = sys._getframe(1).f_locals["self"]
            object.__setattr__(target, "_main", foreign)
            seen.append(target)
    slot = next(i for i in (3, 5, 4) if sys.monitoring.get_tool(i) is None)
    sys.monitoring.use_tool_id(slot, "lease pre-issuer shadow")
    try:
        sys.monitoring.register_callback(slot, sys.monitoring.events.PY_RETURN, injected)
        sys.monitoring.set_local_events(slot, constructor, sys.monitoring.events.PY_RETURN)
        with pytest.raises(ValueError, match="Lease runtime issuance or fields changed"):
            store._enable_authoritative_leases(settings, create=True)
        assert len(seen) == 1 and foreign_calls == []
        assert adapter.runtime(store) is None
    finally:
        sys.monitoring.set_local_events(slot, constructor, 0)
        sys.monitoring.register_callback(slot, sys.monitoring.events.PY_RETURN, None)
        sys.monitoring.free_tool_id(slot)


def test_runtime_rejects_store_type_disguise_before_foreign_dispatch(env):
    selected, _, bound = claim(env)
    original_type = type(selected.store)
    foreign_calls = []
    class Foreign:
        def tx(self, *args, **kwargs):
            foreign_calls.append(True)
            raise AssertionError("Foreign Store dispatched")
    selected.store.__class__ = Foreign
    try:
        with pytest.raises(ValueError, match="Lease runtime issuance or fields changed"):
            selected.bind_claim(bound)
        assert foreign_calls == []
    finally:
        selected.store.__class__ = original_type
    assert selected.committed_run(bound["id"])["id"] == bound["id"]


@pytest.mark.parametrize("role", ["tx", "guard", "owns_connection", "frozen_contract", "event"])
def test_runtime_rejects_store_method_shadow_before_foreign_dispatch(env, role, monkeypatch):
    selected, _, bound = claim(env)
    foreign_calls = []
    def foreign(*args, **kwargs):
        foreign_calls.append(True)
        raise AssertionError("Foreign Store dispatched")
    with monkeypatch.context() as patch:
        patch.setattr(selected.store, role, foreign)
        with pytest.raises(ValueError, match="Lease runtime issuance or fields changed"):
            selected.bind_claim(bound)
        assert foreign_calls == []
    assert selected.committed_run(bound["id"])["id"] == bound["id"]


def test_post_state_method_shadow_rechecks_before_foreign_dispatch(env):
    selected, _, bound = claim(env)
    seen, foreign_calls = [], []
    code = adapter._state.__code__
    def foreign(*args, **kwargs):
        foreign_calls.append(True)
        raise AssertionError("Foreign runtime dispatched")
    def injected(active, offset, result):
        if active is code and not seen:
            object.__setattr__(selected, "_main", foreign)
            seen.append(True)
    slot = next(i for i in (3, 5, 4) if sys.monitoring.get_tool(i) is None)
    sys.monitoring.use_tool_id(slot, "lease post-state shadow")
    try:
        sys.monitoring.register_callback(slot, sys.monitoring.events.PY_RETURN, injected)
        sys.monitoring.set_local_events(slot, code, sys.monitoring.events.PY_RETURN)
        with pytest.raises(ValueError, match="Lease runtime issuance or fields changed"):
            selected.committed_run(bound["id"])
        assert seen == [True] and foreign_calls == []
    finally:
        sys.monitoring.set_local_events(slot, code, 0)
        sys.monitoring.register_callback(slot, sys.monitoring.events.PY_RETURN, None)
        sys.monitoring.free_tool_id(slot)
        vars(selected).pop("_main", None)


def test_activation_rejects_same_connection_select_callback_write(env):
    store, settings = env[:2]
    selected = store._enable_authoritative_leases(settings, create=True)
    rid = enqueue(env, "same-connection-main-control-claim")
    original = store.claim("original-worker", 30)
    writes = []
    def after_read(c, cursor, statement, parameters, context, many):
        if statement.startswith("SELECT runs.") and "WHERE runs.id =" in statement and not writes:
            # The first read belongs to legacy guard; wait until the marker
            # handoff has committed and the second writer begins activation.
            raw = c.connection.driver_connection
            marker = raw.execute("SELECT context FROM runs WHERE id=?", (rid,)).fetchone()[0]
            if control.CONTEXT in json.loads(marker):
                writes.append(True)
                raw.execute("UPDATE runs SET version=version+1 WHERE id=?", (rid,))
    event.listen(store.engine, "after_cursor_execute", after_read)
    try:
        with pytest.raises(DomainError, match="Main activation barrier wrote protected data"):
            selected.bind_claim(original)
    finally:
        event.remove(store.engine, "after_cursor_execute", after_read)
    assert writes == [True]
    assert selected.committed_run(rid)["version"] == original["version"]
    assert selected.authority.sessions == {}
    with selected.authority.connection() as c:
        assert c.execute("SELECT state FROM leases WHERE run_id=?", (rid,)).fetchone() == ("PENDING",)


@pytest.mark.parametrize("main_write", [False, True])
def test_store_heartbeat_commits_past_old_lease_with_main_snapshot_or_writer(env, main_write, tmp_path):
    import sqlite3
    import time
    from dataclasses import replace
    local_env = (env[0], replace(env[1], lease_seconds=1), *env[2:])
    selected, original, bound = claim(local_env)
    raw = sqlite3.connect(str(selected.path), isolation_level=None, timeout=.2)
    timings = []
    began = time.monotonic()
    try:
        raw.execute("BEGIN IMMEDIATE" if main_write else "BEGIN DEFERRED")
        assert raw.execute("SELECT lease_until FROM runs WHERE id=?", (bound["id"],)).fetchone() == (original["lease_until"],)
        if main_write:
            raw.execute("UPDATE runs SET lease_until=lease_until WHERE id=?", (bound["id"],))
        changes = raw.total_changes
        for index in range(8):
            started = time.monotonic()
            renewed = selected.store.heartbeat(original["worker_id"], bound["id"], bound["fence"], 1,
                _expected_version=bound["version"], _running_only=True)
            timings.append(time.monotonic() - started)
            assert renewed > original["lease_until"] and raw.total_changes == changes
            time.sleep(.16)
        assert time.time() > original["lease_until"]
        # A real G0 read snapshot can still upgrade after many independently
        # committed renewals. There was no hidden main heartbeat write.
        raw.execute("UPDATE runs SET lease_until=lease_until WHERE id=?", (bound["id"],))
        raw.commit()
    finally:
        raw.close()
    assert selected.committed_run(bound["id"]) == bound
    assert selected.authority.check(bound)["sequence"] == 8
    result = dict(status="PASS",real_wall_seconds=time.monotonic()-began,
        main_writer=main_write,control_commits=8,renewal_seconds=timings,
        main_run_unchanged=True,lease_seconds=1,large_30_second_acceptance=False)
    (tmp_path / "committed-heartbeat-with-main-lock.json").write_text(json.dumps(result))


@pytest.mark.parametrize("failure", ["version", "owner", "cancel", "deadline", "missing-version"])
def test_store_control_heartbeat_rejects_changed_identity_or_intent_without_renewal(env, failure):
    import time
    selected, original, bound = claim(env)
    version = bound["version"]
    if failure in {"version", "owner"}:
        with selected.store.tx() as c:
            if failure == "version":
                c.execute(text("UPDATE runs SET version=version+1 WHERE id=:id"), dict(id=bound["id"]))
            else:
                c.execute(text("UPDATE runs SET worker_id='other-worker' WHERE id=:id"), dict(id=bound["id"]))
    elif failure == "cancel":
        selected.authority.command(bound, "cancel")
    elif failure == "missing-version":
        version = None
    with pytest.raises(DomainError):
        selected.store.heartbeat(original["worker_id"], bound["id"], bound["fence"], 30,
            _expected_version=version,
            _deadline=time.time()-1 if failure == "deadline" else None)
    with selected.authority.connection() as c:
        assert c.execute("SELECT sequence FROM leases WHERE run_id=?", (bound["id"],)).fetchone() == (0,)


def test_heartbeat_final_read_crossing_earlier_node_deadline_does_not_publish_success(env):
    import threading
    import time
    selected, original, bound = claim(env)
    deadline = time.time() + .5
    reads = []
    read_code = adapter.Runtime.committed_run.__code__
    heartbeat_code = adapter.Runtime.heartbeat.__code__
    def delayed_read(code, offset, result):
        if code is read_code and sys._getframe(1).f_back.f_code is heartbeat_code:
            reads.append(True)
            threading.Event().wait(max(0, deadline-time.time()) + .02)
    slot = next(i for i in (3, 5, 4) if sys.monitoring.get_tool(i) is None)
    sys.monitoring.use_tool_id(slot, "lease final read deadline")
    try:
        sys.monitoring.register_callback(slot, sys.monitoring.events.PY_RETURN, delayed_read)
        sys.monitoring.set_local_events(slot, read_code, sys.monitoring.events.PY_RETURN)
        with pytest.raises(DomainError, match="deadline ended before final publication"):
            selected.store.heartbeat(original["worker_id"], bound["id"], bound["fence"], 30,
                _expected_version=bound["version"], _deadline=deadline)
    finally:
        sys.monitoring.set_local_events(slot, read_code, 0)
        sys.monitoring.register_callback(slot, sys.monitoring.events.PY_RETURN, None)
        sys.monitoring.free_tool_id(slot)
    assert reads == [True]
    # A committed renewal remains a known fact; only success publication was
    # refused. Do not lie about rollback or erase the actual control history.
    with selected.authority.connection() as c:
        assert c.execute("SELECT sequence FROM leases WHERE run_id=?", (bound["id"],)).fetchone() == (1,)


def test_heartbeat_rechecks_committed_revocation_after_control_renewal(env):
    import sqlite3
    selected, original, bound = claim(env)
    read_code = adapter.Runtime.committed_run.__code__
    heartbeat_code = adapter.Runtime.heartbeat.__code__
    revoked = []
    def revoke_after_renewal(code, offset, result):
        if code is read_code and sys._getframe(1).f_back.f_code is heartbeat_code:
            with sqlite3.connect(str(selected.path)) as other:
                changed = other.execute("UPDATE grants SET revoked=1,revision=revision+1 "
                    "WHERE principal_id=? AND resource_id=? AND tool_ref='resource.read'",
                    (bound["runtime_id"], bound["resource_refs"][0]))
                revoked.append(changed.rowcount)
    slot = next(i for i in (3, 5, 4) if sys.monitoring.get_tool(i) is None)
    sys.monitoring.use_tool_id(slot, "lease committed revocation")
    try:
        sys.monitoring.register_callback(slot, sys.monitoring.events.PY_RETURN, revoke_after_renewal)
        sys.monitoring.set_local_events(slot, read_code, sys.monitoring.events.PY_RETURN)
        with pytest.raises(DomainError) as denied:
            selected.store.heartbeat(original["worker_id"], bound["id"], bound["fence"], 30,
                _expected_version=bound["version"])
        assert denied.value.code == "GRANT_REVOKED"
    finally:
        sys.monitoring.set_local_events(slot, read_code, 0)
        sys.monitoring.register_callback(slot, sys.monitoring.events.PY_RETURN, None)
        sys.monitoring.free_tool_id(slot)
    assert revoked == [1]
    with selected.authority.connection() as c:
        assert c.execute("SELECT sequence FROM leases WHERE run_id=?", (bound["id"],)).fetchone() == (1,)


def test_store_control_heartbeat_refuses_missing_storage_without_creating_replacement(env):
    selected, original, bound = claim(env)
    path = selected.authority.path
    backup = path.with_name(path.name + ".preserved")
    path.rename(backup)
    try:
        with pytest.raises(DomainError) as unavailable:
            selected.store.heartbeat(original["worker_id"], bound["id"], bound["fence"], 30,
                _expected_version=bound["version"])
        assert unavailable.value.code == "RESOURCE_UNAVAILABLE"
        assert not path.exists()
        assert selected.committed_run(bound["id"]) == bound
    finally:
        backup.rename(path)
    assert selected.authority.check(bound)["sequence"] == 0


def test_store_control_heartbeat_does_not_resurrect_expired_owner(env):
    import threading
    from dataclasses import replace
    local_env = (env[0], replace(env[1], lease_seconds=1), *env[2:])
    selected, original, bound = claim(local_env)
    threading.Event().wait(1.05)
    with pytest.raises(DomainError, match="expired"):
        selected.store.heartbeat(original["worker_id"], bound["id"], bound["fence"], 1,
            _expected_version=bound["version"])
    assert selected.authority.check(bound, live=False)["sequence"] == 0


def test_foreign_store_runtime_rejected_before_reading_other_workspace(env):
    from sim2act.db import Store
    selected, original, bound = claim(env)
    other = Store(str(selected.store.engine.url), test_only=True)
    other._authoritative_lease_runtime = selected
    try:
        with pytest.raises(DomainError, match="Foreign authoritative heartbeat runtime"):
            other.heartbeat(original["worker_id"], bound["id"], bound["fence"], 30,
                _expected_version=bound["version"])
    finally:
        other.engine.dispose()
    assert selected.authority.check(bound)["sequence"] == 0


def test_runtime_expected_state_is_not_a_gc_visible_mutable_registry(env):
    import gc
    import weakref
    selected, _, bound = claim(env)
    gc.collect()
    reachable = []
    for candidate in gc.get_objects():
        if type(candidate) is dict:
            value = candidate.get(id(selected))
            if (type(value) is tuple and len(value) == 4 and type(value[0]) is weakref.ReferenceType
                    and value[0]() is selected):
                reachable.append(candidate)
    assert reachable == []
    # Manually invoking a discoverable weak callback must not revoke a living
    # issued record (or free a record underneath a native invocation).
    for reference in weakref.getweakrefs(selected):
        callback = reference.__callback__
        if callback is not None:
            callback(reference)
    assert selected.committed_run(bound["id"]) == bound


def test_new_process_ack_recovers_real_main_receipt_without_issuing_old_owner(env, tmp_path):
    selected, original, bound = claim(env)
    session = selected.session(bound)
    receipt = session.prepare("f" * 64)
    # A real durable main receipt models the exact main-committed/ack-not-yet
    # transition. No test claims a normal business flow or an execution PASS.
    with selected.store.tx() as c:
        c.execute(text("INSERT INTO " + adapter.RECEIPTS + " VALUES(:key,:control,:run,:nonce,:header,:receipt)"),
                  dict(key=receipt["commit_id"], control=receipt["control_id"], run=bound["id"],
                       nonce=receipt["nonce"], header=control._wire(tuple(receipt["header"])),
                       receipt=json.dumps(receipt)))
    script = """
import json,sys
from pathlib import Path
from sim2act.db import Store
from sim2act.config import Settings
from sim2act import _lease_control_runtime as adapter
store=Store(sys.argv[1],test_only=True)
try:
 settings=Settings(sys.argv[1],Path(sys.argv[2]),mode='mock')
 selected=store._enable_authoritative_leases(settings,create=False)
 assert selected.authority.sessions=={}
 with store.tx() as c:
  first=selected.recover_committed(c,sys.argv[3])
 with store.tx() as c:
  again=selected.recover_committed(c,sys.argv[3])
 assert first==again and selected.authority.sessions=={}
 print(json.dumps(dict(status='PASS',fresh_process=True,old_mono_reissued=False,
   acknowledgement_idempotent=True,effect_or_model_replays=0)))
finally:store.engine.dispose()
"""
    result = subprocess.run([sys.executable, "-c", script, str(selected.store.engine.url),
                             str(tmp_path), receipt["commit_id"]], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    assert json.loads(result.stdout)["status"] == "PASS"
    assert selected.authority.check(bound, live=False)["acked"] == receipt["commit_id"]
    with selected.store.engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM " + adapter.RECEIPTS)).scalar_one() == 1
        assert c.execute(select(runs.c.result).where(runs.c.id == bound["id"])).scalar_one() is None
    (tmp_path / "fresh-main-receipt-recovery.json").write_text(result.stdout)
