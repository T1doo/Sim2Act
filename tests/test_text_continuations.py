"""Exact old SQLite fixture -> explicit compatible software -> cold actual Worker.

Fixtures were created by accepted Git software, never by rewriting current seals.
The documented explicit schema initializer adds empty current tables to a copy;
all original tables, columns and rows must remain unchanged before API startup.
Time is fixed inside their original TTL for reproducible synthetic offline proof.
"""

import copy
import gzip
import hashlib
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import MetaData, delete, event, select, update
from test_persistent_app_runs import NoModel

from sim2act import text_continuations as cont
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.contracts import Limits
from sim2act.db import (
    Store,
    fingerprint,
    goal_cards,
    grants,
    internal_app_runs,
    internal_approvals,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    meta,
    new_id,
    operations,
    runs,
)
from sim2act.errors import DomainError
from sim2act.worker import Worker

FIXTURES = Path(__file__).parent / "fixtures/text-legacy"


@pytest.fixture(params=["233", "a747"])
def legacy(request, tmp_path, monkeypatch):
    yield from open_legacy(request.param, tmp_path, monkeypatch)


@pytest.fixture(params=["233-failed", "a747-failed"])
def legacy_failure(request, tmp_path, monkeypatch):
    yield from open_legacy(request.param, tmp_path, monkeypatch)


def open_legacy(name, tmp_path, monkeypatch):
    info = json.loads((FIXTURES / (name + "-info.json")).read_text())
    raw = gzip.decompress((FIXTURES / (name + ".db.gz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == info["database_sha256"]
    database = tmp_path / "old.db"
    database.write_bytes(raw)
    monkeypatch.setattr(time, "time", lambda: info["fixture_time"])
    settings = Settings("sqlite:///" + str(database), tmp_path, mode="mock", live_enabled=False)
    store = Store(settings.database_url, test_only=True)
    original = rows(store)
    with store.engine.connect() as c:
        original_schema = c.exec_driver_sql("SELECT type, name, tbl_name, sql FROM sqlite_master").all()
    store.initialize()  # Explicit fixture upgrade, never an implicit API migration.
    upgraded = rows(store)
    assert all(upgraded[name] == values for name, values in original.items())
    assert all(not values for name, values in upgraded.items() if name not in original)
    with store.engine.connect() as c:
        upgraded_schema = c.exec_driver_sql("SELECT type, name, tbl_name, sql FROM sqlite_master").all()
    assert all(value in upgraded_schema for value in original_schema)
    added_tables = upgraded.keys() - original.keys()
    assert added_tables <= meta.tables.keys()
    assert all(value.type in {"table", "index"} and value.tbl_name in added_tables
               for value in upgraded_schema if value not in original_schema)
    with TestClient(create_app(store, settings)) as client:
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        yield store, settings, client, info
    store.engine.dispose()


def rows(store):
    with store.tx() as c:
        # Preserve every actual historical table/column, including unknown ones;
        # querying today's metadata invents tables that the original DB never had.
        historical = MetaData()
        historical.reflect(bind=c)
        return {t.name: [dict(r) for r in c.execute(select(t)).mappings()]
                for t in historical.sorted_tables}


def path(info):
    return "/api/internal/instances/" + info["instance"]["id"] + "/software-continuations"


def prepared(data):
    _, _, client, info = data
    options = client.get("/api/projects/" + info["project"] + "/software-continuation-options")
    assert options.status_code == 200, options.text
    chosen = next(x for x in options.json()["items"] if x["id"] == info["instance"]["id"])
    body = dict(expected_revision=chosen["revision"], expected_release_fingerprint=chosen["release_fingerprint"],
        expected_candidate_fingerprint=chosen["fingerprint"], expected_source_implementation=chosen["source_implementation"],
        input={"term": "Alpha"}, request_key="explicit-preflight")
    reply = client.post(path(info).replace("software-continuations", "software-continuation-preflights"), json=body)
    assert reply.status_code == 201, reply.text
    approval = reply.json()
    commit = dict(approval_id=approval["approval_id"], expected_approval_fingerprint=approval["approval_fingerprint"],
        consent="CONTINUE_ONLY_THIS_EXACT_EXISTING_INSTANCE_WITH_THIS_SOFTWARE", request_key="exact-commit")
    return approval, body, commit


def continued(data):
    _, _, client, info = data
    approval, body, commit = prepared(data)
    reply = client.post(path(info), json=commit)
    assert reply.status_code == 201, reply.text
    return approval, body, commit, reply.json()


def queue(data, receipt, key="new-cold-input"):
    _, _, client, info = data
    own = client.get("/api/internal/apps/" + info["app"]["id"] + "/owner-goals")
    assert own.status_code == 200, own.text
    goal = own.json().get("current")
    body = dict(expected_revision=receipt["revision"], expected_release_fingerprint=receipt["release_fingerprint"],
        input={"term": "final"}, request_key=key)
    if goal:
        body["expected_owner_goal_binding_fingerprint"] = goal["binding_fingerprint"]
    reply = client.post("/api/internal/instances/" + info["instance"]["id"] + "/runs", json=body)
    assert reply.status_code == 202, reply.text
    return reply.json()["run_id"]


def unchanged_old(before, after, info):
    iid = info["instance"]["id"]
    for name, values in before.items():
        for value in values:
            if name == "internal_instances" and value["id"] == iid:
                continue
            assert value in after[name], (name, value.get("id"))
    old = next(v for v in before["internal_instances"] if v["id"] == iid)
    new = next(v for v in after["internal_instances"] if v["id"] == iid)
    assert new["data_version"] == old["data_version"] and new["history"][:-1] == old["history"]
    for key in old.keys() - {"release_id", "revision", "history"}:
        assert new[key] == old[key]


def test_exact_old_db_cold_current_continuation_preserves_and_new_worker(legacy):
    store, settings, client, info = legacy
    before = rows(store)
    assert client.get("/api/apps/" + info["app"]["id"]).status_code == 409
    assert rows(store) == before
    _, _, body, receipt = continued(legacy)
    after = rows(store)
    unchanged_old(before, after, info)
    assert receipt["revision"] == 2 and receipt["data_version_at_commit"] == 1 and receipt["current_permission"]
    assert client.post(path(info), json=body).json() == receipt and rows(store) == after
    result = client.get("/api/internal/instances/" + info["instance"]["id"])
    assert result.status_code == 200 and result.json()["data_version"] == 1, result.text
    old_run = client.get("/api/internal/instances/" + info["instance"]["id"] + "/runs/" + info["successful_old_run_id"])
    assert old_run.status_code == 200 and old_run.json()["status"] == "SUCCEEDED", old_run.text
    rid = queue(legacy, receipt)
    cold = Store(settings.database_url, test_only=True)
    try:
        assert Worker(cold, settings, NoModel()).once()
        with TestClient(create_app(cold, settings)) as reader:
            reader.headers["Authorization"] = "Bearer synthetic-test-A"
            actual = reader.get("/api/internal/instances/" + info["instance"]["id"] + "/runs/" + rid)
            assert actual.status_code == 200, actual.text
            actual = actual.json()
            assert actual["status"] == "SUCCEEDED" and actual["result_version"] == 2, actual
            assert actual["result"]["citations"] == [{"start_line": 4, "end_line": 4, "quote": "Gamma final note"}]
            state = reader.get("/api/internal/instances/" + info["instance"]["id"] + "/owner-review").json()
            assert state["owner_acceptance"] != "ACCEPTED"
            if info.get("old_signature"):
                assert state["owner_acceptance"] == "STALE" and state["history"]
            restored = reader.get(path(info), params={"request_key": "exact-commit"})
            assert restored.status_code == 200 and restored.json()["current_permission"]
    finally:
        cold.engine.dispose()


def test_other_instance_generic_execution_never_inherits_permission(legacy):
    store, _, client, info = legacy
    *_, receipt = continued(legacy)
    before = rows(store)
    other = info["other_instance"]["id"]
    reply = client.post("/api/internal/instances/" + other + "/runs", json=dict(expected_revision=1,
        expected_release_fingerprint=info["release"]["fingerprint"], input={"term": "Gamma"}, request_key="not-approved"))
    assert reply.status_code == 409
    assert client.post("/api/internal/releases/" + receipt["release_id"] + "/instances", json=dict(
        expected_release_fingerprint=receipt["release_fingerprint"], request_key="never-new")).json()["error"]["code"] == "UNSUPPORTED_CAPABILITY"
    assert client.post("/api/internal/apps/" + info["app"]["id"] + "/release-approvals", json=dict(
        expected_draft_fingerprint=info["app"]["candidate_fingerprint"], sample_input={"term": "Alpha"})).json()["error"]["code"] == "UNSUPPORTED_CAPABILITY"
    assert rows(store) == before


@pytest.mark.parametrize("mutation", ["revision", "data", "history", "grant", "goal", "expiry", "limits", "software", "consent"])
def test_exact_commit_cas_denies_without_partial_rows(legacy, monkeypatch, mutation):
    store, settings, client, info = legacy
    approval, _, body = prepared(legacy)
    iid = info["instance"]["id"]
    with store.tx() as c:
        if mutation == "revision":
            c.execute(update(internal_instances).where(internal_instances.c.id == iid).values(revision=3))
        elif mutation == "data":
            c.execute(update(internal_instances).where(internal_instances.c.id == iid).values(data_version=2))
        elif mutation == "history":
            row = c.execute(select(internal_instances).where(internal_instances.c.id == iid)).mappings().one()
            c.execute(update(internal_instances).where(internal_instances.c.id == iid).values(history=[{**row["history"][0], "unexpected": True}]))
        elif mutation == "grant":
            c.execute(update(grants).where(grants.c.principal_id == info["owner"], grants.c.resource_id == info["resource"]).values(revoked=True))
        elif mutation == "goal":
            if info.get("goal"):
                c.execute(update(goal_cards).where(goal_cards.c.id == info["goal"]["card_id"]).values(title="competing editor"))
            else:
                # Target application criteria are not the independent app's goals.
                monkeypatch.setattr(cont, "preconditions", lambda *args: {**approval["preflight"], "goal_fingerprint": "0"*64})
        elif mutation == "expiry":
            monkeypatch.setattr(time, "time", lambda: approval["expires_at"] + 1)
        elif mutation == "software":
            monkeypatch.setattr(cont, "implementation", lambda: "0"*64)
        elif mutation == "consent":
            body["consent"] = "AUTO_ACCEPT"
    before = rows(store)
    if mutation == "limits":
        limits = Limits(**{k: getattr(settings, k) for k in Limits.model_fields})
        limits = limits.model_copy(update={"run_seconds": limits.run_seconds-1})
        with pytest.raises(DomainError):
            cont.commit(store, info["owner"], iid, cont.CommitInput.model_validate(body), limits)
    else:
        assert client.post(path(info), json=body).status_code in {403, 409, 422}
    assert rows(store) == before


@pytest.mark.parametrize("mutation", ["run-status", "no-binding", "receipt", "queued", "unknown"])
def test_full_preserved_worker_proof_is_required_before_preflight(legacy, monkeypatch, mutation):
    store, _, client, info = legacy
    with store.tx() as c:
        rid = info["successful_old_run_id"]
        if mutation == "run-status":
            c.execute(update(runs).where(runs.c.id == rid).values(status="FAILED"))
        elif mutation == "no-binding":
            c.execute(delete(internal_run_bindings).where(internal_run_bindings.c.run_id == rid))
        elif mutation == "receipt":
            c.execute(update(operations).where(operations.c.run_id == rid).values(receipt={}))
        elif mutation == "queued":
            c.execute(update(runs).where(runs.c.id == rid).values(status="QUEUED"))
        else:
            monkeypatch.setattr(store, "has_unknown", lambda *_: True)
    before = rows(store)
    options = client.get("/api/projects/" + info["project"] + "/software-continuation-options").json()
    item = next(x for x in options["items"] if x["id"] == info["instance"]["id"])
    reply = client.post(path(info).replace("software-continuations", "software-continuation-preflights"), json=dict(
        expected_revision=item["revision"], expected_release_fingerprint=item["release_fingerprint"],
        expected_candidate_fingerprint=item["fingerprint"], expected_source_implementation=item["source_implementation"],
        input={"term": "Alpha"}, request_key="bad-old-history"))
    assert reply.status_code in {400, 409} and reply.json()["error"]["code"] in {"VERSION_CONFLICT", "OUTCOME_UNKNOWN"}, reply.text
    assert rows(store) == before


def test_atomic_insertion_failure_and_expiry_after_write_roll_back(legacy, monkeypatch):
    store, _, _, info = legacy
    approval, _, body = prepared(legacy)
    before = rows(store)
    original = cont.logic.record_release_index
    def fail(*_):
        raise DomainError("VERSION_CONFLICT", "synthetic index write failure")
    monkeypatch.setattr(cont.logic, "record_release_index", fail)
    limits = Limits(**{k: getattr(legacy[1], k) for k in Limits.model_fields})
    with pytest.raises(DomainError):
        cont.commit(store, info["owner"], info["instance"]["id"], cont.CommitInput.model_validate(body), limits)
    assert rows(store) == before
    def expire(*args):
        original(*args)
        monkeypatch.setattr(time, "time", lambda: approval["expires_at"] + 1)
    monkeypatch.setattr(cont.logic, "record_release_index", expire)
    with pytest.raises(DomainError):
        cont.commit(store, info["owner"], info["instance"]["id"], cont.CommitInput.model_validate(body), limits)
    assert rows(store) == before


def test_cancel_preflight_revoke_permission_and_original_key_history(legacy):
    store, _, client, info = legacy
    _, request, body = prepared(legacy)
    stop_path = path(info).replace("software-continuations", "software-continuation-stops")
    cancelled = client.post(stop_path, json=dict(command="CANCEL", target_key=request["request_key"], reason="explicit stop", request_key="cancelled-preflight"))
    assert cancelled.status_code == 201 and cancelled.json()["stopped"]
    before = rows(store)
    assert client.post(path(info), json=body).status_code == 409
    recovery = client.get(path(info), params={"request_key": request["request_key"]})
    assert recovery.status_code == 200 and recovery.json()["kind"] == "STOPPED"
    request["request_key"] = "second-explicit-preflight"
    reply = client.post(path(info).replace("software-continuations", "software-continuation-preflights"), json=request)
    assert reply.status_code == 201, reply.text
    body.update(approval_id=reply.json()["approval_id"], expected_approval_fingerprint=reply.json()["approval_fingerprint"])
    made = client.post(path(info), json=body)
    assert made.status_code == 201, made.text
    value = made.json()
    revoked = client.post(stop_path, json=dict(command="REVOKE", target_key="exact-commit",
        expected_record_fingerprint=value["record_fingerprint"], reason="explicit execution withdrawal", request_key="revoked-permission"))
    assert revoked.status_code == 201 and revoked.json()["stopped"]
    before = rows(store)
    history = client.get(path(info), params={"request_key": "exact-commit"})
    assert history.status_code == 200 and not history.json()["current_permission"]
    assert client.get("/api/internal/instances/" + info["instance"]["id"]).status_code == 200
    assert client.post("/api/internal/instances/" + info["instance"]["id"] + "/runs", json=dict(
        expected_revision=2, expected_release_fingerprint=value["release_fingerprint"], input={"term": "final"}, request_key="revoked-new")).status_code == 409
    assert rows(store) == before


def test_private_preflight_receipt_is_not_read_after_target_revocation(legacy):
    store, _, client, info = legacy
    _, request, body = prepared(legacy)
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.principal_id == info["owner"], grants.c.resource_id == info["resource"]).values(revoked=True))
    statements = []
    def record(_c, _cursor, sql, _parameters, _context, _many):
        statements.append((sql, _parameters))
    event.listen(store.engine, "before_cursor_execute", record)
    before = rows(store)
    try:
        for method, url, payload in [("POST", path(info).replace("software-continuations", "software-continuation-preflights"), request),
            ("POST", path(info), body), ("GET", path(info)+"?request_key=explicit-preflight", None)]:
            statements.clear()
            reply = client.request(method, url, json=payload)
            assert reply.status_code == 403, reply.text
            assert not any("internal_approvals.payload" in sql or ("delivery_graph_requests.snapshot" in sql
                and any(k in parameters for k in [cont.PREPARE, cont.PREPARE+"_seal", cont.COMMIT, cont.COMMIT+"_seal"]))
                for sql, parameters in statements), statements
    finally:
        event.remove(store.engine, "before_cursor_execute", record)
    assert rows(store) == before


def test_no_marker_or_forged_software_receipt_cannot_revive_execution(legacy):
    store, _, client, info = legacy
    *_, receipt = continued(legacy)
    with store.tx() as c:
        r = c.execute(select(internal_releases).where(internal_releases.c.id == receipt["release_id"])).mappings().one()
        snap = copy.deepcopy(r["snapshot"])
        snap.pop("software_continuation")
        fp = fingerprint(snap)
        c.execute(update(internal_releases).where(internal_releases.c.id == r["id"]).values(snapshot=snap, fingerprint=fp))
        a = c.execute(select(internal_approvals).where(internal_approvals.c.id == r["approval_id"])).mappings().one()
        payload = {**a["payload"], "snapshot": snap}
        c.execute(update(internal_approvals).where(internal_approvals.c.id == a["id"]).values(payload=payload, fingerprint=fingerprint(payload)))
    before = rows(store)
    reply = client.post("/api/internal/instances/" + info["instance"]["id"] + "/runs", json=dict(
        expected_revision=2, expected_release_fingerprint=fp, input={"term": "final"}, request_key="stripped-marker"))
    assert reply.status_code == 409 and rows(store) == before


def test_revocation_after_actual_calculation_never_appends_late_result(legacy, monkeypatch):
    from sim2act import app_jobs
    store, settings, client, info = legacy
    *_, receipt = continued(legacy)
    rid = queue(legacy, receipt)
    original = app_jobs.commit_result
    def withdraw(worker, run, plan, output):
        stop = client.post(path(info).replace("software-continuations", "software-continuation-stops"), json=dict(
            command="REVOKE", target_key="exact-commit", expected_record_fingerprint=receipt["record_fingerprint"],
            reason="withdraw before result commit", request_key="late-revoke"))
        assert stop.status_code == 201, stop.text
        return original(worker, run, plan, output)
    monkeypatch.setattr(app_jobs, "commit_result", withdraw)
    assert Worker(store, settings, NoModel()).once()
    with store.tx() as c:
        assert c.execute(select(internal_instances.c.data_version).where(internal_instances.c.id == info["instance"]["id"])).scalar_one() == 1
        assert c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one() == "FAILED"


def test_new_commit_final_response_cannot_swallow_late_expiry(legacy, monkeypatch):
    store, settings, _, info = legacy
    approval, _, body = prepared(legacy)
    before = rows(store)
    public = cont.public_commit
    def expire(*args):
        result = public(*args)
        monkeypatch.setattr(time, "time", lambda: approval["expires_at"]+1)
        return result
    monkeypatch.setattr(cont, "public_commit", expire)
    limits = Limits(**{k: getattr(settings, k) for k in Limits.model_fields})
    with pytest.raises(DomainError):
        cont.commit(store, info["owner"], info["instance"]["id"], cont.CommitInput.model_validate(body), limits)
    assert rows(store) == before


def test_current_cold_private_bodies_denied_before_revoked_target_read(legacy):
    store, _, client, info = legacy
    *_, receipt = continued(legacy)
    with store.tx() as c:
        approval_id = c.execute(select(internal_releases.c.approval_id).where(internal_releases.c.id == receipt["release_id"])).scalar_one()
        c.execute(update(grants).where(grants.c.principal_id == info["app"]["runtime_id"]).values(revoked=True))
    before = rows(store)
    captured = []
    def record(_c, _cursor, sql, parameters, _context, _many):
        captured.append((sql, parameters))
    event.listen(store.engine, "before_cursor_execute", record)
    try:
        for url in ["/api/apps/"+info["app"]["id"], "/api/internal/releases/"+receipt["release_id"],
            "/api/internal/apps/"+info["app"]["id"]+"/releases",
            "/api/internal/approvals/"+approval_id, "/api/internal/instances/"+info["instance"]["id"],
            "/api/internal/instances/"+info["instance"]["id"]+"/runs/"+info["successful_old_run_id"]]:
            captured.clear()
            reply = client.get(url)
            assert reply.status_code == 403, (url, reply.text)
            assert not any(sql.startswith("SELECT app_drafts.candidate ") or sql.startswith("SELECT internal_approvals.id,") or sql.startswith("SELECT internal_releases.id,")
                or sql.startswith("SELECT app_drafts.id,") or sql.startswith("SELECT runs.id,")
                or sql.startswith("SELECT internal_run_bindings.run_id,") for sql, _ in captured), (url, captured)
    finally:
        event.remove(store.engine, "before_cursor_execute", record)
    assert rows(store) == before


def test_cancel_after_commit_is_durable_truthful_metadata_receipt(legacy):
    store, _, client, info = legacy
    _, request, _, receipt = continued(legacy)
    url = path(info).replace("software-continuations", "software-continuation-stops")
    body = dict(command="CANCEL", target_key=request["request_key"], reason="too late preflight cancel", request_key="late-cancel-intent")
    reply = client.post(url, json=body)
    assert reply.status_code == 201 and not reply.json()["stopped"] and reply.json()["already_committed"]
    after = rows(store)
    assert client.post(url, json=body).json() == reply.json() and rows(store) == after
    restored = client.get(path(info), params={"request_key": body["request_key"]})
    assert restored.json()["kind"] == "STOP_RECEIPT" and restored.json()["commit_key"] == "exact-commit"
    assert client.get(path(info), params={"request_key": "exact-commit"}).json()["current_permission"]
    assert receipt["revision"] == 2


def test_original_keys_never_alias_other_intents_and_cancel_is_repeatable(legacy):
    store, _, client, info = legacy
    _, request, body = prepared(legacy)
    before = rows(store)
    assert client.post(path(info), json={**body, "request_key": request["request_key"]}).status_code == 409
    assert rows(store) == before
    stop_url = path(info).replace("software-continuations", "software-continuation-stops")
    cancel = dict(command="CANCEL", target_key=request["request_key"], reason="first cancellation", request_key="first-stop")
    assert client.post(stop_url, json=cancel).status_code == 201
    assert client.post(stop_url, json={**cancel, "reason": "second explicit cancellation", "request_key": "second-stop"}).status_code == 201
    after = rows(store)
    assert client.get(path(info), params={"request_key": "first-stop"}).json()["stopped"]
    assert client.get(path(info), params={"request_key": "second-stop"}).json()["stopped"]
    assert client.post(path(info), json=body).status_code == 409
    assert rows(store) == after


def test_metadata_stop_after_revocation_cold_scope_needs_no_private_body(legacy):
    store, _, client, info = legacy
    continued(legacy)
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.principal_id == info["app"]["runtime_id"]).values(revoked=True))
    options = client.get("/api/projects/" + info["project"] + "/software-continuation-options")
    assert options.status_code == 200, options.text
    selected = next(x for x in options.json()["items"] if x["id"] == info["instance"]["id"])
    assert not selected["requires_explicit_preflight"]
    metadata = selected["permission_stop_metadata"]
    assert metadata["commit_key"] == "exact-commit"
    stopped = client.post(path(info).replace("software-continuations", "software-continuation-stops"), json=dict(
        command="REVOKE", target_key=metadata["commit_key"], expected_record_fingerprint=metadata["record_fingerprint"],
        reason="cold metadata stop without target content", request_key="cold-stop-key"))
    assert stopped.status_code == 201 and stopped.json()["stopped"]
    before = rows(store)
    restored = client.get(path(info), params={"request_key": "cold-stop-key"})
    assert restored.status_code == 200 and restored.json()["kind"] == "STOPPED" and rows(store) == before


def test_actual_approved_failed_worker_history_is_preserved_and_cold_readable(legacy_failure):
    test_exact_old_db_cold_current_continuation_preserves_and_new_worker(legacy_failure)
    _, _, client, info = legacy_failure
    failed = client.get("/api/internal/instances/"+info["instance"]["id"]+"/runs/"+info["failed_old_run_id"])
    assert failed.status_code == 200, failed.text
    assert failed.json()["status"] == "FAILED" and failed.json()["result_version"] is None
    assert failed.json()["error"]["code"] == "INVALID_INPUT"


def test_corrupted_failed_queue_history_cannot_pass_preflight(legacy):
    """Negative persisted fault only; this added job is not a valid old Worker."""
    store, _, client, info = legacy
    with store.tx() as c:
        old = dict(c.execute(select(runs).where(runs.c.id == info["successful_old_run_id"])).mappings().one())
        binding = dict(c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == old["id"])).mappings().one())
        actual = dict(c.execute(select(internal_app_runs).where(internal_app_runs.c.id == binding["app_run_id"])).mappings().one())
        rid, aid = new_id("run"), new_id("iapprun")
        old.update(id=rid, request_key="CORRUPTED-negative-terminal", status="FAILED", result=None, error={"code":"CORRUPTED_TEST_FAULT"})
        actual.update(id=aid, request_key="CORRUPTED-negative-terminal", status="FAILED", output=None, result_version=None, error={"code":"CORRUPTED_TEST_FAULT"})
        snapshot = {**binding["snapshot"], "run_id": rid, "app_run_id": aid}
        c.execute(runs.insert().values(**old))
        c.execute(internal_app_runs.insert().values(**actual))
        c.execute(internal_run_bindings.insert().values(**{**binding, "run_id": rid, "app_run_id": aid, "snapshot":snapshot,"fingerprint":"0"*64}))
    before = rows(store)
    chosen = next(x for x in client.get("/api/projects/"+info["project"]+"/software-continuation-options").json()["items"] if x["id"] == info["instance"]["id"])
    reply = client.post(path(info).replace("software-continuations", "software-continuation-preflights"), json=dict(
        expected_revision=chosen["revision"], expected_release_fingerprint=chosen["release_fingerprint"],
        expected_candidate_fingerprint=chosen["fingerprint"], expected_source_implementation=chosen["source_implementation"],
        input={"term":"Alpha"}, request_key="reject-corrupt-terminal"))
    assert reply.status_code == 409 and rows(store) == before, reply.text


def test_terminal_history_change_after_exact_preflight_rejects_commit(legacy):
    store, _, client, info = legacy
    _, _, body = prepared(legacy)
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == info["successful_old_run_id"]).values(version=99))
    before = rows(store)
    assert client.post(path(info), json=body).status_code == 409
    assert rows(store) == before
