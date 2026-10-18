"""New journal persistence/concurrency only; no old policy matrix or model IO."""

import copy
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import delete, event, select, update
from test_natural_live_admission import frozen, started
from test_natural_spec_apps import setup
from test_production_trial_policy import received
from test_spec_app_operations import snapshot

from sim2act import natural_live_admission as gate
from sim2act import production_evidence as evidence
from sim2act import production_trial_admission as admission
from sim2act import production_trial_journal as journal
from sim2act import production_trial_policy as policy
from sim2act.db import Store, fingerprint, new_id, runs
from sim2act.db import delivery_graph_requests as rows
from sim2act.errors import DomainError


def build(env):
    data = setup(env)
    contract, approval = frozen(data)
    account = "synthetic-durable-journal-account"
    contract = contract.model_copy(update=dict(trial_key="journal-" + data[4],
        quota_subject=admission.canonical_quota_subject(account)))
    approval = approval.model_copy(update=dict(expected_contract_fingerprint=fingerprint(contract.model_dump())))
    gate.approve(data[0], data[3], contract, approval)
    job = started(data, contract)
    scope = evidence.requirements_for(data[3], contract, approval.request_key)
    source = policy.SourceVerificationResult(requirements_fingerprint=fingerprint(scope.model_dump()),
        account_id=account, quota_subject=scope.quota_subject, provider=scope.provider,
        model=scope.model, endpoint=scope.endpoint, evidence_fingerprint="a" * 64,
        decision="ALLOW", legal_free_entitlement=True, enforced_non_chargeable=True, revoked=False,
        observed_at=time.time() - 600, expires_at=contract.expires_at)
    with data[0].tx() as c:
        context = policy.check_run(data[0], c, data[3], contract, approval.request_key,
            "generate", job["id"], job["version"], job["fence"], job["worker_id"])
    wire = b'{"synthetic_durable_journal":true}'
    identity = policy.identity_for(context, source, new_id("attempt"), wire)
    return data, contract, approval, job, source, identity, wire


def command(t, operation, *, store=None, revision=0, item=None, source=None, **extra):
    data, contract, approval, _, original_source, identity, wire = t
    return operation(store or data[0], data[3], contract, approval.request_key,
        item or identity, wire, source or original_source, expected_revision=revision, **extra)


def read(t, *, store=None):
    data, contract, approval, _, source, _, _ = t
    return journal.read(store or data[0], data[3], contract, approval.request_key, source.account_id)


def journal_rows(store):
    with store.tx() as c:
        return [dict(row) for row in c.execute(select(rows).where(rows.c.kind.in_(
            [journal.KIND, journal.KIND + "_seal", journal.QUOTA, journal.QUOTA + "_seal"]))
            .order_by(rows.c.app_id, rows.c.principal_id, rows.c.kind, rows.c.request_key)).mappings()]


def unchanged_other_tables(before, after, *, except_tables=()):
    for table in before:
        if table in except_tables:
            continue
        if table == rows.name:
            def unrelated(values):
                return [v for v in values if not v["kind"].startswith(journal.KIND)]
            assert unrelated(before[table]) == unrelated(after[table])
        else:
            assert before[table] == after[table], table


@pytest.fixture
def trial(env, tmp_path):
    t = build(env)
    baseline = snapshot(t[0][0])
    yield t
    after = snapshot(t[0][0])
    # Races deliberately change runs/events via existing command or fixture SQL.
    unchanged_other_tables(baseline, after, except_tables=("runs", "events"))
    saved = journal_rows(t[0][0])
    (tmp_path / "journal-state.json").write_text(json.dumps(dict(
        scope="OFFLINE_UNINSTALLED_JOURNAL", row_count=len(saved), rows_sha256=fingerprint(saved),
        mirrors=[dict(kind=r["kind"], entity=r["app_id"], key=r["request_key"],
            fingerprint=r["fingerprint"], revision=r["snapshot"]["response"]["revision"])
            for r in saved], unchanged_other_tables=True, except_controlled_tables=["runs", "events"],
        provider_calls=0, live_permits=0), indent=2))
    t[0][2].close()


def test_two_stores_same_attempt_one_reservation_then_exact_history(trial, tmp_path):
    store = trial[0][0]
    baseline = snapshot(store)
    with pytest.raises(DomainError):
        read(trial)
    assert journal_rows(store) == []
    peer = Store(str(store.engine.url), test_only=True)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(command, trial, journal.reserve, store=s) for s in (store, peer)]
            results = [f.result(timeout=15) for f in futures]
        assert sorted(r.duplicate for r in results) == [False, True]
        assert all(r.revision == r.quota_revision == 1 and len(r.ledger.slots) == 1 for r in results)
        assert len(journal_rows(store)) == 4
        marked = command(trial, journal.record_attempt, revision=1)
        settled = command(trial, journal.settle, revision=marked.revision, outcome=received())
        assert settled.revision == settled.quota_revision == 3
        assert settled.ledger.slots[0].accepted and not settled.ledger.halted
        prior = snapshot(store)
        for operation, extra in ((journal.reserve, {}), (journal.record_attempt, {}),
                                 (journal.settle, dict(outcome=received()))):
            result = command(trial, operation, store=peer, revision=0,
                source=trial[4].model_copy(update=dict(revoked=True)), **extra)
            assert result.duplicate and not result.changed and result.revision == 3
            assert result.live_allowed is result.dispatch_authorized is result.real_source_verified is False
        assert snapshot(store) == prior
        unchanged_other_tables(baseline, prior)
        (tmp_path / "concurrent-same-attempt.json").write_text(json.dumps(dict(
            results=[r.model_dump(mode="json") for r in results], final=settled.model_dump(mode="json")), indent=2))
    finally:
        peer.engine.dispose()


def test_one_account_across_two_projects_and_trials_has_one_cursor(env, tmp_path):
    first = build(env)
    pid = env[2].post("/api/projects", json=dict(name="second synthetic journal project")).json()["id"]
    second = build((*env[:5], pid, env[6]))
    assert first[1].trial_key != second[1].trial_key and first[1].project_id != second[1].project_id
    store = env[0]
    baseline = snapshot(store)
    peer = Store(str(store.engine.url), test_only=True)
    def attempt(t, s):
        try:
            return command(t, journal.reserve, store=s)
        except DomainError as exc:
            return exc.code
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt, t, s) for t, s in ((first, store), (second, peer))]
            results = [f.result(timeout=15) for f in futures]
        assert sum(isinstance(r, journal.Receipt) for r in results) == 1
        assert "RATE_LIMITED" in results
        winner = first if isinstance(results[0], journal.Receipt) else second
        loser = second if winner is first else first
        state = read(winner)
        assert state.revision == state.quota_revision == 1 and state.quota.last_reserved_at is not None
        cursor_reads = []
        def observe(c, cursor, statement, parameters, context, executemany):
            if statement.startswith("SELECT ") and journal.QUOTA in parameters:
                cursor_reads.append(True)
        event.listen(store.engine, "before_cursor_execute", observe)
        try:
            assert read(winner) == state and cursor_reads
            cursor_reads.clear()
            for original in (loser[1], loser[1].model_copy(update=dict(trial_key="unapproved-forged-trial"))):
                with pytest.raises(DomainError) as denied:
                    journal.read(store, loser[0][3], original, loser[2].request_key, loser[4].account_id)
                assert denied.value.code == "OUTCOME_UNKNOWN"
        finally:
            event.remove(store.engine, "before_cursor_execute", observe)
        assert cursor_reads == []
        records = journal_rows(store)
        assert len(records) == 4 and sum(r["kind"] == journal.QUOTA for r in records) == 1
        unchanged_other_tables(baseline, snapshot(store))
        (tmp_path / "cross-project-account-contention.json").write_text(json.dumps(dict(
            results=[r if isinstance(r, str) else r.model_dump(mode="json") for r in results],
            winner_state=state.model_dump(mode="json"), empty_or_forged_trial_cursor_reads=cursor_reads), indent=2))
    finally:
        peer.engine.dispose()
        first[0][2].close()
        second[0][2].close()


def test_stale_revision_and_mid_pair_cas_conflict_roll_back_all_rows(trial, monkeypatch, tmp_path):
    reserved = command(trial, journal.reserve)
    before = snapshot(trial[0][0])
    other = trial[5].model_copy(update=dict(attempt_id=new_id("attempt")))
    with pytest.raises(DomainError) as stale:
        command(trial, journal.reserve, item=other, revision=0)
    assert stale.value.code == "VERSION_CONFLICT" and snapshot(trial[0][0]) == before
    original = journal._cas_pair
    observed = []
    def stale_quota(c, owner, entity, kind, key, previous, current):
        if kind == journal.QUOTA:
            previous = copy.deepcopy(previous)
            previous["response"]["revision"] -= 1
            observed.append("stale quota fingerprint after both ledger CAS writes")
        return original(c, owner, entity, kind, key, previous, current)
    monkeypatch.setattr(journal, "_cas_pair", stale_quota)
    with pytest.raises(DomainError) as conflict:
        command(trial, journal.record_attempt, revision=reserved.revision)
    assert conflict.value.code == "VERSION_CONFLICT" and observed
    assert snapshot(trial[0][0]) == before
    current = read(trial)
    assert current.revision == current.quota_revision == 1 and not current.ledger.slots[0].attempted
    (tmp_path / "atomic-cas-rollback.json").write_text(json.dumps(dict(
        injection=observed, all_55_tables_strict_equal=True, state=current.model_dump(mode="json")), indent=2))


@pytest.mark.parametrize("kind", [journal.KIND, journal.QUOTA])
def test_missing_mirror_is_rejected_without_initialization_or_repair(trial, kind):
    command(trial, journal.reserve)
    with trial[0][0].tx() as c:
        c.execute(delete(rows).where(rows.c.kind == kind + "_seal"))
    damaged = snapshot(trial[0][0])
    for action in (lambda: read(trial), lambda: command(trial, journal.reserve)):
        with pytest.raises(DomainError):
            action()
        assert snapshot(trial[0][0]) == damaged
    assert len(journal_rows(trial[0][0])) == 3


CHILD = r'''
import json,sys
import httpx
from sim2act.config import Settings
from sim2act.model import InternModel
from sim2act import natural_live_admission as gate, production_trial_journal as journal, production_trial_policy as policy
from sim2act.db import Store
io_attempts=[]
def blocked(*args,**kwargs):
    io_attempts.append('forbidden IO')
    raise AssertionError('offline child only')
httpx.HTTPTransport.handle_request=blocked
httpx.AsyncHTTPTransport.handle_async_request=blocked
Settings.from_env=blocked
for name in ('request','request_serialized','request_serialized_captured','_request_serialized','_deadline_request'):
    if hasattr(InternModel,name):setattr(InternModel,name,blocked)
d=json.load(sys.stdin)
store=Store(d['url'],test_only=True)
try:
    contract=gate.parse_contract(d['contract'])
    item=policy.ReservationIdentity.model_validate(d['identity'])
    source=policy.SourceVerificationResult.model_validate(d['source'])
    before=journal.read(store,d['user'],contract,d['key'],source.account_id)
    duplicate=journal.reserve(store,d['user'],contract,d['key'],item,d['wire'].encode('ascii'),source,expected_revision=0)
    after=journal.read(store,d['user'],contract,d['key'],source.account_id)
    assert before==after and duplicate.duplicate and not duplicate.changed
    assert not duplicate.live_allowed and not duplicate.dispatch_authorized
    print(json.dumps(dict(before=before.model_dump(mode='json'),duplicate=duplicate.model_dump(mode='json'),after=after.model_dump(mode='json'),io_attempts=io_attempts)))
finally:store.engine.dispose()
'''


def child_read(t, tmp_path, name):
    data, contract, approval, _, source, identity, wire = t
    payload = dict(url=str(data[0].engine.url), user=data[3], contract=contract.model_dump(mode="json"),
        key=approval.request_key, identity=identity.model_dump(mode="json"),
        source=source.model_copy(update=dict(revoked=True)).model_dump(mode="json"), wire=wire.decode("ascii"))
    environment = {k: v for k, v in os.environ.items() if not k.startswith(("SIM2ACT_", "INTERN_"))}
    result = subprocess.run([sys.executable, "-c", CHILD], input=json.dumps(payload),
        text=True, capture_output=True, env=environment, timeout=20)
    (tmp_path / (name + ".stdout")).write_text(result.stdout)
    (tmp_path / (name + ".stderr")).write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    proof = json.loads(result.stdout)
    assert proof["io_attempts"] == []
    return journal.Receipt.model_validate_json(json.dumps(proof["after"]))


def test_new_process_pending_unknown_and_duplicate_settlement_never_resend(trial, tmp_path):
    reserved = command(trial, journal.reserve)
    prior = snapshot(trial[0][0])
    pending = child_read(trial, tmp_path, "pending-child")
    assert pending == read(trial) and pending.revision == 1
    assert not pending.ledger.slots[0].attempted and snapshot(trial[0][0]) == prior
    other = trial[5].model_copy(update=dict(attempt_id=new_id("attempt")))
    with pytest.raises(DomainError) as blocked:
        command(trial, journal.reserve, item=other, revision=1)
    assert blocked.value.code == "OUTCOME_UNKNOWN"
    marked = command(trial, journal.record_attempt, revision=reserved.revision)
    unknown = policy.Outcome(outcome="UNKNOWN", response_sha256="b" * 64,
        response_ascii_bytes=40, prompt_tokens=5)
    settled = command(trial, journal.settle, revision=marked.revision, outcome=unknown)
    assert settled.ledger.halted and settled.quota.last_reserved_at == reserved.quota.last_reserved_at
    prior = snapshot(trial[0][0])
    restarted = child_read(trial, tmp_path, "unknown-child")
    assert restarted == read(trial) and restarted.revision == 3
    slot = restarted.ledger.slots[0]
    assert slot.attempted and not slot.accepted and slot.settlement.prompt_tokens == 5
    assert slot.settlement.total_tokens is slot.settlement.completion_tokens is None
    duplicate = command(trial, journal.settle, revision=0, outcome=unknown)
    assert duplicate.duplicate and duplicate.revision == 3
    with pytest.raises(DomainError):
        command(trial, journal.settle, revision=3, outcome=received())
    with pytest.raises(DomainError) as blocked:
        command(trial, journal.reserve, item=other, revision=3)
    assert blocked.value.code == "OUTCOME_UNKNOWN" and snapshot(trial[0][0]) == prior


@pytest.mark.parametrize("change", ["cancel", "lease", "fence"])
@pytest.mark.parametrize("first", ["marker", "control"])
def test_two_connection_marker_control_linearization(trial, change, first, monkeypatch, tmp_path):
    reserved = command(trial, journal.reserve)
    store, job = trial[0][0], trial[3]
    peer = Store(str(store.engine.url), test_only=True)
    held, release, contender = Event(), Event(), Event()
    trace = []
    def pause(label):
        trace.append(label + "-written-lock-held")
        held.set()
        assert release.wait(8), "bounded race release"
        trace.append(label + "-released")
    original = journal._persist
    def persist(*args, **kwargs):
        result = original(*args, **kwargs)
        if first == "marker" and not held.is_set():
            pause("marker")
        return result
    monkeypatch.setattr(journal, "_persist", persist)
    def begin(c, cursor, statement, parameters, context, executemany):
        if statement == "BEGIN IMMEDIATE":
            trace.append("contender-BEGIN-attempt")
            contender.set()
    loser = peer if first == "marker" else store
    event.listen(loser.engine, "before_cursor_execute", begin)
    def after_control(c, cursor, statement, parameters, context, executemany):
        if first == "control" and statement.startswith("UPDATE runs SET"):
            pause("control")
    event.listen(peer.engine, "after_cursor_execute", after_control)
    def control():
        if change == "cancel":
            result = peer.command(trial[0][3], job["id"], "cancel", job["version"])
        else:
            with peer.tx() as c:
                c.execute(update(runs).where(runs.c.id == job["id"]).values(
                    **({"lease_until": 1.0} if change == "lease" else {"fence": job["fence"] + 1})))
            result = "committed"
        trace.append("control-returned")
        return result
    def marker():
        try:
            result = command(trial, journal.record_attempt, revision=reserved.revision)
        except DomainError as exc:
            result = exc.code
        trace.append("marker-returned")
        return result
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            winner = pool.submit(marker if first == "marker" else control)
            assert held.wait(8), "winner acquired transaction and wrote"
            follower = pool.submit(control if first == "marker" else marker)
            try:
                assert contender.wait(8), "contender attempted independent transaction"
                assert not follower.done()
                trace.append("both-active-before-release")
            finally:
                release.set()
            winner_result = winner.result(timeout=15)
            follower_result = follower.result(timeout=15)
        current = read(trial)
        if first == "marker":
            assert isinstance(winner_result, journal.Receipt) and current.revision == 2
            assert current.ledger.slots[0].attempted
        else:
            assert isinstance(follower_result, str) and current.revision == 1
            assert not current.ledger.slots[0].attempted
        settled = command(trial, journal.settle, revision=current.revision, outcome=received())
        slot = settled.ledger.slots[0]
        assert not slot.accepted and settled.ledger.halted and slot.settlement.total_tokens == 8
        assert slot.attempted == (first == "marker") and len(settled.ledger.slots) == 1
        assert settled.quota.last_reserved_at == reserved.quota.last_reserved_at
        before_duplicate = snapshot(store)
        duplicate = command(trial, journal.reserve, revision=0)
        assert duplicate.duplicate and not duplicate.changed and snapshot(store) == before_duplicate
        (tmp_path / "linearization.json").write_text(json.dumps(dict(
            change=change, first=first, trace=trace, independent_connections=2,
            marker_result="committed" if first == "marker" else follower_result,
            settled=settled.model_dump(mode="json")), indent=2))
    finally:
        release.set()
        event.remove(loser.engine, "before_cursor_execute", begin)
        event.remove(peer.engine, "after_cursor_execute", after_control)
        peer.engine.dispose()
