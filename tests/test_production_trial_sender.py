"""Uninstalled sender windows; existing InternModel to exact synthetic transport."""

import base64
import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Event

import httpx
import pytest
from sqlalchemy import event, select, update
from test_natural_live_admission import frozen
from test_natural_spec_apps import setup
from test_spec_app_operations import snapshot

from sim2act import natural_live_admission as gate
from sim2act import production_evidence as evidence
from sim2act import production_trial_admission as admission
from sim2act import production_trial_journal as journal
from sim2act import production_trial_policy as policy
from sim2act import production_trial_sender as sender
from sim2act.config import Settings
from sim2act.db import Store, fingerprint, new_id
from sim2act.db import delivery_graph_requests as rows
from sim2act.errors import DomainError
from sim2act.goal_applications import body
from sim2act.model import InternModel
from sim2act.worker import Worker


def response(**changes):
    raw = dict(
        model="Intern-S2",
        choices=[
            dict(
                finish_reason="stop",
                message=dict(role="assistant", content="Synthetic 花, no business acceptance"),
            )
        ],
        usage=dict(prompt_tokens=5, completion_tokens=3, total_tokens=8),
    )
    raw.update(changes)
    return json.dumps(raw, ensure_ascii=False, indent=1).encode()


def prepare(env, *, claim=True):
    data = setup(env)
    contract, approval = frozen(data)
    account = "synthetic-uninstalled-sender"
    contract = contract.model_copy(
        update=dict(quota_subject=admission.canonical_quota_subject(account))
    )
    approval = approval.model_copy(
        update=dict(expected_contract_fingerprint=fingerprint(contract.model_dump()))
    )
    gate.approve(data[0], data[3], contract, approval)
    scope = evidence.requirements_for(data[3], contract, approval.request_key)
    source = policy.SourceVerificationResult(
        requirements_fingerprint=fingerprint(scope.model_dump()),
        account_id=account,
        quota_subject=scope.quota_subject,
        provider=scope.provider,
        model=scope.model,
        endpoint=scope.endpoint,
        evidence_fingerprint="a" * 64,
        decision="ALLOW",
        legal_free_entitlement=True,
        enforced_non_chargeable=True,
        revoked=False,
        observed_at=time.time() - 600,
        expires_at=contract.expires_at,
    )
    wire = body([dict(role="user", content="synthetic sender boundary only")], [], 1024)
    state = dict(sent=[], reply=response(), hook=None)

    def handler(request):
        assert (
            request.content == wire
            and request.method == "POST"
            and str(request.url) == contract.endpoint
        )
        state["sent"].append(
            dict(
                wire_sha256=hashlib.sha256(request.content).hexdigest(), bytes=len(request.content)
            )
        )
        if state["hook"] is not None:
            return state["hook"](request)
        return httpx.Response(200, content=state["reply"])

    settings = replace(data[1], quota_subject=contract.quota_subject)
    worker = Worker(data[0], settings, goal_planner_transport=httpx.MockTransport(handler))
    card = data[6]
    made = data[2].post(
        f"/api/projects/{data[4]}/goal-cards/{card['id']}/application-runs",
        json=dict(
            expected_version=card["version"],
            expected_fingerprint=card["fingerprint"],
            request_key=contract.stage_keys.generate,
            family="natural_spec",
        ),
    )
    assert made.status_code == 202, made.text
    job, item = None, None
    if claim:
        job = data[0].claim(worker.id, 30)
        assert job["id"] == made.json()["run_id"]
        with data[0].tx() as c:
            context = policy.check_run(
                data[0],
                c,
                data[3],
                contract,
                approval.request_key,
                "generate",
                job["id"],
                job["version"],
                job["fence"],
                worker.id,
            )
        item = policy.identity_for(context, source, new_id("attempt"), wire)
    return dict(
        data=data,
        contract=contract,
        approval=approval,
        source=source,
        wire=wire,
        worker=worker,
        state=state,
        job=job,
        identity=item,
        run_id=made.json()["run_id"],
    )


def dispatch(t, *, worker=None, revision=0, **changes):
    values = dict(
        contract=t["contract"],
        key=t["approval"].request_key,
        identity=t["identity"],
        wire=t["wire"],
        source=t["source"],
        expected_revision=revision,
    )
    values.update(changes)
    return sender.dispatch_offline(worker or t["worker"], **values)


def read(t):
    return journal.read(
        t["data"][0], t["data"][3], t["contract"], t["approval"].request_key, t["source"].account_id
    )


def records(store):
    with store.tx() as c:
        return [
            dict(r)
            for r in c.execute(
                select(rows)
                .where(
                    rows.c.kind.in_(
                        [
                            journal.KIND,
                            journal.KIND + "_seal",
                            journal.QUOTA,
                            journal.QUOTA + "_seal",
                            sender.CAPTURE,
                            sender.CAPTURE + "_seal",
                        ]
                    )
                )
                .order_by(rows.c.app_id, rows.c.kind)
            ).mappings()
        ]


def protected(before, after):
    for table in before:
        if table in ("runs", "events"):
            continue
        if table == rows.name:

            def unrelated(values):
                return [
                    v for v in values if not v["kind"].startswith((journal.KIND, sender.CAPTURE))
                ]

            assert unrelated(before[table]) == unrelated(after[table])
        else:
            assert before[table] == after[table], table


@pytest.fixture
def trial(env, tmp_path):
    t = prepare(env)
    before = snapshot(env[0])
    yield t
    protected(before, snapshot(env[0]))
    saved = records(env[0])
    (tmp_path / "sender-state.json").write_text(
        json.dumps(
            dict(
                scope="UNINSTALLED_SYNTHETIC_ONLY",
                mirrors=[dict(kind=r["kind"], fingerprint=r["fingerprint"]) for r in saved],
                rows_sha256=fingerprint(saved),
                mock_handler_calls=len(t["state"]["sent"]),
                real_provider_calls=0,
                current_worker_live_enabled=t["worker"].s.live_enabled,
                protected_tables_strict_equal=True,
                except_controlled_tables=["runs", "events"],
            ),
            indent=2,
        )
    )
    t["data"][2].close()


def alter_pair(store, kind, change):
    """Controlled fixture corruption with recomputed seals; never product repair."""
    with store.tx() as c:
        found = (
            c.execute(select(rows).where(rows.c.kind.in_([kind, kind + "_seal"]))).mappings().all()
        )
        assert len(found) == 2
        for row in found:
            saved = copy.deepcopy(row["snapshot"])
            change(saved["response"])
            c.execute(
                update(rows)
                .where(
                    rows.c.app_id == row["app_id"],
                    rows.c.principal_id == row["principal_id"],
                    rows.c.kind == row["kind"],
                    rows.c.request_key == row["request_key"],
                )
                .values(
                    snapshot=saved,
                    fingerprint=fingerprint(saved),
                    request_fingerprint=fingerprint(saved["request"]),
                )
            )


def test_exact_adapter_capture_atomic_accounting_and_immutable_history(trial, tmp_path):
    original_store = trial["worker"].store
    foreign = Store(str(original_store.engine.url), test_only=True)
    foreign.test_only = False
    foreign_sql = []

    def observe_foreign(*args):
        foreign_sql.append(True)

    event.listen(foreign.engine, "before_cursor_execute", observe_foreign)

    def moved_worker(request):
        trial["worker"].store = foreign
        return httpx.Response(200, content=trial["state"]["reply"])

    trial["state"]["hook"] = moved_worker
    try:
        result = dispatch(trial)
        assert foreign_sql == []
    finally:
        trial["worker"].store = original_store
        event.remove(foreign.engine, "before_cursor_execute", observe_foreign)
        foreign.engine.dispose()
    assert len(trial["state"]["sent"]) == 1 and result.journal.revision == 3
    assert result.journal.ledger.slots[0].accepted and result.response_verdict == "VALID_PROTOCOL"
    assert result.may_have_sent and result.adapter_entered and not result.business_accepted
    assert result.live_allowed is result.dispatch_authorized is result.real_source_verified is False
    saved = records(trial["data"][0])
    assert len(saved) == 6
    capture = next(r["snapshot"]["response"] for r in saved if r["kind"] == sender.CAPTURE)
    assert base64.b64decode(capture["body_b64"]) == trial["state"]["reply"]
    assert capture["raw_sha256"] == hashlib.sha256(trial["state"]["reply"]).hexdigest()
    assert capture["raw_sha256"] != capture["canonical_sha256"]
    assert capture["outcome"]["response_ascii_bytes"] == capture["canonical_ascii_bytes"]
    assert (
        "body_b64" not in result.model_dump_json()
        and "Synthetic 花" not in result.model_dump_json()
    )
    before = snapshot(trial["data"][0])
    duplicate = dispatch(trial)
    assert duplicate.journal.duplicate and not duplicate.adapter_entered
    assert len(trial["state"]["sent"]) == 1 and snapshot(trial["data"][0]) == before
    with pytest.raises(DomainError):
        sender._receive(
            trial["data"][0],
            trial["data"][3],
            trial["contract"],
            trial["approval"].request_key,
            trial["identity"],
            trial["wire"],
            trial["source"],
            3,
            response(model="different-model"),
            True,
            True,
        )
    assert snapshot(trial["data"][0]) == before
    (tmp_path / "known-body-accounting.json").write_text(result.model_dump_json(indent=2))
    # Two separately valid mirrors must still agree across capture and journal.
    alter_pair(
        trial["data"][0],
        journal.KIND,
        lambda r: r["ledger"]["slots"][0]["settlement"].update(response_sha256="f" * 64),
    )
    damaged = snapshot(trial["data"][0])
    with pytest.raises(DomainError):
        dispatch(trial)
    assert snapshot(trial["data"][0]) == damaged and len(trial["state"]["sent"]) == 1


def test_fixture_and_actual_wire_gates_refuse_before_reservation(trial):
    worker = trial["worker"]
    before = snapshot(trial["data"][0])
    original_settings, original_transport = worker.s, worker.goal_planner_transport
    try:
        worker.store.test_only = False
        with pytest.raises(DomainError):
            dispatch(trial)
    finally:
        worker.store.test_only = True
    for change in (
        dict(mode="live"),
        dict(live_enabled=True),
        dict(token="synthetic-rejected-value"),
    ):
        worker.s = replace(original_settings, **change)
        with pytest.raises(DomainError):
            dispatch(trial)
    worker.s = original_settings
    worker.goal_planner_transport = object()
    with pytest.raises(DomainError):
        dispatch(trial)
    worker.goal_planner_transport = original_transport

    class Trap:
        def __getattribute__(self, name):
            raise AssertionError("no foreign source callback")

        def __repr__(self):
            raise AssertionError("no foreign repr")

    with pytest.raises(DomainError):
        dispatch(trial, source=Trap())
    envelope = json.loads(trial["wire"])
    for change in (
        dict(model="other"),
        dict(stream=True),
        dict(max_tokens=True),
        dict(max_tokens=1025),
    ):
        with pytest.raises(DomainError):
            dispatch(trial, wire=json.dumps(envelope | change).encode())
    rejected = sender._derive(response(model="different-model"), True, True)
    assert rejected.outcome.outcome == "UNKNOWN" and rejected.outcome.total_tokens == 8
    assert snapshot(trial["data"][0]) == before and trial["state"]["sent"] == []


def test_cancel_between_committed_marker_and_guard_never_reaches_transport(
    trial, monkeypatch, tmp_path
):
    original = InternModel.request_serialized_captured

    def cancel_before_adapter(self, wire, guard):
        assert read(trial).ledger.slots[0].attempted
        trial["data"][0].command(
            trial["data"][3], trial["job"]["id"], "cancel", trial["job"]["version"]
        )
        return original(self, wire, guard)

    monkeypatch.setattr(InternModel, "request_serialized_captured", cancel_before_adapter)
    result = dispatch(trial)
    slot = result.journal.ledger.slots[0]
    assert trial["state"]["sent"] == [] and slot.attempted and not slot.accepted
    assert result.journal.ledger.halted and slot.settlement.total_tokens is None
    assert result.capture_bytes == 0 and result.may_have_sent
    (tmp_path / "marker-before-guard-cancel.json").write_text(result.model_dump_json(indent=2))
    # EMPTY archives cannot invent a nonempty digest or known usage.
    alter_pair(
        trial["data"][0],
        sender.CAPTURE,
        lambda r: (r.update(raw_sha256="e" * 64), r["outcome"].update(response_sha256="e" * 64)),
    )
    alter_pair(
        trial["data"][0],
        journal.KIND,
        lambda r: r["ledger"]["slots"][0]["settlement"].update(response_sha256="e" * 64),
    )
    damaged = snapshot(trial["data"][0])
    with pytest.raises(DomainError):
        dispatch(trial)
    assert snapshot(trial["data"][0]) == damaged and trial["state"]["sent"] == []


def test_cancel_after_guard_may_send_once_and_retains_late_body(trial, monkeypatch, tmp_path):
    entered, release = Event(), Event()
    trace = []
    original = InternModel.request_serialized_captured

    def observed(self, wire, guard):
        def recorded(request):
            answer = guard(request)
            trace.append("guard-transaction-finished")
            return answer

        return original(self, wire, recorded)

    monkeypatch.setattr(InternModel, "request_serialized_captured", observed)

    def handler(request):
        trace.append("mock-handler-entered-may-have-sent")
        entered.set()
        assert release.wait(8)
        return httpx.Response(200, content=trial["state"]["reply"])

    trial["state"]["hook"] = handler
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(dispatch, trial)
        try:
            assert entered.wait(8)
            trial["data"][0].command(
                trial["data"][3], trial["job"]["id"], "cancel", trial["job"]["version"]
            )
            trace.append("actual-cancel-committed")
        finally:
            release.set()
        result = future.result(timeout=15)
    slot = result.journal.ledger.slots[0]
    assert trace == [
        "guard-transaction-finished",
        "mock-handler-entered-may-have-sent",
        "actual-cancel-committed",
    ]
    assert len(trial["state"]["sent"]) == 1 and slot.settlement.total_tokens == 8
    assert not slot.accepted and result.journal.ledger.halted and result.capture_bytes > 0
    before = snapshot(trial["data"][0])
    assert dispatch(trial).journal.duplicate
    assert snapshot(trial["data"][0]) == before and len(trial["state"]["sent"]) == 1
    (tmp_path / "guard-to-transport-window.json").write_text(
        json.dumps(
            dict(
                trace=trace,
                mock_handler_calls=1,
                claim="DB guard cannot undo already possible IO",
                result=result.model_dump(mode="json"),
            ),
            indent=2,
        )
    )


class Prefix(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield json.dumps(dict(model="intern-s2", usage=dict(prompt_tokens=5))).encode()
        raise httpx.ReadTimeout("synthetic received prefix only")


def test_adapter_received_prefix_derives_partial_usage_and_never_retries(trial, tmp_path):
    trial["state"]["hook"] = lambda request: httpx.Response(200, stream=Prefix())
    result = dispatch(trial)
    slot = result.journal.ledger.slots[0]
    assert result.response_verdict == "UNKNOWN_OR_REJECTED" and result.journal.ledger.halted
    assert slot.settlement.outcome == "UNKNOWN" and slot.settlement.prompt_tokens == 5
    assert slot.settlement.completion_tokens is slot.settlement.total_tokens is None
    assert not slot.accepted and len(trial["state"]["sent"]) == 1
    before = snapshot(trial["data"][0])
    assert dispatch(trial).journal.duplicate
    assert snapshot(trial["data"][0]) == before and len(trial["state"]["sent"]) == 1
    (tmp_path / "received-prefix-unknown.json").write_text(result.model_dump_json(indent=2))


def test_capture_then_journal_cas_conflict_rolls_back_six_rows_without_resend(
    trial, monkeypatch, tmp_path
):
    checkpoint = []
    original_adapter, original_cas = InternModel.request_serialized_captured, journal._cas_pair

    def observed(self, wire, guard):
        result = original_adapter(self, wire, guard)
        checkpoint.append(snapshot(trial["data"][0]))
        return result

    def conflict(c, owner, entity, kind, key, previous, current):
        if kind == journal.QUOTA and checkpoint:
            previous = copy.deepcopy(previous)
            previous["response"]["revision"] -= 1
        return original_cas(c, owner, entity, kind, key, previous, current)

    monkeypatch.setattr(InternModel, "request_serialized_captured", observed)
    monkeypatch.setattr(journal, "_cas_pair", conflict)
    with pytest.raises(DomainError) as failed:
        dispatch(trial)
    assert failed.value.code == "VERSION_CONFLICT" and len(checkpoint) == 1
    assert snapshot(trial["data"][0]) == checkpoint[0]
    saved = read(trial)
    assert (
        saved.revision == 2
        and saved.ledger.slots[0].attempted
        and saved.ledger.slots[0].settlement is None
    )
    assert len(records(trial["data"][0])) == 4 and len(trial["state"]["sent"]) == 1
    duplicate = dispatch(trial)
    assert (
        duplicate.journal.duplicate
        and duplicate.capture_sha256 is None
        and not duplicate.adapter_entered
    )
    assert snapshot(trial["data"][0]) == checkpoint[0] and len(trial["state"]["sent"]) == 1
    (tmp_path / "capture-cas-rollback.json").write_text(
        json.dumps(
            dict(
                all_55_tables_strict_equal_to_marked_checkpoint=True,
                mock_handler_calls=1,
                pending=duplicate.model_dump(mode="json"),
            ),
            indent=2,
        )
    )


def child_guard(transport, io, methods):
    def forbidden(*args, **kwargs):
        io.append("FORBIDDEN_REAL_IO")
        raise AssertionError("offline child")

    httpx.HTTPTransport.handle_request = forbidden
    httpx.AsyncHTTPTransport.handle_async_request = forbidden
    Settings.from_env = forbidden
    for name in (
        "request",
        "request_serialized",
        "request_serialized_captured",
        "_request_serialized",
        "_deadline_request",
    ):
        original = getattr(InternModel, name)

        def guarded(self, *args, _original=original, _name=name, **kwargs):
            assert (
                type(self) is InternModel
                and self.transport is transport
                and type(transport) is httpx.MockTransport
            )
            assert (
                self.settings.mode == "mock" and self.settings.token == "synthetic-offline-planner"
            )
            methods.append(_name)
            return _original(self, *args, **kwargs)

        setattr(InternModel, name, guarded)


def child_main():
    d = json.load(sys.stdin)
    io, methods, sent = [], [], []
    store = Store(d["url"], test_only=True)
    contract = gate.parse_contract(d["contract"])
    source = policy.SourceVerificationResult.model_validate(d["source"])
    wire = d["wire"].encode("ascii")

    def handler(request):
        sent.append(hashlib.sha256(request.content).hexdigest())
        print(json.dumps(dict(event="mock-handler", count=len(sent))), flush=True)
        assert d["mode"] == "crash"
        return httpx.Response(200, content=base64.b64decode(d["reply_b64"]))

    transport = httpx.MockTransport(handler)
    child_guard(transport, io, methods)
    worker = Worker(
        store,
        Settings(
            d["url"],
            Path(d["data_dir"]),
            quota_subject=contract.quota_subject,
            goal_planner_provider="intern-s2",
        ),
        goal_planner_transport=transport,
    )
    if d["mode"] == "recover":
        item = policy.ReservationIdentity.model_validate(d["identity"])
        assert worker.id != item.worker_id
        result = sender.dispatch_offline(
            worker, contract, d["key"], item, wire, source, expected_revision=0
        )
        assert (
            result.journal.duplicate
            and not result.adapter_entered
            and not sent
            and not methods
            and not io
        )
        print(
            json.dumps(
                dict(
                    event="recovered-history",
                    result=result.model_dump(mode="json"),
                    methods=methods,
                    sent=sent,
                    io=io,
                )
            ),
            flush=True,
        )
        store.engine.dispose()
        return
    job = store.claim(worker.id, 30)
    assert job["id"] == d["run_id"]
    with store.tx() as c:
        context = policy.check_run(
            store,
            c,
            contract.principal_id,
            contract,
            d["key"],
            "generate",
            job["id"],
            job["version"],
            job["fence"],
            worker.id,
        )
    item = policy.identity_for(context, source, d["attempt_id"], wire)
    print(
        json.dumps(dict(event="actual-child-claim", identity=item.model_dump(mode="json"))),
        flush=True,
    )
    original = InternModel.request_serialized_captured

    def crash(self, wire, guard):
        if d["phase"] == "marker-before-adapter":
            print(
                json.dumps(
                    dict(
                        event="crash-after-marker-before-adapter", sent=sent, methods=methods, io=io
                    )
                ),
                flush=True,
            )
            os._exit(17)
        captured = original(self, wire, guard)
        print(
            json.dumps(
                dict(
                    event="crash-after-capture-before-archive",
                    sent=sent,
                    methods=methods,
                    io=io,
                    received_sha256=hashlib.sha256(captured.body).hexdigest(),
                )
            ),
            flush=True,
        )
        os._exit(23)

    InternModel.request_serialized_captured = crash
    sender.dispatch_offline(worker, contract, d["key"], item, wire, source, expected_revision=0)
    raise AssertionError("planned process exit did not occur")


def subprocess_call(payload, tmp_path, name):
    environment = {k: v for k, v in os.environ.items() if not k.startswith(("SIM2ACT_", "INTERN_"))}
    environment["PYTHONPATH"] = str(Path(__file__).parent)
    command = [
        sys.executable,
        "-c",
        "from test_production_trial_sender import child_main; child_main()",
    ]
    result = subprocess.run(
        command,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=environment,
        timeout=25,
    )
    (tmp_path / (name + ".stdout")).write_text(result.stdout)
    (tmp_path / (name + ".stderr")).write_text(result.stderr)
    (tmp_path / (name + "-execution.json")).write_text(
        json.dumps(
            dict(
                command=command,
                exit_code=result.returncode,
                planned_exit=payload["mode"] == "crash",
            ),
            indent=2,
        )
    )
    return result, [json.loads(line) for line in result.stdout.splitlines()]


@pytest.mark.parametrize(
    "phase,exit_code,send_count",
    [("marker-before-adapter", 17, 0), ("received-before-archive", 23, 1)],
)
def test_crashed_sender_new_process_recovery_is_history_only(
    env, tmp_path, phase, exit_code, send_count
):
    t = prepare(env, claim=False)
    before = snapshot(env[0])
    payload = dict(
        url=str(env[0].engine.url),
        contract=t["contract"].model_dump(mode="json"),
        source=t["source"].model_dump(mode="json"),
        key=t["approval"].request_key,
        wire=t["wire"].decode("ascii"),
        reply_b64=base64.b64encode(t["state"]["reply"]).decode("ascii"),
        data_dir=str(tmp_path),
        mode="crash",
        phase=phase,
        run_id=t["run_id"],
        attempt_id=new_id("attempt"),
    )
    crashed, trace = subprocess_call(payload, tmp_path, "crashed-sender")
    assert crashed.returncode == exit_code, crashed.stderr
    identity = trace[0]["identity"]
    assert trace[0]["event"] == "actual-child-claim"
    assert len(trace[-1]["sent"]) == send_count and trace[-1]["io"] == []
    current = journal.read(
        env[0], env[3], t["contract"], t["approval"].request_key, t["source"].account_id
    )
    assert current.revision == current.quota_revision == 2 and len(current.ledger.slots) == 1
    slot = current.ledger.slots[0]
    assert slot.attempted and slot.settlement is None and not slot.accepted
    assert len(records(env[0])) == 4
    checkpoint = snapshot(env[0])
    recovered, receipt = subprocess_call(
        payload | dict(mode="recover", identity=identity), tmp_path, "fresh-recovery"
    )
    assert recovered.returncode == 0, recovered.stderr
    assert (
        receipt[-1]["event"] == "recovered-history"
        and receipt[-1]["sent"] == receipt[-1]["methods"] == []
    )
    assert (
        receipt[-1]["result"]["may_have_sent"] and receipt[-1]["result"]["capture_sha256"] is None
    )
    assert snapshot(env[0]) == checkpoint
    protected(before, checkpoint)
    (tmp_path / "process-window-proof.json").write_text(
        json.dumps(
            dict(
                phase=phase,
                planned_crash_exit=exit_code,
                actual_mock_handler_calls=send_count,
                fresh_recovery_adapter_calls=0,
                after_recovery_all_55_tables_strict_equal=True,
                pending=current.model_dump(mode="json"),
            ),
            indent=2,
        )
    )
    t["data"][2].close()
