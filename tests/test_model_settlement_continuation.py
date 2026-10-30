"""Original advance_model five writes/rejection with real SQLite and no IO.

Recipe/phase ancestry, sender, journal ledger and non-trial guard are explicit
unit stubs. Current consent, Grants, full Run predicate, NS body archives,
response pairing, five production writes, rollback and rejection CAS are real.
The unmodified full P-B test remains the complete lineage acceptance gate.
"""

import copy
import hashlib
import json
import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace

import httpx
import pytest
import test_pb_spec_production_controller as prepared
from sqlalchemy import event, insert, select, update
from sqlalchemy.exc import OperationalError
from test_pb_spec_production_controller import prepare_pb

from sim2act import app_jobs
from sim2act import natural_live_admission as gate
from sim2act import natural_source_archives as archive
from sim2act import natural_spec_runtime as runtime
from sim2act import natural_specs as natural
from sim2act import pa_spec_apps as spec
from sim2act import pa_trial_dispatch as trial
from sim2act import production_evidence as evidence
from sim2act import production_trial_admission as admission
from sim2act import production_trial_policy as policy
from sim2act import spec_production as production
from sim2act.contracts import Limits
from sim2act.db import (
    attempts,
    events,
    fingerprint,
    grants,
    internal_app_runs,
    new_id,
    operations,
    reservations,
    runs,
)
from sim2act.errors import DomainError
from sim2act.model import CapturedResponse, InternModel, normalize_usage


@pytest.mark.parametrize("case", [
    "success", "source_revoke", "grant_expiry", "raw_pair", "first_proof",
    "reject_owner", "limits_platform", "limits_node", "tail_reentry",
    "output_drift", "failed_write",
    "tail_extra_expiry", "row_mapping_drift",
    "source_identity_drift", "source_deadline_drift", "snapshot_pending_control",
])
def test_original_model_settlement_atomicity_and_continuation(env, tmp_path, monkeypatch, case):
    def forbidden(*_, **__):
        pytest.fail("No real or Mock model transport in settlement boundary units")
    for transport in (httpx.HTTPTransport, httpx.AsyncHTTPTransport, httpx.MockTransport):
        for method in ("handle_request", "handle_async_request"):
            if hasattr(transport, method):
                monkeypatch.setattr(transport, method, forbidden)
    # Grant expiry is part of the frozen authorization fingerprint. Establish
    # this synthetic fixture deadline before the original contract is approved.
    if case in {"grant_expiry", "reject_owner"}:
        original_frozen = prepared.frozen
        def expiring_contract(data, **kwargs):
            contract, consent = original_frozen(data, **kwargs)
            with data[0].tx() as c:
                c.execute(update(grants).where(grants.c.resource_id == contract.bindings[1].resource_id)
                          .values(expires_at=time.time() + 10))
                authorization = gate.authorization_fingerprint(c, data[3], contract.project_id,
                    contract.runtime_id, [b.resource_id for b in contract.bindings])
            contract = contract.model_copy(update=dict(authorization_fingerprint=authorization))
            return contract, consent.model_copy(update=dict(
                expected_contract_fingerprint=fingerprint(contract.model_dump())))
        with monkeypatch.context() as fixture_patch:
            fixture_patch.setattr(prepared, "frozen", expiring_contract)
            data, selected = prepare_pb(env, tmp_path)
    else:
        data, selected = prepare_pb(env, tmp_path)
    store, settings, client, user, pid, *_ = data
    contract = selected.contract
    binding = production.ProductionTrialBinding(contract, selected.approval_key, selected.account_id)
    clock = [time.time()]
    if case in {"grant_expiry", "tail_extra_expiry", "reject_owner", "source_deadline_drift"}:
        monkeypatch.setattr(time, "time", lambda: clock[0])
    rid, aid, app_id = new_id("run"), new_id("attempt"), new_id("apprun")
    target = contract.bindings[1]
    worker = SimpleNamespace(store=store, s=settings, pa_trial=binding, id="model-boundary-worker",
        stop=threading.Event(), goal_planner_transport=None, _journal_trial_store=store,
        _journal_trial_binding=binding, _journal_trial_drift=False)
    now = time.time()
    with store.tx() as c:
        c.execute(insert(runs).values(id=rid, principal_id=user, project_id=pid,
            runtime_id=contract.runtime_id, goal=target.goal_snapshot.content.goal,
            resource_refs=[target.resource_id], status="RUNNING", request_key="model-boundary",
            fingerprint="a" * 64, created_at=now, lease_until=now + 30, fence=1, version=1,
            worker_id=worker.id, context=dict(spec_family=natural.VERSION, requests=0, tools=0),
            cancel_intent=False))
        c.execute(insert(internal_app_runs).values(id=app_id, instance_id="unit-instance",
            release_id="unit-release", principal_id=user, request_key="unit-app-run",
            fingerprint="b" * 64, input={}, status="QUEUED"))
        authority = gate.StageAuthority(contract_fingerprint=binding.contract_fingerprint,
            stage="cold", run_id=rid, accepted_fingerprint="a" * 64, app_run_id=app_id,
            instance_id="unit-instance", instance_revision=1, runtime_id=contract.runtime_id,
            app_id="unit-app", candidate_fingerprint="b" * 64, recipe_fingerprint="c" * 64,
            release_id="unit-release", release_fingerprint="d" * 64,
            generation_run_id=new_id("run"), generation_candidate_fingerprint="e" * 64,
            target_goal_fingerprint=target.goal_fingerprint,
            authorization_fingerprint=contract.authorization_fingerprint)
        gate._save(c, user, gate.entity(contract), gate.PHASE, "cold", gate.StageApproveInput(
            authority=authority, expected_authority_fingerprint=fingerprint(authority.model_dump()),
            approval_key=binding.approval_key, request_key="unit-model-phase",
            consent="BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL"))
        if case == "tail_extra_expiry":
            c.execute(update(grants).where(grants.c.resource_id == env[6])
                      .values(expires_at=clock[0] + 10))
        run = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
    limits = Limits(**{k: getattr(settings, k) for k in Limits.model_fields})
    node = limits.model_copy(update=dict(max_requests=3))
    step = dict(step_id="unit-model")
    action = dict(executor=dict(ref=next(iter(natural.MODEL_KINDS))), limits=node.model_dump(),
                  output_schema=dict(type="object", properties={}, additionalProperties=False))
    bound = dict(app_run=dict(id=app_id), source=dict(resource_id=target.resource_id),
        audit_fingerprint="f" * 64, snapshot=dict(natural_spec_clock=dict(deadline=now + 300)),
        draft=dict(candidate=dict(manifest=dict(runtime_limits=limits.model_dump()))),
        plan=dict(definition=dict(actions=[action], manifest=dict(workflow=[step])),
                  plan_fingerprint="e" * 64))
    raw = dict(model="intern-s2", choices=[], usage=dict(prompt_tokens=1, completion_tokens=1,
                                                       total_tokens=2))
    trace, sql, transactions = [], [], []
    state = dict(post=False, armed=False, reject_owner=False, journal=0, post_admission=0,
                 post_source=0, tx=None, context=None)
    connection = []
    monkeypatch.setattr(runtime, "enabled", lambda _: None)
    monkeypatch.setattr(runtime, "renew", lambda *_, **__: None)
    monkeypatch.setattr(runtime, "effective", lambda *_, **__: node)
    monkeypatch.setattr(runtime, "messages", lambda *_, **kwargs: [dict(role="user", content="synthetic")])
    monkeypatch.setattr(runtime, "parse", lambda *_: ({}, normalize_usage(raw)))
    monkeypatch.setattr(spec, "intent_for", lambda *_: dict(tool="unit-model", args={}))
    monkeypatch.setattr(spec, "receipt_for", lambda op, *_: dict(operation_id=op, data={}))
    monkeypatch.setattr(production, "evidence_mode", lambda *_: "LIVE")
    monkeypatch.setattr(trial, "_binding", lambda w: binding if w is worker else None)
    monkeypatch.setattr(trial, "_stage", lambda *_: "cold")
    monkeypatch.setattr(admission, "_qualified", lambda: None)
    monkeypatch.setattr(store, "_frozen_contract_after_scope", lambda *_: SimpleNamespace(limits=limits))

    def own_live(s, c, original):
        actual = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        assert actual["worker_id"] == worker.id and actual["fence"] == original["fence"]
        return actual
    monkeypatch.setattr(app_jobs, "lock_live", own_live)

    def bound_stub(s, c, *args):
        if state["post"]:
            trace.append("post_binding")
        value = copy.deepcopy(bound)
        value["app_run"] = c.execute(select(internal_app_runs).where(
            internal_app_runs.c.id == app_id)).mappings().one()
        assert runtime._model_inputs(dict(value=value["app_run"])) == fingerprint(
            dict(value=dict(value["app_run"])))
        return value
    monkeypatch.setattr(spec, "bound", bound_stub)

    def receipts_stub(s, c, current, b, **kwargs):
        if state["post"]:
            trace.append("post_receipts")
            row = c.execute(select(attempts).where(attempts.c.id == aid)).mappings().one()
            assert row["status"] == "VERIFIED"
            assert runtime.anchor(c, rid, "NS_SETTLED", aid)["attempt_fingerprint"] == fingerprint(dict(row))
            assert c.execute(select(events.c.id).where(events.c.run_id == rid,
                events.c.kind == "SPEC_STEP_VERIFIED")).first()
            if case == "output_drift":
                b["audit_fingerprint"] = "0" * 64
            if case == "row_mapping_drift":
                b["app_run"]["input"]["nested_drift"] = True
            if case in {"source_identity_drift", "source_deadline_drift"}:
                state["source_changed"] = True
        return {}, []
    monkeypatch.setattr(spec, "receipts", receipts_stub)

    def phase_stub(s, c, current_user, current_contract, key, stage, run_id, version, fence, worker_id):
        if state["post"]:
            state["post_admission"] += 1
            trace.append("full_post_admission")
            if case == "first_proof":
                raise DomainError("VERSION_CONFLICT", "Full postwrite proof rejected")
        approval = gate._approved(s, c, current_user, current_contract, key)
        actual = c.execute(select(runs).where(runs.c.id == run_id)).mappings().one()
        gate._require_run_context_row(user, contract, "cold", actual, version, fence,
                                     approval, authority, time.time())
        return SimpleNamespace(stage="cold", approval_fingerprint=fingerprint(approval.model_dump()),
            stage_fingerprint=fingerprint(authority.model_dump()),
            deadline=min(actual["lease_until"], contract.expires_at),
            requirements_fingerprint=fingerprint(evidence.requirements_for(user, contract, key).model_dump()))
    monkeypatch.setattr(policy, "check_run", phase_stub)
    monkeypatch.setattr(trial, "_pb_source", lambda *_: None)

    def guard_body(w, c, original, b, delta=0, *, _commit_out=None, _model_out=None, _model_after=None):
        current = own_live(store, c, original)
        store.authorize(c, user, contract.runtime_id, pid, target.resource_id, "resource.read")
        if _model_after is not None:
            assert _model_after.state == "TAIL_BUSY"
            trace.append("tail_body")
            if case == "tail_extra_expiry":
                extra = (user, contract.runtime_id, pid, env[6], "resource.read")
                assert extra not in _model_after.authorities
                store.authorize(c, *extra)
                state["armed"] = True
            if case == "tail_reentry":
                trial.settle_verified(w, c, current, aid, raw, _model_after=_model_after)
            _model_after.tail_row(w, c, current, b)
        else:
            trial.check_commit(w, c, current,
                **({"_model_out": _model_out} if _model_out is not None else {}))
        return current
    monkeypatch.setattr(spec, "_commit_guard", guard_body)

    def source(current_user, current_contract, key):
        if state["post"]:
            state["post_source"] += 1
        if state["armed"]:
            state["armed"] = False
            if case == "source_revoke":
                assert connection[0].execute(update(grants).where(grants.c.resource_id == target.resource_id,
                    grants.c.principal_id == user, grants.c.tool_ref == "resource.read")
                    .values(revoked=True)).rowcount == 1
            elif case in {"grant_expiry", "reject_owner", "tail_extra_expiry"}:
                clock[0] += 11
            elif case == "failed_write":
                with pytest.raises(OperationalError):
                    connection[0].exec_driver_sql("UPDATE missing_model_settlement_table SET value=1")
        scope = evidence.requirements_for(current_user, current_contract, key)
        changed = state.get("source_changed", False)
        if case == "source_deadline_drift" and changed:
            clock[0] += 11
            state["source_changed"] = False
        return policy.SourceVerificationResult(requirements_fingerprint=fingerprint(scope.model_dump()),
            account_id=binding.account_id, quota_subject=scope.quota_subject, provider=scope.provider,
            model=scope.model, endpoint=scope.endpoint,
            evidence_fingerprint=("b" if case == "source_identity_drift" and changed else "a") * 64,
            decision="ALLOW",
            legal_free_entitlement=True, enforced_non_chargeable=True, revoked=False,
            observed_at=time.time(), expires_at=(clock[0] + 10
                if case == "source_deadline_drift" and not state["post"] else
                now + 10 if case == "source_deadline_drift" and not changed else contract.expires_at))
    monkeypatch.setattr(evidence, "resolve_account", source)

    def reserve(run_id, fence, ctx, *, request_tools, natural_spec_request):
        wire = runtime.body(ctx["messages"], [], node.max_output_tokens,
            request_protocol=runtime.request_protocol(natural_spec_request))
        state["wire"] = wire
        with store.tx() as c:
            c.execute(insert(attempts).values(id=aid, run_id=rid, status="STARTED", mode="LIVE",
                created_at=time.time(), request_model="intern-s2", reserved_tokens=len(wire)+1024,
                parameters=dict(natural_spec=natural_spec_request, natural_spec_wire=dict(
                    sha256=hashlib.sha256(wire).hexdigest(), bytes=len(wire)))))
            c.execute(insert(reservations).values(id=aid, run_id=rid, subject=settings.quota_subject,
                                                 created_at=time.time()))
            c.execute(insert(operations).values(id=natural_spec_request["operation_id"], run_id=rid,
                call_id=step["step_id"], status="PREPARED", fingerprint="a" * 64, tool_ref="unit-model"))
            archive.record_request(store, c, run, aid, wire)
        return aid
    worker.reserve = reserve

    def adapter(w, job, attempt, wire, guard, provider, **kwargs):
        guard(httpx.Request("POST", InternModel.ENDPOINT, content=wire,
                            headers={"Authorization": "Bearer synthetic-offline-natural-spec"}))
        return CapturedResponse(raw, json.dumps(raw).encode())
    monkeypatch.setattr(trial, "request_captured", adapter)

    def identity(w, c, current, attempt):
        assert attempt == aid and current["id"] == rid
        archive.receipt_owner(c, current, attempt, state["wire"])
        return binding
    monkeypatch.setattr(trial, "_identity", identity)

    def journal_stub(s, c, b, current, attempt, response):
        state["journal"] += 1
        trace.append("post_journal")
        _, wire = archive._read(c, user, current, attempt, archive.REQUEST)
        _, response_bytes = archive._read(c, user, current, attempt, archive.RESPONSE)
        assert archive.receipt_owner(c, current, attempt, wire)
        row = c.execute(select(attempts).where(attempts.c.id == attempt)).mappings().one()
        gate.require(runtime.response_archive(json.loads(response_bytes)) == runtime.response_archive(response),
                     "Actual received response belongs to a different handoff")
        return SimpleNamespace(model_dump=lambda: dict(unit_ledger=True)), \
            SimpleNamespace(model_dump=lambda: dict(unit_capture=True)), json.loads(response_bytes), row
    monkeypatch.setattr(trial, "_journal_chain", journal_stub)
    monkeypatch.setattr(trial, "reject", lambda *args: None)

    original_event = store.event
    def observe(c, run_id, kind, value=None):
        result = original_event(c, run_id, kind, value)
        if run_id == rid and kind == "SPEC_STEP_VERIFIED":
            state["post"], state["tx"] = True, id(c.get_transaction())
        return result
    monkeypatch.setattr(store, "event", observe)

    def statement(c, cursor, query, parameters, ctx, many):
        transactions.append(c.get_transaction())  # Retain identity; IDs cannot recycle between TXs.
        sql.append(dict(transaction=id(c.get_transaction()), kind=query.lstrip().split()[0],
                        epoch=c.info.get("source_proof_write_epoch", 0)))
    event.listen(store.engine, "before_cursor_execute", statement)

    original_scope = runtime._model_settlement_read
    @contextmanager
    def scoped(w, c, inputs):
        connection[:] = [c]
        if case == "raw_pair":
            inputs["raw"] = {**inputs["raw"], "model": "wrong-paired-model"}
        try:
            with original_scope(w, c, inputs) as result:
                proof = result[2]
                state["context"] = proof
                assert proof.state == "READY" and state["journal"] == 1
                trace.append("ready")
                state["armed"] = case in {"source_revoke", "grant_expiry", "reject_owner", "failed_write"}
                if case in {"limits_platform", "limits_node"}:
                    key = "platform" if case == "limits_platform" else "node"
                    inputs[key].max_requests -= 1
                yield result
        except DomainError:
            if case == "reject_owner":
                state["reject_owner"] = True
            raise
    monkeypatch.setattr(runtime, "_model_settlement_read", scoped)
    original_owner = archive.receipt_owner
    def owner(*args, **kwargs):
        if state["reject_owner"]:
            raise DomainError("VERSION_CONFLICT", "Synthetic owner competition blocks rejection")
        return original_owner(*args, **kwargs)
    monkeypatch.setattr(archive, "receipt_owner", owner)
    if case == 'snapshot_pending_control':
        from sim2act._sqlite_model_snapshot import SnapshotChanged, promote
        store._enable_local_model_snapshots()
        original_connection = runtime._model_writer_connection
        @contextmanager
        def competing_snapshot(w, candidate, plan):
            try:
                with original_connection(w, candidate, plan) as pair:
                    c = pair[0]
                    c.execute(select(attempts.c.id).where(attempts.c.id == aid)).one()
                    # A real other-connection commit invalidates the snapshot.
                    with store.tx() as other:
                        store.event(other,rid,'UNIT_CONCURRENT_SNAPSHOT_COMMIT',{})
                    epoch=store._local_model_control.local.epoch
                    epoch.commands.add(threading.Event())  # Undelivered command completion, NOT an ACK.
                    epoch.deadline=time.monotonic()+.02
                    promote(c)
                    c.execute(update(attempts).where(attempts.c.id == aid).values(status='VERIFIED'))
                    pytest.fail('A stale WAL snapshot unexpectedly wrote')
                    yield pair
            except SnapshotChanged as conflict:
                assert isinstance(conflict.__cause__,OperationalError)
                state['actual_snapshot_conflict']=True
                raise
        monkeypatch.setattr(runtime,'_model_writer_connection',competing_snapshot)
    error = None
    try:
        if case == "success":
            assert runtime.advance_model(worker, run) is True
        elif case == 'snapshot_pending_control':
            assert runtime.advance_model(worker,run) is False
        else:
            with pytest.raises(DomainError) as caught:
                runtime.advance_model(worker, run)
            error = caught.value.public()
        (tmp_path / "boundary-handoff.json").write_text(json.dumps(dict(
            case=case, error=error, trace=trace, post=state["post"],
            armed=state["armed"], post_admission=state["post_admission"]), indent=2) + "\n")
        with store.tx() as c:
            attempt = dict(c.execute(select(attempts).where(attempts.c.id == aid)).mappings().one())
            op = dict(c.execute(select(operations).where(operations.c.run_id == rid)).mappings().one())
            kinds = c.execute(select(events.c.kind).where(events.c.run_id == rid)).scalars().all()
            app_state = c.execute(select(internal_app_runs.c.status).where(internal_app_runs.c.id == app_id)).scalar_one()
            assert archive._read(c, user, run, aid, archive.RESPONSE)[1]
        assert attempt["response"]["received_raw"] and "NS_RECEIVED" in kinds
        if case == "success":
            assert attempt["status"] == op["status"] == "VERIFIED" and app_state == "RUNNING"
            assert "NS_SETTLED" in kinds and "SPEC_STEP_VERIFIED" in kinds
            assert state["post_admission"] == 1 and state["journal"] == 1
            assert trace.index("post_journal") < trace.index("ready") < trace.index("tail_body")
            assert state["context"].state == "CLOSED" and not state["context"].active
            statements = [row["kind"] for row in sql if row["transaction"] == state["tx"]]
            assert [kind for kind in statements if kind != "SELECT"] == [
                "BEGIN", "UPDATE", "INSERT", "UPDATE", "UPDATE", "INSERT"]
        elif case == 'snapshot_pending_control':
            assert state['actual_snapshot_conflict']
            assert attempt['status']=='RECEIVED' and op['status']=='DISPATCHED'
            assert 'NS_SETTLED' not in kinds and 'NS_REJECTED' not in kinds
            with store.tx() as c:
                current=c.execute(select(runs).where(runs.c.id==rid)).mappings().one()
                assert current['status']==run['status'] and current['version']==run['version']
            assert app_state=='QUEUED'
        else:
            assert "NS_SETTLED" not in kinds and "SPEC_STEP_VERIFIED" not in kinds
            assert app_state == "QUEUED" and op["receipt"] is None
            expected = "RECEIVED" if case == "reject_owner" else "REJECTED_KNOWN"
            assert attempt["status"] == expected
            assert op["status"] == ("DISPATCHED" if case == "reject_owner" else "REJECTED_KNOWN")
            assert ("NS_REJECTED" in kinds) == (case != "reject_owner")
            assert state["post_admission"] == 1  # no fallback admission after failure
            if case in {"grant_expiry", "tail_extra_expiry"}:
                assert error["code"] == "GRANT_REVOKED"
        (tmp_path / "model-settlement-boundary.json").write_text(json.dumps(dict(case=case,
            error=error, trace=trace, post_full_admission=state["post_admission"],
            journal_traversals=state["journal"], post_source_calls=state["post_source"],
            attempt=attempt["status"], operation=op["status"], app=app_state,
            events=kinds, sql=sql, real_models=0, mock_exchanges=0,
            actual_advance_model_five_writes=True,
            unit_stubs=["recipe/phase ancestry", "sender", "journal ledger", "non-trial guard",
                        "model parse", "renew", "software eligibility", "trial reject accounting"]),
            indent=2)+"\n")
    finally:
        event.remove(store.engine, "before_cursor_execute", statement)
        client.close()
