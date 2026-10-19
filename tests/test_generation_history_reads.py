"""Completed production history reuse; copied structural reads never run a task."""
import copy
import hashlib
import json
import sqlite3
import time
from collections.abc import Mapping
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import OperationalError
from test_pb_spec_production_controller import configured, prepare_pb
from test_spec_production_controller import no_real_http as no_real_http

from sim2act import goal_applications as generation
from sim2act import pb_natural_specs as pb
from sim2act.db import Store, fingerprint, grants, runs
from sim2act.errors import DomainError


def plain(value):
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value.model_dump() if hasattr(value, "model_dump") else value


def check_history_reads(database, run_id, out):
    database, out = Path(database), Path(out)
    out.mkdir(exist_ok=False)
    original_hash = hashlib.sha256(database.read_bytes()).hexdigest()
    original = generation._history
    http_calls, reports = [], []

    def forbidden(*args, **kwargs):
        http_calls.append(True)
        raise AssertionError("Every real and Mock transport is forbidden during structural history reads")

    def clone(name):
        path = out / (name + ".db")
        with sqlite3.connect("file:" + str(database) + "?mode=ro", uri=True) as source, sqlite3.connect(path) as target:
            source.backup(target)
        return Store("sqlite:///" + str(path), test_only=True)

    with pytest.MonkeyPatch.context() as network:
        for transport, methods in ((httpx.HTTPTransport, ("handle_request",)),
                (httpx.AsyncHTTPTransport, ("handle_async_request",)),
                (httpx.MockTransport, ("handle_request", "handle_async_request"))):
            for method in methods:
                network.setattr(transport, method, forbidden)
        baseline = clone("original")
        try:
            with baseline.tx() as c, pb._source_reads(baseline, c):
                job = dict(c.execute(select(runs).where(runs.c.id == run_id)).mappings().one())
                assert job["status"] == "PARTIAL"
                expected = plain(original(baseline, c, job))
        finally:
            baseline.engine.dispose()
        (out / "original.json").write_text(json.dumps(expected, indent=2) + "\n")
        accepted_job = copy.deepcopy(job)
        for case in ("same", "returned_mutation", "write", "failed_write", "new_transaction",
                "grant_revoke", "grant_expire", "run_identity", "first_failure", "no_scope"):
            store = clone(case)
            state = dict(full_calls=0, armed=False, injected=False, mutation_rowcount=None)
            recheck = store.recheck_proof_authorities

            def complete(*args, case=case, state=state, **kwargs):
                state["full_calls"] += 1
                if case == "first_failure" and state["full_calls"] == 1:
                    raise DomainError("VERSION_CONFLICT", "Synthetic first history failure")
                return original(*args, **kwargs)

            def fresh(c, proof, case=case, state=state, job=accepted_job, recheck=recheck):
                if state["armed"] and not state["injected"] and case.startswith("grant_"):
                    state["injected"] = True
                    values = {"revoked": True, "revision": grants.c.revision + 1} if case == "grant_revoke" else {"expires_at": time.time() - 1}
                    changed = c.execute(update(grants).where(grants.c.principal_id == job["runtime_id"],
                        grants.c.project_id == job["project_id"], grants.c.resource_id == job["resource_refs"][0],
                        grants.c.tool_ref == "resource.read").values(**values))
                    state["mutation_rowcount"] = changed.rowcount
                    assert changed.rowcount > 0
                return recheck(c, proof)

            error, first_error, actual = None, None, None
            try:
                with pytest.MonkeyPatch.context() as patch:
                    patch.setattr(generation, "_history", complete)
                    patch.setattr(store, "recheck_proof_authorities", fresh)
                    if case == "no_scope":
                        with store.tx() as c:
                            assert plain(generation.history(store, c, copy.deepcopy(job))) == expected
                            actual = plain(generation.history(store, c, copy.deepcopy(job)))
                    elif case == "new_transaction":
                        for _ in range(2):
                            with store.tx() as c, pb._source_reads(store, c):
                                actual = plain(generation.history(store, c, copy.deepcopy(job)))
                    else:
                        with store.tx() as c, pb._source_reads(store, c):
                            current_job = copy.deepcopy(job)
                            try:
                                first = generation.history(store, c, current_job)
                                assert plain(first) == expected
                            except DomainError as denied:
                                assert case == "first_failure" and denied.code == "VERSION_CONFLICT"
                                first_error = denied.public()
                                assert not any(k[0] == "completed-production-generation-history"
                                    for k in c.info["pb_source_reads"].results)
                            if case == "returned_mutation":
                                first[0][0]["content"] = "Caller changed a returned message"
                                first[1][0]["parameters"]["caller_change"] = True
                            elif case == "write":
                                assert c.execute(update(runs).where(runs.c.id == run_id).values(version=runs.c.version)).rowcount == 1
                            elif case == "failed_write":
                                with pytest.raises(OperationalError):
                                    c.exec_driver_sql("UPDATE synthetic_absent_history_table SET value=1")
                            elif case == "run_identity":
                                current_job["principal_id"] = "user_" + "0" * 32
                                with pytest.raises(DomainError) as oracle:
                                    original(store, c, current_job)
                                assert oracle.value.code == "PERMISSION_DENIED"
                            state["armed"] = True
                            try:
                                with pb._source_reads(store, c):
                                    actual = plain(generation.history(store, c, current_job))
                            except DomainError as denied:
                                assert case in {"grant_revoke", "grant_expire", "run_identity"}
                                assert denied.code == ("PERMISSION_DENIED" if case == "run_identity" else "GRANT_REVOKED")
                                error = denied.public()
                if error is None:
                    assert actual == expected
                    assert state["full_calls"] == (1 if case in {"same", "returned_mutation"} else 2)
                else:
                    assert state["full_calls"] == (2 if case == "run_identity" else 1)
                report = dict(case=case, result="PASS", actual=actual, error=error,
                    first_error=first_error, actual_fingerprint=fingerprint(actual), **state)
                (out / (case + ".json")).write_text(json.dumps(report, indent=2) + "\n")
                reports.append({k: v for k, v in report.items() if k != "actual"})
                print("history " + case + " PASS", flush=True)
            finally:
                store.engine.dispose()
    assert not http_calls and original_hash == hashlib.sha256(database.read_bytes()).hexdigest()
    record = dict(classification="OWNED_STRUCTURAL_COPIES_NO_WORKER_OR_RUN_CONTINUATION", cases=reports,
        original_db_sha256=original_hash, original_db_unchanged=True, real_models=0, new_mock_calls=0,
        original_value_fingerprint=fingerprint(expected))
    (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def test_completed_production_history_read_scope(env, tmp_path, monkeypatch):
    import test_natural_spec_apps as apps
    data, _, fixture, _ = configured(env, tmp_path, monkeypatch, prepare_case=prepare_pb)
    generation_id, _, _, _, generated = apps.ready(data, style="ordered")
    assert len(generated) == len(fixture["sends"]) == 3
    try:
        check_history_reads(data[0].engine.url.database, generation_id, tmp_path / "history-safety")
        assert len(fixture["sends"]) == 3
    finally:
        data[2].close()
