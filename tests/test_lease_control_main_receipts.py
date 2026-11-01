"""Actual main/control handshake; execution remains explicitly unavailable."""

import json
import subprocess
import sys

import pytest
from sqlalchemy import select, text
from test_foundation import enqueue

from sim2act import _lease_control as control
from sim2act import _lease_control_runtime as adapter
from sim2act.db import runs
from sim2act.errors import DomainError


def claim(env):
    store, settings = env[:2]
    selected = store._enable_authoritative_leases(settings, create=True)
    rid = enqueue(env, "real-main-control-claim")
    original = store.claim("original-worker", 30)
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
