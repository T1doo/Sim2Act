"""Actual closed DAG provenance, fresh cold inputs and atomic typed persistence."""

import copy
import hashlib
from fractions import Fraction

import pytest
from sqlalchemy import delete, select, update
from test_column_patches import setup as source_setup
from test_csv_dag import NoModel
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits

from sim2act import csv_dag as dag
from sim2act import csv_dag_instances as instances
from sim2act import lifecycle
from sim2act.db import (
    Store,
    fingerprint,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    operations,
    resources,
    runs,
)
from sim2act.errors import DomainError
from sim2act.worker import Worker


def setup(env, completed=True, *, with_report=False):
    aid, rid, anchor, _, _ = source_setup(env)
    base = f"/api/projects/{env[5]}/apps/{aid}/csv-dag"
    composition = dict(
        version="csv.composition.v1",
        nodes=[
            dict(
                step_id="read",
                action="resource.read",
                depends_on=[],
                inputs=dict(resource_id=dict(source="data", ref="source", field="resource_id")),
            ),
            dict(
                step_id="total",
                action="data.aggregate_csv",
                column="amount",
                depends_on=["read"],
                inputs=dict(
                    resource_id=dict(source="step", ref="read", field="resource_id"),
                    column=dict(source="input", field="total_column"),
                ),
            ),
        ],
    )
    if with_report:
        composition["nodes"].append(dict(step_id="formatted", action="intern.csv_report.v1",
            depends_on=["total"], inputs={k: dict(source="step", ref="total", field=k)
                for k in ("resource_id", "column", "count", "sum", "source_hash")}))
    response = env[2].post(
        base,
        json=dict(
            expected_candidate_fingerprint=anchor["candidate_fingerprint"],
            expected_graph_fingerprint=anchor["graph_fingerprint"],
            column="amount",
            request_key="reusable",
            composition=composition,
        ),
    )
    assert response.status_code == 201, response.text
    plan = response.json()
    accepted = (
        env[2]
        .post(
            base + "/reusable/runs",
            json=dict(
                expected_plan_fingerprint=plan["plan_fingerprint"],
                consent="CONFIRM_EXACT_OFFLINE_CSV_DAG",
                request_key="source",
            ),
        )
        .json()
    )
    worker = Worker(env[0], env[1], NoModel())
    job = env[0].claim(worker.id, env[1].lease_seconds)
    assert job["id"] == accepted["run_id"]
    if completed:
        worker.process(job)
        assert dag.inspect_job(env[0], env[3], job["id"], limits(env))["status"] == "SUCCEEDED"
    return aid, rid, plan, worker, job


def release(env, *, with_report=False):
    aid, rid, plan, _, job = setup(env, with_report=with_report)
    approval = env[2].post(
        f"/api/csv-dag/runs/{job['id']}/release-approvals",
        json=dict(expected_plan_fingerprint=plan["plan_fingerprint"], request_key="prepare"),
    )
    assert approval.status_code == 201, approval.text
    a = approval.json()
    read = env[2].get("/api/internal/approvals/" + a["id"])
    assert read.status_code == 200, read.text
    committed = env[2].post(
        "/api/internal/approvals/" + a["id"] + "/commit", json=dict(fingerprint=a["fingerprint"])
    )
    assert committed.status_code == 200, committed.text
    return aid, rid, plan, job, committed.json()


def create(env, rel, key="one"):
    reply = env[2].post(
        "/api/internal/releases/" + rel["id"] + "/instances",
        json=dict(expected_release_fingerprint=rel["fingerprint"], request_key=key),
    )
    assert reply.status_code == 201, reply.text
    return reply.json()


def enqueue(env, i, rel, column="quantity", key="new-column"):
    body = dict(
        expected_revision=i["revision"],
        expected_release_fingerprint=rel["fingerprint"],
        input=dict(column=column),
        request_key=key,
    )
    reply = env[2].post("/api/internal/instances/" + i["id"] + "/runs", json=body)
    assert reply.status_code == 202, reply.text
    return reply.json(), body


def work(env, accepted):
    w = Worker(env[0], env[1], NoModel())
    job = env[0].claim(w.id, env[1].lease_seconds)
    assert job["id"] == accepted["run_id"]
    w.process(job)
    return job


def test_actual_two_nodes_two_cold_columns_instances_and_read_only_recovery(env):
    aid, rid, original, source, rel = release(env)
    assert rel["snapshot"]["execution_source"]["version"] == instances.VERSION
    assert rel["snapshot"]["execution_source"]["columns"] == ["amount", "quantity"]
    a, b = create(env, rel), create(env, rel, "second")
    assert create(env, rel)["id"] == a["id"]
    assert env[2].get(f"/api/internal/apps/{aid}/releases").json()["items"] == []
    assert len(env[2].get(f"/api/internal/apps/{aid}/dag-releases").json()["items"]) == 1
    results = []
    for i, col, key, wanted in [
        (a, "quantity", "new", 15),
        (a, "amount", "another", 30),
        (b, "quantity", "new", 15),
    ]:
        accepted, body = enqueue(env, i, rel, col, key)
        work(env, accepted)
        reply = env[2].get(f"/api/internal/instances/{i['id']}/runs/{accepted['run_id']}")
        assert reply.status_code == 200, reply.text
        result = reply.json()
        assert result["status"] == "SUCCEEDED" and Fraction(result["output"]["sum"]) == wanted
        assert result["output"]["column"] == col and result["output"]["resource_id"] == rid
        assert len(result["proof"]["steps"]) == 2 and result["proof"]["business_writes"] == 1
        assert (
            result["proof"]["result"]["business_writes"] == 1
            and result["proof"]["model_requests"] == 0
        )
        assert result["proof"]["steps"][1]["predecessor_receipts"] == [
            fingerprint(result["proof"]["steps"][0])
        ]
        assert (
            result["run_id"] != source["id"]
            and result["proof"]["plan_fingerprint"] != original["plan_fingerprint"]
        )
        repeat = env[2].post(f"/api/internal/instances/{i['id']}/runs", json=body)
        assert (
            repeat.status_code == 202
            and repeat.json()["run_id"] == accepted["run_id"]
            and repeat.json()["cached"]
        )
        results.append(result)
    assert [r["result_version"] for r in results] == [1, 2, 1]
    assert len({r["run_id"] for r in results}) == 3
    before = fingerprint(snapshot(env))
    cold = Store(env[1].database_url, test_only=True)
    cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    try:
        for r in results:
            assert (
                instances.inspect_job(cold, env[3], r["run_id"], limits(env))["output"]
                == r["output"]
            )
        assert lifecycle.inspect_instance(cold, env[3], a["id"], limits(env))["data_version"] == 2
    finally:
        cold.engine.dispose()
    assert fingerprint(snapshot(env)) == before
    with env[0].engine.connect() as c:
        assert (
            len(
                c.execute(
                    select(operations).where(
                        operations.c.run_id.in_([r["run_id"] for r in results])
                    )
                ).all()
            )
            == 6
        )
    assert env[2].get(f"/api/internal/apps/{aid}/instances").json()["items"] == []
    assert len(env[2].get(f"/api/internal/apps/{aid}/dag-instances").json()["items"]) == 2


def test_unfinished_source_cannot_prepare_release(env):
    _, _, plan, _, job = setup(env, False)
    before = fingerprint(snapshot(env))
    reply = env[2].post(
        f"/api/csv-dag/runs/{job['id']}/release-approvals",
        json=dict(expected_plan_fingerprint=plan["plan_fingerprint"], request_key="prepare"),
    )
    assert reply.status_code == 409, reply.text
    assert fingerprint(snapshot(env)) == before


@pytest.mark.parametrize(
    "attack", ["missing", "text", "override", "same-key", "release", "revision", "replay"]
)
def test_invalid_new_input_and_request_replay_write_nothing(env, attack):
    _, _, _, _, rel = release(env)
    i = create(env, rel)
    _, body = enqueue(env, i, rel)
    bad = copy.deepcopy(body)
    if attack == "missing":
        bad["input"] = {"column": "missing"}
    if attack == "text":
        bad["input"] = {"column": "item"}
    if attack == "override":
        bad["input"]["resource_id"] = "another"
    if attack == "same-key":
        bad["input"]["column"] = "amount"
    if attack == "release":
        bad["expected_release_fingerprint"] = "0" * 64
    if attack == "revision":
        bad["expected_revision"] = 2
    if attack == "replay":
        bad["offline_replay"] = [{}, {}]
    before = fingerprint(snapshot(env))
    reply = env[2].post(f"/api/internal/instances/{i['id']}/runs", json=bad)
    assert reply.status_code in {400, 409, 422}, reply.text
    assert fingerprint(snapshot(env)) == before


@pytest.mark.parametrize(
    "attack", ["grant", "source", "instance-aba", "binding-delete", "binding-input", "receipt"]
)
def test_changed_authority_provenance_or_cas_never_appends_result(env, attack):
    _, rid, _, _, rel = release(env)
    i = create(env, rel)
    accepted, _ = enqueue(env, i, rel)
    w = Worker(env[0], env[1], NoModel())
    job = env[0].claim(w.id, env[1].lease_seconds)
    assert job["id"] == accepted["run_id"]
    assert dag.advance(w, job)
    with env[0].tx() as c:
        if attack == "grant":
            c.execute(update(grants).where(grants.c.resource_id == rid).values(revoked=True))
        if attack == "source":
            c.execute(
                update(resources)
                .where(resources.c.id == rid)
                .values(content="bad", hash=hashlib.sha256(b"bad").hexdigest())
            )
        if attack == "instance-aba":
            c.execute(
                update(internal_instances)
                .where(internal_instances.c.id == i["id"])
                .values(revision=3)
            )
        if attack == "binding-delete":
            c.execute(
                delete(internal_run_bindings).where(internal_run_bindings.c.run_id == job["id"])
            )
        if attack == "binding-input":
            b = (
                c.execute(
                    select(internal_run_bindings).where(internal_run_bindings.c.run_id == job["id"])
                )
                .mappings()
                .one()
            )
            s = copy.deepcopy(b["snapshot"])
            s["input"]["column"] = "amount"
            c.execute(
                update(internal_run_bindings)
                .where(internal_run_bindings.c.run_id == job["id"])
                .values(snapshot=s, fingerprint=fingerprint(s))
            )
        if attack == "receipt":
            op = (
                c.execute(select(operations).where(operations.c.run_id == job["id"]))
                .mappings()
                .one()
            )
            receipt = copy.deepcopy(op["receipt"])
            receipt["data"]["content"] = "fake"
            c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=receipt))
    w.process(job)
    with env[0].engine.connect() as c:
        saved = c.execute(select(runs).where(runs.c.id == job["id"])).mappings().one()
        assert saved["status"] in {"WAITING_RESOURCE", "FAILED"} and saved["result"] is None
        assert not c.execute(
            select(internal_instance_data).where(internal_instance_data.c.instance_id == i["id"])
        ).first()
        assert (
            c.execute(
                select(internal_instances.c.data_version).where(internal_instances.c.id == i["id"])
            ).scalar_one()
            == 0
        )
    metadata = env[2].get(f"/api/internal/instances/{i['id']}/runs/{job['id']}/control-status")
    if attack in {"grant", "source", "instance-aba", "receipt"}:
        assert metadata.status_code == 200 and metadata.json()["content_access"] is False


def test_cold_lease_reclaim_and_old_fence_no_duplicate_operations(env):
    _, _, _, _, rel = release(env)
    i = create(env, rel)
    accepted, _ = enqueue(env, i, rel)
    w = Worker(env[0], env[1], NoModel())
    job = env[0].claim(w.id, env[1].lease_seconds)
    assert dag.advance(w, job)
    with env[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == job["id"]).values(lease_until=0))
    other = Worker(env[0], env[1], NoModel())
    claimed = env[0].claim(other.id, env[1].lease_seconds)
    assert claimed["fence"] > job["fence"]
    with pytest.raises(DomainError):
        dag.advance(w, job)
    other.process(claimed)
    proof = instances.inspect_job(env[0], env[3], job["id"], limits(env))
    assert (
        proof["status"] == "SUCCEEDED"
        and proof["result_version"] == 1
        and len(proof["proof"]["steps"]) == 2
    )


def test_cross_owner_control_metadata_and_other_instance_rejected(env):
    _, _, _, _, rel = release(env)
    i = create(env, rel)
    a, _ = enqueue(env, i, rel)
    b = create(env, rel, "other-instance")
    env[2].headers.update({"Authorization": "Bearer synthetic-test-B"})
    for suffix in ["", "/control-status"]:
        reply = env[2].get(f"/api/internal/instances/{i['id']}/runs/{a['run_id']}" + suffix)
        assert reply.status_code == 403, reply.text
    env[2].headers.update({"Authorization": "Bearer synthetic-test-A"})
    assert (
        env[2]
        .get(f"/api/internal/instances/{b['id']}/runs/{a['run_id']}/control-status")
        .status_code
        == 403
    )


def test_coherent_typed_output_tamper_cannot_replace_actual_operations(env):
    aid, _, _, _, rel = release(env)
    i = create(env, rel)
    a, _ = enqueue(env, i, rel)
    work(env, a)
    with env[0].tx() as c:
        ar = (
            c.execute(select(internal_app_runs).where(internal_app_runs.c.id == a["app_run_id"]))
            .mappings()
            .one()
        )
        output = copy.deepcopy(ar["output"])
        output["sum"] = "999"
        c.execute(
            update(internal_app_runs)
            .where(internal_app_runs.c.id == ar["id"])
            .values(output=output)
        )
        c.execute(
            update(internal_instance_data)
            .where(internal_instance_data.c.run_id == ar["id"])
            .values(data={"result": output}, fingerprint=fingerprint({"result": output}))
        )
    listing = env[2].get(f"/api/internal/apps/{aid}/dag-instances")
    assert listing.status_code == 200 and all("data" not in v for v in listing.json()["items"])
    assert env[2].get("/api/internal/instances/" + i["id"]).status_code == 409
    with pytest.raises(DomainError):
        lifecycle.inspect_instance(env[0], env[3], i["id"], limits(env))


@pytest.mark.parametrize("orphan", [False, True])
def test_release_origin_seal_rejects_family_downgrade(env, orphan):
    _, _, _, _, rel = release(env)
    i = create(env, rel)
    with env[0].tx() as c:
        from sim2act.db import internal_approvals

        if orphan:
            from sim2act.db import delivery_graph_requests

            c.execute(
                delete(delivery_graph_requests).where(
                    delivery_graph_requests.c.kind == "csv_dag_release_origin",
                    delivery_graph_requests.c.request_key == rel["approval_id"],
                )
            )
        snap = copy.deepcopy(rel["snapshot"])
        snap.pop("execution_source")
        a = (
            c.execute(
                select(internal_approvals).where(internal_approvals.c.id == rel["approval_id"])
            )
            .mappings()
            .one()
        )
        payload = copy.deepcopy(a["payload"])
        payload["snapshot"] = snap
        c.execute(
            update(internal_releases)
            .where(internal_releases.c.id == rel["id"])
            .values(snapshot=snap, fingerprint=fingerprint(snap))
        )
        c.execute(
            update(internal_approvals)
            .where(internal_approvals.c.id == a["id"])
            .values(payload=payload, fingerprint=fingerprint(payload))
        )
    assert env[2].get("/api/internal/releases/" + rel["id"]).status_code == 409
    assert env[2].get("/api/internal/instances/" + i["id"]).status_code == 409
    with pytest.raises(DomainError):
        lifecycle.run_instance(
            env[0],
            env[3],
            i["id"],
            1,
            fingerprint(snap),
            {"column": "quantity"},
            "wrong-executor",
            limits(env),
        )


def test_atomic_final_transaction_rolls_back_typed_append_on_terminal_write_failure(env):
    from sqlalchemy import event

    _, _, _, _, rel = release(env)
    i = create(env, rel)
    a, _ = enqueue(env, i, rel)
    w = Worker(env[0], env[1], NoModel())
    job = env[0].claim(w.id, env[1].lease_seconds)
    assert dag.advance(w, job) and dag.advance(w, job)

    def reject_terminal(conn, cursor, statement, parameters, context, executemany):
        if (
            context.compiled is not None
            and context.compiled.statement.is_update
            and context.compiled.statement.table is runs
            and context.compiled.params.get("status") == "SUCCEEDED"
        ):
            raise RuntimeError(
                "owned fixture injects failure after typed append, before terminal state"
            )

    event.listen(env[0].engine, "before_cursor_execute", reject_terminal)
    try:
        with pytest.raises(RuntimeError, match="owned fixture"):
            dag.advance(w, job)
    finally:
        event.remove(env[0].engine, "before_cursor_execute", reject_terminal)
    with env[0].engine.connect() as c:
        assert not c.execute(
            select(internal_instance_data).where(internal_instance_data.c.instance_id == i["id"])
        ).first()
        assert (
            c.execute(
                select(internal_app_runs.c.status).where(internal_app_runs.c.id == a["app_run_id"])
            ).scalar_one()
            == "QUEUED"
        )
        assert (
            c.execute(
                select(internal_instances.c.data_version).where(internal_instances.c.id == i["id"])
            ).scalar_one()
            == 0
        )
        assert (
            c.execute(select(runs.c.status).where(runs.c.id == job["id"])).scalar_one() == "RUNNING"
        )
    assert not dag.advance(w, job)
    assert instances.inspect_job(env[0], env[3], job["id"], limits(env))["result_version"] == 1


def test_preparation_and_commit_recover_exact_intent_without_duplicate_version(env):
    _, _, plan, _, job = setup(env)
    body = dict(expected_plan_fingerprint=plan["plan_fingerprint"], request_key="lost-response")
    url = f"/api/csv-dag/runs/{job['id']}/release-approvals"
    first = env[2].post(url, json=body)
    second = env[2].post(url, json=body)
    assert first.status_code == second.status_code == 201 and first.json() == second.json()
    a = first.json()
    endpoint = "/api/internal/approvals/" + a["id"] + "/commit"
    one = env[2].post(endpoint, json={"fingerprint": a["fingerprint"]})
    two = env[2].post(endpoint, json={"fingerprint": a["fingerprint"]})
    assert one.status_code == two.status_code == 200 and one.json()["id"] == two.json()["id"]


def test_actual_previous_dev_source_upgrade_preserves_old_proofs_and_requires_fresh_source(
    env, tmp_path
):
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    from test_csv_dag_upgrade import raw_history_hashes

    archive_value = os.environ.get("SIM2ACT_DAG_REUSE_OLD_ARCHIVE")
    if not archive_value:
        pytest.skip("Requires explicit actual 67c6ccc8 source archive")
    archive = Path(archive_value)
    old_module = archive / "src/sim2act/csv_dag.py"
    assert (
        hashlib.sha256(old_module.read_bytes()).hexdigest()
        == "e02a5a1e38910f64914e095e77da95cd7f0106dea49844f3a1723e37d0acc1d2"
    )
    out = tmp_path / "old-67-proof.json"
    body = dict(
        database_url=env[1].database_url,
        schema=env[0].engine.get_execution_options().get("schema_translate_map", {}).get(None),
        data_root=str(tmp_path),
        owner=env[3],
        other=env[4],
        project=env[5],
        resource=env[6],
        output=str(out),
    )
    driver = Path(__file__).with_name("fixtures") / "csv_dag_instance_upgrade.py"
    child = subprocess.run(
        [sys.executable, str(driver.resolve())],
        cwd=archive,
        env={
            **os.environ,
            "PYTHONPATH": str(archive / "src") + os.pathsep + str(archive / "tests"),
            "LIVE": "0",
        },
        input=json.dumps(body),
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert child.returncode == 0, child.stdout + child.stderr
    old = json.loads(out.read_text())
    assert Path(old["old_module_path"]).resolve() == old_module.resolve()
    assert (
        old["proof"]["result"]["output_by_step"]["total"]["sum"] == "30"
        and len(old["proof"]["steps"]) == 2
    )
    names = [
        "runs",
        "operations",
        "operation_intents",
        "events",
        "delivery_graph_requests",
        "delivery_graph_anchors",
        "delivery_graph_source_versions",
        "app_drafts",
        "app_previews",
        "resources",
    ]
    before = raw_history_hashes(env[0], names)
    reply = env[2].post(
        "/api/csv-dag/runs/" + old["run_id"] + "/release-approvals",
        json=dict(
            expected_plan_fingerprint=old["plan"]["plan_fingerprint"],
            request_key="new-reader-old-source",
        ),
    )
    assert reply.status_code == 409, reply.text
    assert env[2].get("/api/csv-dag/runs/" + old["run_id"] + "/status").status_code == 200
    assert raw_history_hashes(env[0], names) == before
    # A fresh current proof chain is required, without rewriting the previous Run.
    _, _, _, _, rel = release(env)
    i = create(env, rel)
    a, _ = enqueue(env, i, rel)
    work(env, a)
    assert instances.inspect_job(env[0], env[3], a["run_id"], limits(env))["output"]["sum"] == "15"
    with env[0].engine.connect() as c:
        old_now = c.execute(select(runs).where(runs.c.id == old["run_id"])).mappings().one()
        assert old_now["status"] == "SUCCEEDED" and old_now["result"] == old["proof"]["result"]
    (tmp_path / "upgrade-proof.json").write_text(
        json.dumps(
            dict(
                old_sha="67c6ccc8ad7d6f132205c2ac4f33b10defca5da7",
                old_module_sha256=old["old_module_sha256"],
                old_run_id=old["run_id"],
                old_source_rejected=reply.status_code,
                old_rows_unchanged_on_failed_upgrade=True,
                new_run_id=a["run_id"],
                new_result_sum="15",
                model_requests=0,
            ),
            indent=2,
        )
        + "\n"
    )


@pytest.mark.parametrize("finished", [False, True])
def test_independent_acceptance_detects_shared_join_or_result_deletion(env, finished):
    _, _, _, _, rel = release(env)
    i = create(env, rel)
    a, _ = enqueue(env, i, rel)
    if finished:
        work(env, a)
    with env[0].tx() as c:
        c.execute(
            delete(internal_instance_data).where(internal_instance_data.c.run_id == a["app_run_id"])
        )
        c.execute(
            delete(internal_run_bindings).where(internal_run_bindings.c.run_id == a["run_id"])
        )
        c.execute(delete(internal_app_runs).where(internal_app_runs.c.id == a["app_run_id"]))
        # Even a forged data_version cannot conceal the independent accepted Run seal.
        c.execute(
            update(internal_instances)
            .where(internal_instances.c.id == i["id"])
            .values(data_version=0)
        )
    assert env[2].get("/api/internal/instances/" + i["id"]).status_code == 409


def test_dag_instance_application_role_and_no_new_principal_or_grant(env, runtime_role):
    from dataclasses import replace

    from fastapi.testclient import TestClient
    from sqlalchemy import func, text

    from sim2act.api import create_app
    from sim2act.db import principals

    store = Store(runtime_role, test_only=True)
    settings = replace(env[1], database_url=runtime_role)
    client = TestClient(create_app(store, settings))
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    role_env = (store, settings, client, *env[3:])
    try:
        _, _, _, _, rel = release(role_env)
        i = create(role_env, rel)
        with store.engine.connect() as c:
            before = [
                c.execute(select(func.count()).select_from(t)).scalar_one()
                for t in [principals, grants]
            ]
            assert c.execute(
                text(
                    "SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user"
                )
            ).one() == (False, False, False)
        a, _ = enqueue(role_env, i, rel)
        work(role_env, a)
        assert (
            instances.inspect_job(store, env[3], a["run_id"], limits(role_env))["output"]["sum"]
            == "15"
        )
        with store.engine.connect() as c:
            assert before == [
                c.execute(select(func.count()).select_from(t)).scalar_one()
                for t in [principals, grants]
            ]
    finally:
        client.close()
        store.engine.dispose()


def test_joint_pair_marker_and_join_deletion_cannot_hide_actual_accepted_event(env):
    from sim2act.db import delivery_graph_requests

    _, _, _, _, rel = release(env)
    i = create(env, rel)
    a, _ = enqueue(env, i, rel)
    work(env, a)
    with env[0].tx() as c:
        rows = (
            c.execute(
                select(delivery_graph_requests).where(
                    delivery_graph_requests.c.app_id == i["source_app_id"],
                    delivery_graph_requests.c.kind.in_(["csv_dag_run", "csv_dag_run_seal"]),
                )
            )
            .mappings()
            .all()
        )
        for row in rows:
            if row["snapshot"]["response"].get("run_id") == a["run_id"]:
                value = copy.deepcopy(row["snapshot"])
                value["response"].pop("internal_instance")
                c.execute(
                    update(delivery_graph_requests)
                    .where(
                        delivery_graph_requests.c.app_id == row["app_id"],
                        delivery_graph_requests.c.principal_id == row["principal_id"],
                        delivery_graph_requests.c.kind == row["kind"],
                        delivery_graph_requests.c.request_key == row["request_key"],
                    )
                    .values(snapshot=value, fingerprint=fingerprint(value))
                )
        c.execute(
            delete(internal_instance_data).where(internal_instance_data.c.run_id == a["app_run_id"])
        )
        c.execute(
            delete(internal_run_bindings).where(internal_run_bindings.c.run_id == a["run_id"])
        )
        c.execute(delete(internal_app_runs).where(internal_app_runs.c.id == a["app_run_id"]))
        c.execute(
            update(internal_instances)
            .where(internal_instances.c.id == i["id"])
            .values(data_version=0)
        )
    before = fingerprint(snapshot(env))
    assert env[2].get("/api/internal/instances/" + i["id"]).status_code == 409
    assert env[2].get("/api/runs/" + a["run_id"]).status_code == 409
    assert fingerprint(snapshot(env)) == before
