"""Same-call PB binding reuse; structural reads never admit or resume a Run."""
import copy
import hashlib
import json
import sqlite3
from collections.abc import Mapping
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select, update
from test_pb_natural_uses import prepared_use
from test_spec_production_controller import no_real_http as no_real_http

from sim2act import app_jobs
from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_uses as use
from sim2act.contracts import Limits
from sim2act.db import Store, app_drafts, fingerprint, grants, runs
from sim2act.errors import DomainError


def plain(value):
    if isinstance(value, Mapping):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def check_read_reuse(database, run_id, limits, out):
    """Run exact assertions on owned copies; no worker/lease/clock mutation."""
    database, out = Path(database), Path(out)
    out.mkdir(exist_ok=False)
    original_hash = hashlib.sha256(database.read_bytes()).hexdigest()
    original_load, original_bound = app_jobs.load_binding, use.bound
    original_audit, original_base = use.audit, use.base_audit
    http_calls, reports = [], []

    def forbidden(*args, **kwargs):
        http_calls.append(True)
        raise AssertionError("Every real and Mock transport is forbidden during structural checks")

    def clone(name):
        path = out / (name + ".db")
        with sqlite3.connect("file:" + str(database) + "?mode=ro", uri=True) as origin, sqlite3.connect(path) as target:
            origin.backup(target)
        return Store("sqlite:///" + str(path), test_only=True)

    with pytest.MonkeyPatch.context() as network:
        for transport, methods in ((httpx.HTTPTransport, ("handle_request",)),
                (httpx.AsyncHTTPTransport, ("handle_async_request",)),
                (httpx.MockTransport, ("handle_request", "handle_async_request"))):
            for method in methods:
                network.setattr(transport, method, forbidden)
        baseline = clone("complete-baseline")
        try:
            def complete(*args, **kwargs):
                kwargs.pop("_use_out", None)
                return original_load(*args, **kwargs)
            with pytest.MonkeyPatch.context() as patch, baseline.tx() as c:
                patch.setattr(app_jobs, "load_binding", complete)
                job = dict(c.execute(select(runs).where(runs.c.id == run_id)).mappings().one())
                expected = plain(spec.bound(baseline, c, job["principal_id"], job, limits.model_copy(deep=True)))
        finally:
            baseline.engine.dispose()
        accepted_job = copy.deepcopy(job)
        for case in ("same", "missing", "tuple_mutation", "recheck_write", "recheck_revoke", "audit_write", "audit_base_write", "tail_reject", "first_audit_reject"):
            store = clone(case)
            state = dict(loaded=False, injected=False, bound_calls=0, base_calls=0, audits=0)
            actual_recheck = store.recheck_proof_authorities

            def load(*args, case=case, state=state, **kwargs):
                result = original_load(*args, **kwargs)
                proof = kwargs.get("_use_out")
                if args[3]["id"] == run_id and proof and "bound" in proof:
                    assert {"name", "created_at"} <= proof["audit_base"].keys()
                    state["loaded"] = True
                    if case == "missing":
                        proof.clear()
                    elif case == "tuple_mutation":
                        proof["bound"][0]["untrusted_callback_change"] = True
                return result

            def bound(*args, case=case, state=state, **kwargs):
                if args[3]["id"] == run_id:
                    state["bound_calls"] += 1
                result = original_bound(*args, **kwargs)
                if case == "tail_reject" and kwargs.get("_read_out") is not None and args[3]["id"] == run_id:
                    result = copy.deepcopy(result)
                    result[3]["resource_id"] = "res_" + "0" * 32
                    state["injected"] = True
                return result

            def base(*args, state=state, **kwargs):
                state["base_calls"] += 1
                return original_base(*args, **kwargs)

            def audit(*args, case=case, state=state, **kwargs):
                if args[3].get("pb_use_run_id") == run_id:
                    state["audits"] += 1
                    if case == "audit_write":
                        assert args[1].execute(update(runs).where(runs.c.id == run_id)
                            .values(version=runs.c.version)).rowcount == 1
                        state["injected"] = True
                    elif case == "audit_base_write":
                        assert args[1].execute(update(app_drafts).where(app_drafts.c.id == args[3]["id"])
                            .values(name=app_drafts.c.name + " changed")).rowcount == 1
                        state["injected"] = True
                return original_audit(*args, **kwargs)

            def recheck(c, proof, case=case, state=state, job=accepted_job, actual_recheck=actual_recheck):
                if state["loaded"] and not state["injected"] and case.startswith("recheck_"):
                    state["injected"] = True
                    if case == "recheck_write":
                        assert c.execute(update(runs).where(runs.c.id == run_id)
                            .values(version=runs.c.version)).rowcount == 1
                    else:
                        changed = c.execute(update(grants).where(grants.c.principal_id == job["runtime_id"],
                            grants.c.project_id == job["project_id"], grants.c.resource_id == job["resource_refs"][0],
                            grants.c.tool_ref == "resource.read").values(revoked=True, revision=grants.c.revision + 1))
                        assert changed.rowcount > 0
                return actual_recheck(c, proof)

            original_pb_audit = use.pb.audit_fingerprint
            def pb_audit(*args, case=case, state=state, original_pb_audit=original_pb_audit, **kwargs):
                output = kwargs.get("_audit_out")
                if case != "first_audit_reject" or output is None:
                    return original_pb_audit(*args, **kwargs)
                def reject(*args, **kwargs):
                    raise DomainError("VERSION_CONFLICT", "Synthetic first audit failure")
                with pytest.MonkeyPatch.context() as failure:
                    failure.setattr(use.pb, "source_audit", reject)
                    try:
                        return original_pb_audit(*args, **kwargs)
                    finally:
                        assert output == {}, "Incomplete first audit was published"
                        state["injected"] = True

            try:
                with pytest.MonkeyPatch.context() as patch:
                    patch.setattr(app_jobs, "load_binding", load)
                    patch.setattr(use, "bound", bound)
                    patch.setattr(use, "base_audit", base)
                    patch.setattr(use, "audit", audit)
                    patch.setattr(use.pb, "audit_fingerprint", pb_audit)
                    patch.setattr(store, "recheck_proof_authorities", recheck)
                    try:
                        with store.tx() as c:
                            job = dict(c.execute(select(runs).where(runs.c.id == run_id)).mappings().one())
                            actual = plain(spec.bound(store, c, job["principal_id"], job, limits.model_copy(deep=True)))
                        assert case not in {"recheck_revoke", "tail_reject", "first_audit_reject"}, "Rejected path returned a binding"
                        if case == "audit_base_write":
                            assert actual["audit_fingerprint"] != expected["audit_fingerprint"]
                            assert {k: v for k, v in actual.items() if k != "audit_fingerprint"} == {
                                k: v for k, v in expected.items() if k != "audit_fingerprint"}
                        else:
                            assert actual == expected
                        assert state["bound_calls"] == (2 if case in {"missing", "tuple_mutation", "recheck_write"} else 1)
                        assert state["base_calls"] == (1 if case == "same" else 2 if case in {"audit_write", "audit_base_write"} else 3)
                        error = None
                    except DomainError as denied:
                        assert case in {"recheck_revoke", "tail_reject", "first_audit_reject"}
                        assert denied.code == ("GRANT_REVOKED" if case == "recheck_revoke" else "VERSION_CONFLICT")
                        assert state["bound_calls"] == 1 and state["base_calls"] == 1 and state["audits"] == 0
                        error = denied.public()
                    reports.append(dict(case=case, result="PASS", error=error, **state))
                    print("same-call " + case + " PASS", flush=True)
            finally:
                store.engine.dispose()
    result = dict(classification="SAME_CALL_STRUCTURAL_ASSERTIONS_NO_RUN_EXECUTION", run_id=run_id,
        real_models=0, new_mock_calls=0, http_calls=len(http_calls), reports=reports,
        original_db_sha256=original_hash,
        original_db_unchanged=hashlib.sha256(database.read_bytes()).hexdigest() == original_hash,
        baseline_fingerprint=fingerprint(expected), run_not_resumed=True)
    assert not http_calls and result["original_db_unchanged"] and len(reports) == 9
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def test_same_call_pb_binding_and_audit_read_boundaries(env, tmp_path):
    if not env[0].sqlite:
        pytest.skip("Same-call proof reuse is test-only SQLite")
    data, _, _, _, _, _, body, route = prepared_use(env)
    checked = data[2].post(route + "/pb-use-reviews", json=body)
    assert checked.status_code == 200, checked.text
    queued = data[2].post(route + "/pb-use-runs", json=dict(review=body,
        expected_review_fingerprint=checked.json()["review_fingerprint"], consent=use.CONSENT))
    assert queued.status_code == 202, queued.text
    check_read_reuse(data[0].engine.url.database, queued.json()["run_id"],
        Limits(**{key: getattr(data[1], key) for key in Limits.model_fields}), tmp_path / "read-boundaries")
