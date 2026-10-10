"""Explicit logic authority precedes new grants; workers read only the new CSV."""

import copy
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select, update
from test_csv_dag import NoModel
from test_csv_dag_instances import create, enqueue, release, work
from test_delivery_graph_apps import snapshot

from sim2act import csv_logic_reuse as logic
from sim2act.db import (
    Store,
    delivery_graph_requests,
    fingerprint,
    internal_approvals,
    internal_instance_data,
    internal_releases,
    operations,
    resources,
    runs,
)
from sim2act.worker import Worker


def authorize(env, rel, key="explicit-logic"):
    body = dict(expected_release_fingerprint=rel["fingerprint"], consent=logic.CONSENT, request_key=key)
    reply = env[2].post(f"/api/internal/releases/{rel['id']}/csv-logic-authorizations", json=body)
    assert reply.status_code == 201, reply.text
    return reply.json()["logic"], body


def setup_logic(env, with_report=True, *, mint=True):
    aid, old_rid, _, job, rel = release(env, with_report=with_report)
    obj, auth = authorize(env, rel) if mint else (None, None)
    client, pid = env[2], env[5]
    reply = client.post(f"/api/projects/{pid}/resources", json=dict(name="fresh-only.csv", format="csv",
        content="label,net,units\nfresh-A,-4.5,2\nfresh-B,12,7\nfresh-C,1.25,4\n"))
    assert reply.status_code == 201, reply.text
    rid = reply.json()["id"]
    app = client.post(f"/api/projects/{pid}/apps/csv-preview", json=dict(
        name="New independently authorized app", goal="New data", resource_id=rid)).json()
    app = client.get(f"/api/apps/{app['id']}").json()
    anchor = client.post(f"/api/projects/{pid}/apps/{app['id']}/delivery-graph/derive", json=dict(
        expected_candidate_fingerprint=app["fingerprint"], request_key="fresh-anchor")).json()
    body = dict(expected_logic_fingerprint=obj["fingerprint"] if obj else "0" * 64,
        target_app_id=app["id"], expected_candidate_fingerprint=app["fingerprint"],
        expected_graph_fingerprint=anchor["graph_fingerprint"], expected_resource_id=rid,
        expected_source_hash=app["candidate"]["source_hash"], column="net", request_key="fresh-plan")
    return obj, rel, aid, old_rid, job, app, body, auth


def plan_path(obj):
    return f"/api/internal/csv-logics/{obj['id']}/material-plans"


def accept(env, obj, body):
    reply = env[2].post(plan_path(obj), json=body)
    assert reply.status_code == 201, reply.text
    p = reply.json()["plan"]
    reply = env[2].post(f"/api/projects/{env[5]}/apps/{body['target_app_id']}/csv-dag/{p['request_key']}/runs",
        json=dict(expected_plan_fingerprint=p["plan_fingerprint"], consent="CONFIRM_EXACT_OFFLINE_CSV_DAG",
                  request_key="fresh-run"))
    assert reply.status_code == 202, reply.text
    return p, reply.json()


def revoke_logic(env, obj):
    reply = env[2].post(f"/api/internal/csv-logics/{obj['id']}/revoke", json=dict(
        expected_logic_fingerprint=obj["fingerprint"], consent="REVOKE_DATA_FREE_CSV_LOGIC", request_key="stop-logic"))
    assert reply.status_code == 200, reply.text
    return reply.json()


def retire_old(env, old_rid):
    values = env[2].get(f"/api/projects/{env[5]}/grants").json()
    for g in values:
        if g["resource_id"] == old_rid and not g["revoked"]:
            r = env[2].post(f"/api/grants/{g['id']}/revoke", json=dict(command="revoke", version=g["revision"]))
            assert r.status_code == 200, r.text
    assert env[2].get(f"/api/resources/{old_rid}").status_code == 403
    # No product delete endpoint: retire only this test's synthetic resource row.
    with env[0].tx() as c:
        c.execute(delete(resources).where(resources.c.id == old_rid))


@pytest.mark.parametrize("with_report", [False, True])
def test_authorize_before_register_delete_old_then_actual_target_cold_instance(env, with_report):
    from fastapi.testclient import TestClient

    from sim2act.api import create_app

    obj, rel, _, old_rid, old_job, _, body, auth = setup_logic(env, with_report)
    assert env[2].get(f"/api/internal/releases/{rel['id']}").status_code != 200
    retire_old(env, old_rid)
    assert env[2].get(f"/api/csv-dag/runs/{old_job['id']}").status_code != 200
    assert env[2].get(f"/api/internal/releases/{rel['id']}").status_code != 200
    public = json.dumps(obj)
    for private in ("amount", "quantity", '"total"', "formatted", rel["snapshot"]["execution_source"]["source_hash"], old_rid, rel["id"], old_job["id"], "private_audit"):
        assert private not in public, private
    assert env[2].post(f"/api/internal/releases/{rel['id']}/csv-logic-authorizations", json=auth).json()["logic"] == obj
    target = env[2].get(f"/api/apps/{body['target_app_id']}").json()
    anchor = env[2].post(f"/api/projects/{env[5]}/apps/{target['id']}/delivery-graph/derive", json=dict(expected_candidate_fingerprint=target["fingerprint"], request_key="retired-anchor")).json()
    body["expected_graph_fingerprint"] = anchor["graph_fingerprint"]
    before = snapshot(env)
    opts = env[2].get(f"/api/internal/csv-logics/{obj['id']}/materials")
    assert opts.status_code == 200 and [v["resource_id"] for v in opts.json()["items"]] == [body["expected_resource_id"]]
    assert fingerprint(snapshot(env)) == fingerprint(before)
    p, accepted = accept(env, obj, body)
    work(env, accepted)
    detail = env[2].get(f"/api/csv-dag/runs/{accepted['run_id']}")
    assert detail.status_code == 200, detail.text
    proof = detail.json()
    output = next(iter(proof["result"]["output_by_step"].values()))
    assert proof["status"] == "SUCCEEDED" and len(proof["steps"]) == (3 if with_report else 2)
    assert output["resource_id"] == body["expected_resource_id"] and output["sum"] == "8.75" and output["count"] == 3
    with env[0].tx() as c:
        actual = c.execute(select(operations).where(operations.c.run_id == accepted["run_id"])).mappings().all()
        assert all(old_rid not in json.dumps(dict(op)) for op in actual)
        assert c.execute(select(runs.c.version).where(runs.c.id == old_job["id"])).scalar_one() == rel["snapshot"]["execution_source"]["run_version"]
    approval = env[2].post(f"/api/csv-dag/runs/{accepted['run_id']}/release-approvals", json=dict(
        expected_plan_fingerprint=p["plan_fingerprint"], request_key="fresh-release"))
    assert approval.status_code == 201, approval.text
    a = approval.json()
    r = env[2].post(f"/api/internal/approvals/{a['id']}/commit", json=dict(fingerprint=a["fingerprint"]))
    assert r.status_code == 200, r.text
    new = r.json()
    i = create(env, new)
    cold = Store(env[1].database_url, test_only=True)
    cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    try:
        client = TestClient(create_app(cold, env[1]))
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        assert client.get(f"/api/projects/{env[5]}/csv-logics").json()["items"] == [obj]
        accepted = client.post(f"/api/internal/instances/{i['id']}/runs", json=dict(expected_revision=1,
            expected_release_fingerprint=new["fingerprint"], input={"column": "units"}, request_key="cold-units"))
        assert accepted.status_code == 202, accepted.text
        worker = Worker(cold, env[1], NoModel())
        job = cold.claim(worker.id, env[1].lease_seconds)
        worker.process(job)
        d = client.get(f"/api/internal/instances/{i['id']}")
        assert d.status_code == 200, d.text
        result = d.json()["data"][0]["data"]["result"]
        assert result["sum"] == "13" and result["count"] == 3 and result["resource_id"] == body["expected_resource_id"]
        revoke_logic(env, obj)
        assert client.get(f"/api/internal/instances/{i['id']}").status_code != 200
        assert client.post(f"/api/internal/instances/{i['id']}/runs", json=dict(expected_revision=1,
            expected_release_fingerprint=new["fingerprint"], input={"column": "net"}, request_key="revoked-new-key")).status_code != 202
        client.close()
    finally:
        cold.engine.dispose()


def test_stale_source_cannot_mint_or_fake_authority(env):
    _, rel, _, _, _, _, body, _ = setup_logic(env, mint=False)
    before = fingerprint(snapshot(env))
    r = env[2].post(f"/api/internal/releases/{rel['id']}/csv-logic-authorizations", json=dict(
        expected_release_fingerprint=rel["fingerprint"], consent=logic.CONSENT, request_key="too-late"))
    assert r.status_code != 201
    assert env[2].post(plan_path({"id": "csvlogic_" + "0" * 32}), json=body).status_code == 403
    assert fingerprint(snapshot(env)) == before


@pytest.mark.parametrize("attack", ["column", "hash", "candidate", "owner", "source-json", "source-version", "logic-seal", "logic-json", "target-grant", "target-bytes", "expired", "revoked"])
def test_changed_authority_or_target_denies_before_plan_write(env, monkeypatch, attack):
    obj, rel, _, _, old_job, target, body, _ = setup_logic(env)
    if attack == "column":
        body["column"] = "label"
    elif attack == "hash":
        body["expected_source_hash"] = "0" * 64
    elif attack == "candidate":
        body["expected_candidate_fingerprint"] = "0" * 64
    elif attack == "owner":
        env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    elif attack == "expired":
        monkeypatch.setattr(logic, "time", SimpleNamespace(time=lambda: obj["expires_at"] + 1))
    elif attack == "revoked":
        revoke_logic(env, obj)
    else:
        with env[0].tx() as c:
            if attack == "source-json":
                s = copy.deepcopy(rel["snapshot"])
                s["draft"]["candidate"]["goal"] = "corruption"
                c.execute(update(internal_releases).where(internal_releases.c.id == rel["id"]).values(snapshot=s))
            elif attack == "source-version":
                c.execute(update(runs).where(runs.c.id == old_job["id"]).values(version=999))
            elif attack == "logic-seal":
                c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.kind == logic.AUTH_KIND + "_seal"))
            elif attack == "logic-json":
                row = c.execute(select(internal_approvals).where(internal_approvals.c.id == obj["id"])).mappings().one()
                p = copy.deepcopy(row["payload"])
                p["recipe"]["nodes"][0]["action"] = "evil"
                c.execute(update(internal_approvals).where(internal_approvals.c.id == obj["id"]).values(payload=p, fingerprint=fingerprint(p)))
            elif attack == "target-grant":
                from sim2act.db import grants
                c.execute(update(grants).where(grants.c.principal_id == target["runtime_id"], grants.c.resource_id == body["expected_resource_id"]).values(revoked=True))
            else:
                c.execute(update(resources).where(resources.c.id == body["expected_resource_id"]).values(content="net\n900\n"))
    before = fingerprint(snapshot(env))
    assert env[2].post(plan_path(obj), json=body).status_code != 201
    assert fingerprint(snapshot(env)) == before


@pytest.mark.parametrize("stage", ["queued", "between", "final-typed"])
def test_expiry_or_revoke_at_commit_rolls_back_target_writes(env, monkeypatch, stage):
    from sim2act import csv_dag as dag
    from sim2act import csv_dag_instances as instances

    obj, _, _, _, _, _, body, _ = setup_logic(env)
    p, accepted = accept(env, obj, body)
    w = Worker(env[0], env[1], NoModel())
    job = env[0].claim(w.id, env[1].lease_seconds)
    if stage == "queued":
        revoke_logic(env, obj)
        w.process(job)
    elif stage == "between":
        dag.advance(w, job)
        revoke_logic(env, obj)
        w.process(job)
    else:
        # First complete the target source, then exercise actual instance typed commit.
        w.process(job)
        a = env[2].post(f"/api/csv-dag/runs/{job['id']}/release-approvals", json=dict(expected_plan_fingerprint=p["plan_fingerprint"], request_key="final-release")).json()
        rel = env[2].post(f"/api/internal/approvals/{a['id']}/commit", json=dict(fingerprint=a["fingerprint"])).json()
        i = create(env, rel)
        accepted, _ = enqueue(env, i, rel, "units")
        job = env[0].claim(w.id, env[1].lease_seconds)
        original = instances.commit_result

        def expire_after_write(*args, **kwargs):
            original(*args, **kwargs)
            monkeypatch.setattr(logic, "time", SimpleNamespace(time=lambda: obj["expires_at"] + 1))

        monkeypatch.setattr(instances, "commit_result", expire_after_write)
        w.process(job)
        with env[0].tx() as c:
            assert c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == i["id"])).first() is None
    with env[0].tx() as c:
        row = c.execute(select(runs).where(runs.c.id == job["id"])).mappings().one()
        assert row["status"] != "SUCCEEDED"
        actual = c.execute(select(operations).where(operations.c.run_id == job["id"])).all()
        assert len(actual) == (0 if stage == "queued" else 1 if stage == "between" else 3)


def test_reserved_prefix_cannot_downgrade_when_both_origins_removed(env):
    obj, _, _, _, _, _, body, _ = setup_logic(env)
    p, _ = accept(env, obj, body)
    with env[0].tx() as c:
        c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.kind.in_([logic.ORIGIN, logic.ORIGIN + "_seal"])))
        rows = c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.kind.in_(["csv_dag_plan", "csv_dag_plan_seal"]), delivery_graph_requests.c.request_key == p["request_key"])).mappings().all()
        for r in rows:
            payload = copy.deepcopy(r["snapshot"])
            answer = payload["response"]
            answer.pop("logical_reuse")
            answer["plan_fingerprint"] = fingerprint({k: v for k, v in answer.items() if k != "plan_fingerprint"})
            c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.app_id == r["app_id"], delivery_graph_requests.c.principal_id == r["principal_id"], delivery_graph_requests.c.kind == r["kind"], delivery_graph_requests.c.request_key == r["request_key"]).values(snapshot=payload, fingerprint=fingerprint(payload)))
    assert env[2].get(f"/api/projects/{env[5]}/apps/{body['target_app_id']}/csv-dag/{p['request_key']}").status_code != 200


def test_both_resigned_authority_origins_cannot_change_zero_to_bool(env):
    obj, _, _, _, _, _, body, _ = setup_logic(env)
    with env[0].tx() as c:
        rows = c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.kind.in_(
            [logic.AUTH_KIND, logic.AUTH_KIND + "_seal"]))).mappings().all()
        assert len(rows) == 2
        for row in rows:
            value = copy.deepcopy(row["snapshot"])
            value["response"]["model_requests"] = False
            c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.app_id == row["app_id"],
                delivery_graph_requests.c.principal_id == row["principal_id"], delivery_graph_requests.c.kind == row["kind"],
                delivery_graph_requests.c.request_key == row["request_key"]).values(snapshot=value, fingerprint=fingerprint(value)))
    before = fingerprint(snapshot(env))
    assert env[2].get(f"/api/internal/csv-logics/{obj['id']}").status_code == 409
    assert env[2].post(plan_path(obj), json=body).status_code == 409
    assert fingerprint(snapshot(env)) == before


def test_both_resigned_authority_request_keys_cannot_change_original_intent(env):
    obj, _, _, _, _, _, body, _ = setup_logic(env)
    with env[0].tx() as c:
        rows = c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.kind.in_(
            [logic.AUTH_KIND, logic.AUTH_KIND + "_seal"]))).mappings().all()
        assert len(rows) == 2
        for row in rows:
            value = copy.deepcopy(row["snapshot"])
            value["request"]["request_key"] = "resigned-different-intent"
            c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.app_id == row["app_id"],
                delivery_graph_requests.c.principal_id == row["principal_id"], delivery_graph_requests.c.kind == row["kind"],
                delivery_graph_requests.c.request_key == row["request_key"]).values(snapshot=value,
                fingerprint=fingerprint(value), request_fingerprint=fingerprint(value["request"])))
    before = fingerprint(snapshot(env))
    assert env[2].get(f"/api/internal/csv-logics/{obj['id']}").status_code == 409
    assert env[2].post(plan_path(obj), json=body).status_code == 409
    assert fingerprint(snapshot(env)) == before


def test_actual_fab_source_upgrade_denies_stale_mint_without_rewriting_old_proof(env, tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    from test_csv_dag_upgrade import raw_history_hashes

    archive = os.environ.get("SIM2ACT_LOGIC_OLD_ARCHIVE")
    if not archive:
        pytest.skip("Explicit actual fab14d5 source archive required")
    driver = os.environ["SIM2ACT_LOGIC_OLD_DRIVER"]
    out = tmp_path / "old-proof.json"
    body = dict(database_url=env[1].database_url,
        schema=env[0].engine.get_execution_options().get("schema_translate_map", {}).get(None),
        root=str(tmp_path), owner=env[3], other=env[4], project=env[5], resource=env[6], out=str(out))
    child = subprocess.run([sys.executable, driver], cwd=archive,
        env={**os.environ, "PYTHONPATH": archive + "/src:" + archive + "/tests", "LIVE": "0"},
        input=json.dumps(body), text=True, capture_output=True, timeout=60)
    (tmp_path / "old-driver.log").write_text(child.stdout + child.stderr)
    assert child.returncode == 0, child.stdout + child.stderr
    old = json.loads(out.read_text())
    for path, h in old["source_files"].items():
        import hashlib
        assert hashlib.sha256((Path(archive) / path).read_bytes()).hexdigest() == h
    tables = ["runs", "operations", "operation_intents", "events", "delivery_graph_requests", "delivery_graph_anchors", "internal_releases", "internal_approvals", "resources", "app_drafts"]
    before = raw_history_hashes(env[0], tables)
    r = env[2].post(f"/api/internal/releases/{old['release']['id']}/csv-logic-authorizations", json=dict(
        expected_release_fingerprint=old["release"]["fingerprint"], consent=logic.CONSENT, request_key="stale-upgrade"))
    assert r.status_code == 409, r.text
    assert env[2].get(f"/api/internal/releases/{old['release']['id']}").status_code == 409
    assert raw_history_hashes(env[0], tables) == before
    _, _, _, _, fresh = release(env, with_report=True)
    obj, _ = authorize(env, fresh)
    assert obj["status"] == "ACTIVE" and obj["execution_version"] == "internal.csv-read-sum-report.v1"
    (tmp_path / "upgrade-proof.json").write_text(json.dumps(dict(old_sha="fab14d542d7efe41d0b290e5b5baec433a1669a9",
        old_source_files=old["source_files"], old_release_id=old["release"]["id"], rejected_stale_mint=r.status_code,
        original_raw_rows_unchanged=True, fresh_logic_id=obj["id"], model_requests=0), indent=2)+'\n')


def test_alias_of_original_resource_denied_before_any_original_resource_select(env):
    from sqlalchemy import event

    obj, rel, source_aid, old_rid, _, _, _, _ = setup_logic(env)
    # An existing alias can share the old rid; even options must never load it.
    alias = env[2].post(f"/api/projects/{env[5]}/apps/csv-preview", json=dict(name="Old resource alias",
        goal="PRIVATE_ALIAS", resource_id=old_rid)).json()["id"]
    selected = []

    def watch(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT") and "resources" in statement.lower() and old_rid in str(parameters):
            selected.append(statement)

    event.listen(env[0].engine, "before_cursor_execute", watch)
    try:
        response = env[2].get(f"/api/internal/csv-logics/{obj['id']}/materials")
        assert response.status_code == 200, response.text
        assert all(v["target_app_id"] not in (source_aid, alias) for v in response.json()["items"])
        from test_internal_lifecycle import limits
        with env[0].tx() as c:
            public, src = logic.load(env[0], c, env[3], obj["id"], limits(env))
            for aid in (source_aid, alias):
                from sim2act.errors import DomainError
                with pytest.raises(DomainError):
                    logic.target(env[0], c, env[3], public, src, aid, limits(env))
        assert selected == []
    finally:
        event.remove(env[0].engine, "before_cursor_execute", watch)


def test_platform_tightening_denies_reuse_but_owner_can_revoke(env):
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from sim2act.api import create_app

    obj, _, _, old_rid, _, _, body, _ = setup_logic(env)
    retire_old(env, old_rid)
    client = TestClient(create_app(env[0], replace(env[1], max_tools=1)))
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    before = fingerprint(snapshot(env))
    assert client.post(plan_path(obj), json=body).status_code != 201
    assert fingerprint(snapshot(env)) == before
    assert client.get(f"/api/internal/csv-logics/{obj['id']}").json()["status"] == "ACTIVE"
    r = client.post(f"/api/internal/csv-logics/{obj['id']}/revoke", json=dict(
        expected_logic_fingerprint=obj["fingerprint"], consent="REVOKE_DATA_FREE_CSV_LOGIC", request_key="tight-budget-stop"))
    assert r.status_code == 200 and r.json()["status"] == "REVOKED"
    client.close()


def test_same_owner_cross_project_target_denied_before_write(env):
    obj, _, _, _, _, _, body, _ = setup_logic(env)
    other = env[2].post("/api/projects", json=dict(name="Separate project")).json()["id"]
    rid = env[2].post(f"/api/projects/{other}/resources", json=dict(name="elsewhere.csv", format="csv", content="net\n888\n")).json()["id"]
    aid = env[2].post(f"/api/projects/{other}/apps/csv-preview", json=dict(name="Other project target", goal="Separate", resource_id=rid)).json()["id"]
    body["target_app_id"] = aid
    before = fingerprint(snapshot(env))
    assert env[2].post(plan_path(obj), json=body).status_code == 403
    assert fingerprint(snapshot(env)) == before


def test_malformed_target_binding_rejected_before_resource_read(env):
    from sim2act.db import app_drafts

    obj, _, _, _, _, app, body, _ = setup_logic(env)
    p = copy.deepcopy(app["candidate"])
    p["manifest"]["data_bindings"] = [False]
    with env[0].tx() as c:
        c.execute(update(app_drafts).where(app_drafts.c.id == app["id"]).values(candidate=p, fingerprint=fingerprint(p)))
    before = fingerprint(snapshot(env))
    r = env[2].post(plan_path(obj), json=body)
    assert r.status_code in (400, 403, 409, 422), r.text
    assert fingerprint(snapshot(env)) == before


def test_logic_instance_prefix_cannot_drop_all_origins_and_markers(env):
    obj, _, _, _, _, app, body, _ = setup_logic(env)
    p, accepted = accept(env, obj, body)
    work(env, accepted)
    a = env[2].post(f"/api/csv-dag/runs/{accepted['run_id']}/release-approvals", json=dict(expected_plan_fingerprint=p["plan_fingerprint"], request_key="derived-release")).json()
    rel = env[2].post(f"/api/internal/approvals/{a['id']}/commit", json=dict(fingerprint=a["fingerprint"])).json()
    i = create(env, rel)
    accepted, _ = enqueue(env, i, rel, "units")
    with env[0].tx() as c:
        from sim2act.db import internal_run_bindings
        key = c.execute(select(internal_run_bindings.c.snapshot).where(internal_run_bindings.c.run_id == accepted["run_id"])).scalar_one()["plan_key"]
        assert key.startswith(logic.INSTANCE_PREFIX)
        c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.kind.in_([logic.DERIVED, logic.DERIVED + "_seal"])))
        rows = c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.kind.in_(["csv_dag_plan", "csv_dag_plan_seal"]), delivery_graph_requests.c.request_key == key)).mappings().all()
        for row in rows:
            v = copy.deepcopy(row["snapshot"])
            v["request"].pop("logic_origin")
            v["response"].pop("logical_reuse")
            v["response"]["plan_fingerprint"] = fingerprint({k: value for k, value in v["response"].items() if k != "plan_fingerprint"})
            c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.app_id == row["app_id"],
                delivery_graph_requests.c.principal_id == row["principal_id"], delivery_graph_requests.c.kind == row["kind"],
                delivery_graph_requests.c.request_key == key).values(snapshot=v, fingerprint=fingerprint(v), request_fingerprint=fingerprint(v["request"])))
    assert env[2].get(f"/api/projects/{env[5]}/apps/{app['id']}/csv-dag/{key}").status_code == 409
    work(env, accepted)
    with env[0].tx() as c:
        assert c.execute(select(operations).where(operations.c.run_id == accepted["run_id"])).first() is None
        assert c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == i["id"])).first() is None
