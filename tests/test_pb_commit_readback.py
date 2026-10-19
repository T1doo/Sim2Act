"""Local continuation boundary units; initial phase proof is stubbed, no models.

The original full P-B controller test separately proves actual phase/lineage.
These tests use real SQLite writes, current consent/permissions, fixed-source
checks and the original complete Run predicate, without changing clocks/caps.
"""
import json
import threading
import time
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import insert, select, update
from sqlalchemy.exc import OperationalError
from test_pb_spec_production_controller import prepare_pb

from sim2act import natural_live_admission as gate
from sim2act import pa_trial_dispatch as trial
from sim2act import pb_natural_specs as pb
from sim2act import production_evidence as evidence
from sim2act import production_trial_admission as admission
from sim2act import production_trial_policy as policy
from sim2act import spec_production as production
from sim2act.db import fingerprint, grants, new_id, runs
from sim2act.errors import DomainError


@pytest.mark.parametrize("case", [
    "continue_once", "missing_stamp", "no_scope", "settings_changed",
    "successful_write", "failed_write", "source_callback_write", "authority_revoke",
    "fixed_source_missing", "fixed_source_deny", "fixed_source_expired", "qualification_deny",
    "run_cancelled", "phase_seal_changed", "first_full_failure", "settings_during_full",
    "controller_during_full",
    "source_callback_controller_drift",
    "tail_authority_revoke",
])
def test_postwrite_commit_readback_boundary(env, tmp_path, monkeypatch, case):
    http_calls = []
    def forbidden(*args, **kwargs):
        http_calls.append(True)
        raise AssertionError("No real or Mock model in readback boundary units")
    for transport, names in ((httpx.HTTPTransport, ("handle_request",)),
            (httpx.AsyncHTTPTransport, ("handle_async_request",)),
            (httpx.MockTransport, ("handle_request", "handle_async_request"))):
        for name in names:
            monkeypatch.setattr(transport, name, forbidden)
    data, selected = prepare_pb(env, tmp_path)
    store, settings, _, user, pid, *_ = data
    contract = selected.contract
    binding = production.ProductionTrialBinding(contract, selected.approval_key, selected.account_id)
    rid = new_id("run")
    now = time.time()
    with store.tx() as c:
        c.execute(insert(runs).values(id=rid, principal_id=user, project_id=pid,
            runtime_id=contract.runtime_id, goal="Synthetic boundary unit",
            resource_refs=[contract.bindings[1].resource_id], status="RUNNING",
            request_key="readback-boundary", fingerprint="a" * 64, created_at=now,
            lease_until=now + contract.caps.lease_seconds, fence=1, version=1,
            worker_id="boundary-worker", context={}, cancel_intent=False))
        authority = gate.StageAuthority(contract_fingerprint=binding.contract_fingerprint,
            stage="cold", run_id=rid, accepted_fingerprint="a" * 64,
            app_run_id="synthetic-app-run", instance_id="synthetic-instance", instance_revision=1,
            runtime_id=contract.runtime_id, app_id="synthetic-app", candidate_fingerprint="b" * 64,
            recipe_fingerprint="c" * 64, release_id="synthetic-release", release_fingerprint="d" * 64,
            generation_run_id=new_id("run"), generation_candidate_fingerprint="e" * 64,
            target_goal_fingerprint=contract.bindings[1].goal_fingerprint,
            authorization_fingerprint=contract.authorization_fingerprint)
        phase = gate.StageApproveInput(authority=authority,
            expected_authority_fingerprint=fingerprint(authority.model_dump()),
            approval_key=binding.approval_key, request_key="boundary-phase",
            consent="BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL")
        gate._save(c, user, gate.entity(contract), gate.PHASE, "cold", phase)
    worker = SimpleNamespace(store=store, s=settings, pa_trial=binding, id="boundary-worker",
        stop=threading.Event(), goal_planner_transport=None,
        _journal_trial_store=store, _journal_trial_binding=binding, _journal_trial_drift=False)
    calls = dict(full=0, binding=0, source=0, qualification=0, callback_rows=0)
    original_resolver = evidence.resolve_account
    def current_binding(w):
        calls["binding"] += 1
        assert w is worker and w.pa_trial is binding
        gate.require(not w._journal_trial_drift, "Controller binding drifted")
        return binding
    monkeypatch.setattr(trial, "_binding", current_binding)
    monkeypatch.setattr(trial, "_stage", lambda b, run: "cold")
    def complete_phase_stub(store, c, user, contract, key, stage, run_id, version, fence):
        calls["full"] += 1
        if case == "first_full_failure":
            raise DomainError("VERSION_CONFLICT", "Initial phase proof rejected")
        approval = gate._approved(store, c, user, contract, key)
        gate._saved(c, user, gate.entity(contract), gate.PHASE, "cold", gate.StageApproveInput)
        actual = c.execute(select(runs).where(runs.c.id == run_id)).mappings().one()
        gate._require_run_context_row(user, contract, stage, actual, version, fence,
            approval, authority, time.time())
        if case == "settings_during_full" and calls["full"] == 1:
            worker.s = replace(settings, max_tools=settings.max_tools - 1)
        elif case == "controller_during_full" and calls["full"] == 1:
            worker._journal_trial_drift = True
        return SimpleNamespace(stage="cold", approval_fingerprint=fingerprint(approval.model_dump()),
            stage_fingerprint=fingerprint(authority.model_dump()))
    monkeypatch.setattr(trial, "_admission", lambda w: complete_phase_stub)
    def qualify():
        calls["qualification"] += 1
        if case == "qualification_deny":
            raise DomainError("VERSION_CONFLICT", "Exact software qualification rejected")
    monkeypatch.setattr(admission, "_qualified", qualify)
    active_connection = []
    def source(user, current, key):
        calls["source"] += 1
        if case == "source_callback_write":
            calls["callback_rows"] += active_connection[0].execute(update(runs)
                .where(runs.c.id == rid).values(goal="Synthetic boundary unit")).rowcount
        elif case == "source_callback_controller_drift":
            # Worker.store's rejected replacement sets this sticky flag even
            # when its original Store pointer remains unchanged.
            worker._journal_trial_drift = True
        scope = evidence.requirements_for(user, current, key)
        at = time.time()
        return policy.SourceVerificationResult(requirements_fingerprint=fingerprint(scope.model_dump()),
            account_id=binding.account_id, quota_subject=scope.quota_subject,
            provider=scope.provider, model=scope.model, endpoint=scope.endpoint,
            evidence_fingerprint="f" * 64, decision="DENY" if case == "fixed_source_deny" else "ALLOW",
            legal_free_entitlement=case != "fixed_source_deny", enforced_non_chargeable=True,
            revoked=False, observed_at=at - 2,
            expires_at=at - 1 if case == "fixed_source_expired" else contract.expires_at)
    monkeypatch.setattr(evidence, "resolve_account",
        original_resolver if case == "fixed_source_missing" else source)
    error = None
    with store.tx() as c:
        active_connection.append(c)
        run = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        with pb._source_reads(store, c):
            out = {}
            if case == "first_full_failure":
                with pytest.raises(DomainError):
                    trial.check_commit(worker, c, run, _read_out=out)
                assert out == {}
            elif case == "settings_during_full":
                trial.check_commit(worker, c, run, _read_out=out)
                assert out == {}
                trial.check_commit_after_readback(worker, c, run, out)
                assert calls["full"] == 2
            elif case == "controller_during_full":
                trial.check_commit(worker, c, run, _read_out=out)
                assert out == {}
                with pytest.raises(DomainError, match="Controller binding drifted"):
                    trial.check_commit_after_readback(worker, c, run, out)
                assert calls["full"] == 1
            else:
                trial.check_commit(worker, c, run, _read_out=out)
                stamp = out.get("stamp")
                assert type(stamp) is trial._CommitReadback and not stamp.consumed
                assert not any(isinstance(v, gate.StageAuthority) for v in vars(stamp).values())
                tail_authorities = ()
                if case == "tail_authority_revoke":
                    with store.proof_authorities(c) as tail:
                        store.authorize(c, user, contract.runtime_id, pid, env[6], "resource.read")
                    tail_authorities = tuple(sorted(tail))
                    assert len(tail_authorities) == 1 and not set(tail_authorities).intersection(stamp.authorities)
                if case == "missing_stamp":
                    out.clear()
                elif case == "no_scope":
                    c.info.pop("pb_source_reads")
                elif case == "settings_changed":
                    worker.s = replace(settings, max_tools=settings.max_tools - 1)
                elif case in ("successful_write", "run_cancelled"):
                    values = dict(cancel_intent=True) if case == "run_cancelled" else dict(goal=run["goal"])
                    calls["callback_rows"] = c.execute(update(runs).where(runs.c.id == rid).values(**values)).rowcount
                elif case == "failed_write":
                    with pytest.raises(OperationalError):
                        c.exec_driver_sql("UPDATE definitely_missing_readback_table SET value=1")
                elif case in {"authority_revoke", "tail_authority_revoke"}:
                    original_recheck = store.recheck_proof_authorities
                    def revoke(connection, proof):
                        calls["callback_rows"] = connection.execute(update(grants).where(
                            grants.c.principal_id == user, grants.c.project_id == pid,
                            grants.c.resource_id == (env[6] if case == "tail_authority_revoke" else contract.bindings[1].resource_id),
                            grants.c.tool_ref == "resource.read").values(revoked=True)).rowcount
                        return original_recheck(connection, proof)
                    monkeypatch.setattr(store, "recheck_proof_authorities", revoke)
                elif case == "phase_seal_changed":
                    from sim2act.db import delivery_graph_requests
                    calls["callback_rows"] = c.execute(update(delivery_graph_requests).where(
                        delivery_graph_requests.c.app_id == gate.entity(contract),
                        delivery_graph_requests.c.kind == gate.PHASE + "_seal").values(request_fingerprint="0" * 64)).rowcount
                rejected = case in {"authority_revoke", "fixed_source_missing", "fixed_source_deny",
                    "fixed_source_expired", "qualification_deny", "run_cancelled", "phase_seal_changed",
                    "source_callback_controller_drift", "tail_authority_revoke"}
                try:
                    trial.check_commit_after_readback(worker, c, run, out, _tail_authorities=tail_authorities)
                except DomainError as caught:
                    assert rejected
                    error = caught.public()
                else:
                    assert not rejected
                assert "stamp" not in out
                if case != "missing_stamp":
                    assert stamp.consumed
                if case == "continue_once":
                    assert calls["full"] == 1 and calls["source"] == 1 and calls["qualification"] == 1
                    trial.check_commit_after_readback(worker, c, run, {"stamp": stamp})
                    assert calls["full"] == 2
                elif case in {"missing_stamp", "no_scope", "settings_changed", "successful_write", "failed_write", "source_callback_write"}:
                    assert calls["full"] == 2
                elif case in {"fixed_source_missing", "fixed_source_deny", "fixed_source_expired", "qualification_deny", "authority_revoke", "source_callback_controller_drift", "tail_authority_revoke"}:
                    assert calls["full"] == 1  # No retry can replace a current rejection.
                if rejected:
                    assert error is not None
                if case in {"successful_write", "source_callback_write", "authority_revoke", "run_cancelled", "phase_seal_changed", "tail_authority_revoke"}:
                    assert calls["callback_rows"] == 1
    assert not http_calls
    (tmp_path / "boundary-result.json").write_text(json.dumps(dict(case=case, calls=calls,
        error=error, real_models=0, mock_exchanges=0,
        scope="UNIT_INITIAL_PHASE_STUB_NOT_FULL_LINEAGE_ACCEPTANCE"), indent=2)+'\n')
