"""Independent manually frozen synthetic spec; no product parser builds expected gold."""

import copy
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.exc import ProgrammingError

from sim2act.api import create_app
from sim2act.db import (
    Store,
    fingerprint,
    grants,
    projects,
    resources,
    spec_checklist_tasks,
)
from sim2act.errors import DomainError
from sim2act.spec_checklists import CHECK, complete_checklist, source_checklist, verify_candidate
from sim2act.tools import TOOLS

ROOT = Path(__file__).resolve().parents[1] / "docs/evidence/noncsv-offline-implementation-20261006"
FIXTURE = (ROOT / "independent-fixture.md").read_text()
GOLD = json.loads((ROOT / "independent-gold.json").read_text())


def candidate(rid):
    return {
        "check_version": CHECK,
        "source": {
            "resource_id": rid,
            "hash": GOLD["source"]["sha256"],
            "document_id": GOLD["document_id"],
            "document_version": GOLD["document_version"],
            "coordinate_space": "whole_resource",
            "line_start": 1,
            "line_end": 6,
        },
        "rules": copy.deepcopy(GOLD["rules"]),
    }


def setup(env, key="spec"):
    client, pid = env[2], env[-2]
    r = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "synthetic.md", "format": "md", "content": FIXTURE},
    )
    assert r.status_code == 201
    rid = r.json()["id"]
    return {
        "resource_id": rid,
        "expected_source_hash": GOLD["source"]["sha256"],
        "candidate_json": json.dumps(candidate(rid)),
        "request_key": key,
        "synthetic_fixture": True,
    }


def post(env, body):
    return env[2].post(f"/api/projects/{env[-2]}/spec-checklist-tasks", json=body)


def count(store, table):
    with store.engine.connect() as c:
        return c.execute(select(func.count()).select_from(table)).scalar_one()


def test_independent_gold_current_bytes_and_cold_readback(env):
    assert hashlib.sha256(FIXTURE.encode()).hexdigest() == GOLD["source"]["sha256"]
    assert len(FIXTURE.encode()) == 278
    body = setup(env)
    store = env[0]
    before = count(store, resources)
    with store.tx() as c:
        previous_grants = [dict(x) for x in c.execute(select(grants)).mappings()]
    response = post(env, body)
    assert response.status_code == 201, response.text
    task = response.json()
    assert task["status"] == "SUCCEEDED" and task["semantic_goal_acceptance"] == "NOT_RUN"
    assert task["proof"]["kind"] == "verified_synthetic_labeled_citations"
    assert task["model_requests"] == 0 and not task["publishable"]
    assert task["receipt"]["tool_ref"] == "artifact.save_text"
    output = env[2].get("/api/resources/" + task["output"]["resource_id"]).json()
    assert json.loads(output["content"]) == candidate(body["resource_id"])
    assert task["output"]["hash"] == hashlib.sha256(output["content"].encode()).hexdigest()
    assert count(store, resources) == before + 1
    with store.tx() as c:
        now = [dict(x) for x in c.execute(select(grants)).mappings()]
        assert all(x in now for x in previous_grants)
        added = [x for x in now if x not in previous_grants]
        assert len(added) == 2 and all(
            x["tool_ref"] == "resource.read" and x["resource_id"] == output["id"] for x in added
        )
    cold = Store(env[1].database_url, test_only=True)
    if not store.sqlite:
        cold.engine = cold.engine.execution_options(**store.engine.get_execution_options())
    with TestClient(create_app(cold, env[1])) as client:
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        r = client.get("/api/spec-checklist-tasks/" + task["id"])
        assert r.status_code == 200 and r.json()["proof"] == task["proof"]
        assert "自然语言语义验收 NOT_RUN" in r.json()["markdown_view"]
    cold.engine.dispose()
    assert set(TOOLS) == {"resource.read", "data.aggregate_csv", "artifact.save_text"}


@pytest.mark.parametrize(
    "fault",
    [
        "quote",
        "line",
        "version",
        "hash",
        "resource",
        "missing",
        "duplicate",
        "order",
        "extra_gold",
        "bool_version",
        "duplicate_json",
        "unknown_field",
    ],
)
def test_bad_candidate_persists_failure_without_artifact_or_grants(env, fault):
    body = setup(env)
    v = json.loads(body["candidate_json"])
    if fault == "quote":
        v["rules"][0]["quote"] = "Invented quoted rule"
    elif fault == "line":
        v["rules"][0]["line_start"] = 4
    elif fault == "version":
        v["source"]["document_version"] = 3
    elif fault == "hash":
        v["source"]["hash"] = "0" * 64
    elif fault == "resource":
        v["source"]["resource_id"] = "res_" + "0" * 32
    elif fault == "missing":
        v["rules"].pop()
    elif fault == "duplicate":
        v["rules"][1] = copy.deepcopy(v["rules"][0])
    elif fault == "order":
        v["rules"].reverse()
    elif fault == "extra_gold":
        v["gold"] = v["rules"]
    elif fault == "bool_version":
        v["source"]["document_version"] = True
    elif fault == "unknown_field":
        v["rules"][0]["allow_production_write"] = True
    body["candidate_json"] = json.dumps(v)
    if fault == "duplicate_json":
        body["candidate_json"] = '{"check_version":"x","check_version":"y"}'
    before = [count(env[0], t) for t in [resources, grants]]
    result = post(env, body)
    assert result.status_code == 201 and result.json()["status"] == "FAILED"
    assert result.json()["output"] is None and result.json()["proof"] is None
    assert [count(env[0], t) for t in [resources, grants]] == before
    assert post(env, body).json()["id"] == result.json()["id"]


@pytest.mark.parametrize(
    "content",
    [
        FIXTURE + "unlabeled hidden requirement\n",
        FIXTURE.replace("MUST ", "MAY ", 1),
        FIXTURE + FIXTURE.splitlines()[2] + "\n",
        FIXTURE.replace("\n", "\r\n"),
        FIXTURE.replace("Keep prior", "<script>Keep prior"),
        FIXTURE.replace("Keep prior", "https://bad.invalid Keep prior"),
        "# Spec real_material v1\n- [r] MUST x\n",
        "# Spec synthetic_x v1\n",
        FIXTURE + "\n" * 41,
        FIXTURE + "x" * 4096,
    ],
)
def test_unsupported_source_rejected_without_output(content, env):
    source = {
        "resource_id": "res_" + "a" * 32,
        "format": "md",
        "content": content,
        "hash": hashlib.sha256(content.encode()).hexdigest(),
    }
    with pytest.raises(DomainError):
        source_checklist(source)


def test_golden_mutation_cannot_replace_actual_source(env):
    body = setup(env)
    source = {
        "resource_id": body["resource_id"],
        "format": "md",
        "content": FIXTURE,
        "hash": body["expected_source_hash"],
    }
    v = candidate(body["resource_id"])
    v["rules"][0]["quote"] = "A fake gold and candidate agree"
    with pytest.raises(DomainError):
        verify_candidate(source, json.dumps(v))
    # Byte hashes retain terminal newline; no strip/normalization used.
    source["content"] = FIXTURE.rstrip("\n")
    with pytest.raises(DomainError):
        source_checklist(source)


@pytest.mark.parametrize(
    "tool,who,expired",
    [
        (tool, who, expired)
        for tool in ["resource.read", "artifact.save_text"]
        for who in ["owner", "runtime"]
        for expired in [False, True]
    ],
)
def test_revoked_expired_intersection_blocks_write_and_replay(env, tool, who, expired):
    body = setup(env)
    task = post(env, body).json()
    store = env[0]
    with store.tx() as c:
        runtime = c.execute(
            select(projects.c.runtime_id).where(projects.c.id == env[-2])
        ).scalar_one()
        identity = env[3] if who == "owner" else runtime
        c.execute(
            update(grants)
            .where(
                grants.c.principal_id == identity,
                grants.c.resource_id
                == (body["resource_id"] if tool == "resource.read" else env[-2]),
                grants.c.tool_ref == tool,
            )
            .values(**({"expires_at": time.time() - 1} if expired else {"revoked": True}))
        )
    before = count(store, resources)
    assert post(env, body).status_code == 403
    new = {**body, "request_key": "after-revoke"}
    assert post(env, new).status_code == 403
    assert env[2].get("/api/spec-checklist-tasks/" + task["id"]).status_code == 403
    assert count(store, resources) == before


def test_cross_owner_project_runtime_and_no_token(env):
    body = setup(env)
    task = post(env, body).json()
    store, s, client, a, b, pid, _ = env
    client.headers["Authorization"] = "Bearer synthetic-test-B"
    other = client.post("/api/projects", json={"name": "other"}).json()["id"]
    before = count(store, resources)
    assert post(env, body).status_code == 403
    assert client.post(f"/api/projects/{other}/spec-checklist-tasks", json=body).status_code == 403
    assert client.get("/api/spec-checklist-tasks/" + task["id"]).status_code == 403
    client.headers.pop("Authorization")
    assert post(env, body).status_code == 403
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    # A foreign runtime receives no synthetic grants from this interface.
    with store.tx() as c:
        foreign = c.execute(
            select(projects.c.runtime_id).where(projects.c.id == other)
        ).scalar_one()
        c.execute(update(projects).where(projects.c.id == pid).values(runtime_id=foreign))
    assert post(env, body).status_code == 403
    assert count(store, resources) == before


def test_idempotency_conflict_and_concurrent_one_output(env):
    body = setup(env)
    before = count(env[0], resources)
    barrier = Barrier(2)

    def submit():
        barrier.wait(timeout=5)
        return complete_checklist(env[0], env[3], env[-2], body)

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = list(pool.map(lambda _: submit(), range(2)))
    assert a["id"] == b["id"] and a["output"] == b["output"]
    assert count(env[0], resources) == before + 1
    assert post(env, {**body, "candidate_json": body["candidate_json"] + " "}).status_code == 409


@pytest.mark.parametrize(
    "fault", ["source_drift", "output_tamper", "proof_tamper", "request_binding"]
)
def test_saved_current_source_and_receipt_tamper_rejected(env, fault):
    body = setup(env)
    task = post(env, body).json()
    store = env[0]
    with store.tx() as c:
        if fault == "source_drift":
            content = FIXTURE.replace("v2", "v3", 1)
            c.execute(
                update(resources)
                .where(resources.c.id == body["resource_id"])
                .values(content=content, hash=hashlib.sha256(content.encode()).hexdigest())
            )
        elif fault == "output_tamper":
            c.execute(
                update(resources)
                .where(resources.c.id == task["output"]["resource_id"])
                .values(content="{}", hash=hashlib.sha256(b"{}").hexdigest())
            )
        elif fault == "proof_tamper":
            proof = copy.deepcopy(task["proof"])
            proof["check_version"] = "unverified"
            c.execute(
                update(spec_checklist_tasks)
                .where(spec_checklist_tasks.c.id == task["id"])
                .values(proof=proof, proof_fingerprint=fingerprint(proof))
            )
        else:
            request = copy.deepcopy(body)
            request["resource_id"] = "res_" + "0" * 32
            c.execute(
                update(spec_checklist_tasks)
                .where(spec_checklist_tasks.c.id == task["id"])
                .values(request=request, request_fingerprint=fingerprint(request))
            )
    before = count(store, resources)
    assert env[2].get("/api/spec-checklist-tasks/" + task["id"]).status_code in [400, 409]
    assert post(env, body).status_code in [400, 409]
    assert count(store, resources) == before


def test_failed_write_rolls_back_output_and_read_grants(env, monkeypatch):
    from sim2act import spec_checklists

    original = spec_checklists.write_text_artifact

    def fail(*args):
        original(*args)
        raise DomainError("VERIFICATION_FAILED", "Injected readback failure")

    body = setup(env)
    before = [count(env[0], t) for t in [resources, grants]]
    monkeypatch.setattr(spec_checklists, "write_text_artifact", fail)
    r = post(env, body)
    assert r.status_code == 201 and r.json()["status"] == "FAILED"
    assert [count(env[0], t) for t in [resources, grants]] == before
    assert r.json()["output"] is None


def test_live_interface_denied_without_calls(env):
    body = setup(env)
    with TestClient(create_app(env[0], replace(env[1], mode="live", live_enabled=False))) as client:
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        r = client.post(f"/api/projects/{env[-2]}/spec-checklist-tasks", json=body)
        assert r.status_code == 400 and r.json()["error"]["code"] == "UNSUPPORTED_CAPABILITY"
    assert count(env[0], spec_checklist_tasks) == 0


def test_application_crud_role_no_ddl(env, runtime_role):
    body = setup(env)
    role_store = Store(runtime_role)
    with role_store.engine.connect() as c:
        flags = c.exec_driver_sql(
            "SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user"
        ).one()
        assert not any(flags)
        with pytest.raises(ProgrammingError):
            c.exec_driver_sql("CREATE TABLE forbidden_spec(id integer)")
        c.rollback()
    with TestClient(create_app(role_store, replace(env[1], database_url=runtime_role))) as client:
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        r = client.post(f"/api/projects/{env[-2]}/spec-checklist-tasks", json=body)
        assert r.status_code == 201 and r.json()["status"] == "SUCCEEDED"
        assert client.get("/api/spec-checklist-tasks/" + r.json()["id"]).status_code == 200
    role_store.engine.dispose()


@pytest.mark.parametrize(
    "fault", ["empty_output", "wrong_output_type", "request_candidate_type", "integer_marker"]
)
def test_malformed_saved_shapes_fail_closed_without_500(env, fault):
    body = setup(env)
    task = post(env, body).json()
    store = env[0]
    with store.tx() as c:
        if fault in {"request_candidate_type", "integer_marker"}:
            request = copy.deepcopy(body)
            request[
                "candidate_json" if fault == "request_candidate_type" else "synthetic_fixture"
            ] = 1
            values = {"request": request, "request_fingerprint": fingerprint(request)}
        else:
            values = {"output": {} if fault == "empty_output" else 1}
        c.execute(
            update(spec_checklist_tasks)
            .where(spec_checklist_tasks.c.id == task["id"])
            .values(**values)
        )
    before = [count(store, t) for t in [resources, grants, spec_checklist_tasks]]
    assert env[2].get("/api/spec-checklist-tasks/" + task["id"]).status_code in [400, 409]
    assert post(env, body).status_code in [400, 409]
    assert [count(store, t) for t in [resources, grants, spec_checklist_tasks]] == before


def test_integer_synthetic_marker_rejected_before_any_persistence(env):
    body = setup(env)
    before = [count(env[0], t) for t in [resources, grants, spec_checklist_tasks]]
    response = post(env, {**body, "synthetic_fixture": 1})
    assert response.status_code == 422
    assert [count(env[0], t) for t in [resources, grants, spec_checklist_tasks]] == before
