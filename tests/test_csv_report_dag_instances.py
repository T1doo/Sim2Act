"""Three actual operations, preserved report sink and unchanged typed ledger contract."""

import copy
import hashlib

import pytest
from sqlalchemy import delete, event, select, update
from test_csv_dag import NoModel
from test_csv_dag_instances import create, enqueue, release, setup, work
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits

from sim2act import csv_dag as dag
from sim2act import csv_dag_instances as adapter
from sim2act.db import (
    fingerprint,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_run_bindings,
    operations,
    resources,
    runs,
)
from sim2act.errors import DomainError
from sim2act.worker import Worker


def test_completed_report_flow_reexecutes_two_cold_columns_and_preserves_full_proofs(env):
    _, rid, plan, source, rel = release(env, with_report=True)
    execution = rel["snapshot"]["execution_source"]
    assert execution["version"] == adapter.REPORT_VERSION
    assert execution["report_step"] == "formatted" and len(execution["receipt_fingerprints"]) == 3
    assert plan["composition"]["sinks"] == ["formatted"]
    i = create(env, rel)
    result_ids = []
    for n, (column, total) in enumerate((("quantity", "15"), ("amount", "30")), 1):
        accepted, body = enqueue(env, i, rel, column, column)
        assert accepted["execution_version"] == adapter.REPORT_VERSION
        queued = env[2].get(f"/api/internal/instances/{i['id']}/runs/{accepted['run_id']}")
        assert queued.status_code == 200 and queued.json()["output"] is None
        work(env, accepted)
        reply = env[2].get(f"/api/internal/instances/{i['id']}/runs/{accepted['run_id']}")
        assert reply.status_code == 200, reply.text
        value = reply.json()
        assert value["status"] == "SUCCEEDED" and value["result_version"] == n
        assert value["output"]["sum"] == total and value["output"]["column"] == column
        assert value["output"]["resource_id"] == rid and set(value["output"]) == {
            "resource_id", "column", "count", "sum", "source_hash"}
        proof = value["proof"]
        assert proof["model_requests"] == 0 and proof["business_writes"] == 1
        assert len(proof["steps"]) == 3 and all(p["status"] == "VERIFIED" for p in proof["steps"])
        assert proof["steps"][2]["predecessor_receipts"] == [fingerprint(proof["steps"][1])]
        assert proof["steps"][2]["actual_reads"] == []
        assert proof["result"]["output_by_step"] == {"formatted": {
            **value["output"], "text": f"列 {column}；行数 2；合计 {total}"}}
        assert accepted["run_id"] != source["id"] and proof["plan_fingerprint"] != plan["plan_fingerprint"]
        repeat = env[2].post(f"/api/internal/instances/{i['id']}/runs", json=body)
        assert repeat.status_code == 202 and repeat.json()["cached"]
        assert repeat.json()["run_id"] == accepted["run_id"]
        result_ids.append(accepted["run_id"])
    before = fingerprint(snapshot(env))
    cold = env[2].get("/api/internal/instances/" + i["id"]).json()
    assert cold["data_version"] == 2 and len(cold["runs"]) == 2
    assert fingerprint(snapshot(env)) == before
    with env[0].engine.connect() as c:
        assert len(c.execute(select(operations).where(operations.c.run_id.in_(result_ids))).all()) == 6


@pytest.mark.parametrize("attack", ["grant", "source", "instance-aba", "binding-delete", "report-receipt"])
def test_changed_authority_or_third_receipt_never_appends_typed_result(env, attack):
    _, rid, _, _, rel = release(env, with_report=True)
    i = create(env, rel)
    accepted, _ = enqueue(env, i, rel)
    w = Worker(env[0], env[1], NoModel())
    job = env[0].claim(w.id, env[1].lease_seconds)
    assert job["id"] == accepted["run_id"]
    # Finish all three operations; the typed write is still in the final transaction.
    assert all(dag.advance(w, job) for _ in range(3))
    with env[0].tx() as c:
        if attack == "grant":
            c.execute(update(grants).where(grants.c.resource_id == rid).values(revoked=True))
        elif attack == "source":
            c.execute(update(resources).where(resources.c.id == rid).values(
                content="bad", hash=hashlib.sha256(b"bad").hexdigest()))
        elif attack == "instance-aba":
            c.execute(update(internal_instances).where(internal_instances.c.id == i["id"]).values(revision=3))
        elif attack == "binding-delete":
            c.execute(delete(internal_run_bindings).where(internal_run_bindings.c.run_id == job["id"]))
        else:
            op = c.execute(select(operations).where(operations.c.run_id == job["id"],
                operations.c.call_id == "formatted")).mappings().one()
            receipt = copy.deepcopy(op["receipt"])
            receipt["data"]["text"] = "forged report"
            receipt["output_fingerprint"] = fingerprint(receipt["data"])
            c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=receipt))
    w.process(job)
    with env[0].engine.connect() as c:
        saved = c.execute(select(runs).where(runs.c.id == job["id"])).mappings().one()
        assert saved["status"] in {"FAILED", "WAITING_RESOURCE"} and saved["result"] is None
        assert not c.execute(select(internal_instance_data).where(
            internal_instance_data.c.instance_id == i["id"])).first()
        assert c.execute(select(internal_instances.c.data_version).where(
            internal_instances.c.id == i["id"])).scalar_one() == 0


def test_report_terminal_failure_rolls_back_the_actual_typed_append(env):
    _, _, _, _, rel = release(env, with_report=True)
    i = create(env, rel)
    accepted, _ = enqueue(env, i, rel)
    w = Worker(env[0], env[1], NoModel())
    job = env[0].claim(w.id, env[1].lease_seconds)
    assert all(dag.advance(w, job) for _ in range(3))

    def fail(conn, cursor, statement, parameters, context, executemany):
        if context.compiled and context.compiled.statement.is_update and context.compiled.statement.table is runs and context.compiled.params.get("status") == "SUCCEEDED":
            raise RuntimeError("owned report terminal failure")

    event.listen(env[0].engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="owned report terminal failure"):
            dag.advance(w, job)
    finally:
        event.remove(env[0].engine, "before_cursor_execute", fail)
    with env[0].engine.connect() as c:
        assert not c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == i["id"])).first()
        assert c.execute(select(internal_app_runs.c.status).where(internal_app_runs.c.id == accepted["app_run_id"])).scalar_one() == "QUEUED"
        assert c.execute(select(internal_instances.c.data_version).where(internal_instances.c.id == i["id"])).scalar_one() == 0
    assert dag.advance(w, job) is False
    assert adapter.inspect_job(env[0], env[3], job["id"], limits(env))["result_version"] == 1


@pytest.mark.parametrize("change", ["old-version", "unknown-version", "missing-report-step", "missing-third-receipt"])
def test_source_shape_cannot_be_relabelled_or_partially_frozen(env, change):
    _, _, _, _, rel = release(env, with_report=True)
    snap = copy.deepcopy(rel["snapshot"])
    e = snap["execution_source"]
    if change == "old-version":
        e["version"] = adapter.VERSION
    elif change == "unknown-version":
        e["version"] = "internal.csv-read-sum-report.v2"
    elif change == "missing-report-step":
        e.pop("report_step")
    else:
        e["receipt_fingerprints"].pop()
    before = fingerprint(snapshot(env))
    with env[0].tx() as c, pytest.raises(DomainError):
        adapter.validate_snapshot(env[0], c, env[3], snap, limits(env))
    assert fingerprint(snapshot(env)) == before


@pytest.mark.parametrize("shape", ["extra-edge", "conditional"])
def test_successful_broader_composition_cannot_acquire_the_closed_report_version(env, shape):
    aid, _, original, _, _ = setup(env, with_report=True)
    composition = copy.deepcopy(original["composition"]["definition"])
    if shape == "extra-edge":
        composition["nodes"][2]["depends_on"] = ["read", "total"]
    else:
        composition["nodes"][2]["when"] = dict(op="eq",
            source=dict(source="step", ref="total", field="count"), value=2)
    base = f"/api/projects/{env[5]}/apps/{aid}/csv-dag"
    reply = env[2].post(base, json=dict(expected_candidate_fingerprint=original["candidate_fingerprint"],
        expected_graph_fingerprint=original["graph_fingerprint"], column="amount",
        request_key="broader", composition=composition))
    assert reply.status_code == 201, reply.text
    plan = reply.json()
    accepted = env[2].post(base + "/broader/runs", json=dict(expected_plan_fingerprint=plan["plan_fingerprint"],
        consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key="broader-run"))
    assert accepted.status_code == 202, accepted.text
    w = Worker(env[0], env[1], NoModel())
    job = env[0].claim(w.id, env[1].lease_seconds)
    w.process(job)
    assert dag.inspect_job(env[0], env[3], job["id"], limits(env))["status"] == "SUCCEEDED"
    before = fingerprint(snapshot(env))
    denied = env[2].post(f"/api/csv-dag/runs/{job['id']}/release-approvals",
        json=dict(expected_plan_fingerprint=plan["plan_fingerprint"], request_key="closed-only"))
    assert denied.status_code == 409, denied.text
    assert fingerprint(snapshot(env)) == before


def test_actual_f13_upgrade_preserves_old_rows_and_requires_fresh_source(env, tmp_path):
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    from test_csv_dag_upgrade import raw_history_hashes

    value = os.environ.get("SIM2ACT_REPORT_DAG_OLD_ARCHIVE")
    if not value:
        pytest.skip("Requires explicitly prepared actual f13 source archive")
    archive = Path(value)
    old_module = archive / "src/sim2act/csv_dag_instances.py"
    assert hashlib.sha256(old_module.read_bytes()).hexdigest() == os.environ["SIM2ACT_REPORT_DAG_OLD_MODULE_SHA256"]
    assert old_module.read_bytes() != Path(adapter.__file__).read_bytes()
    output = tmp_path / "old-f13-result.json"
    body = dict(database_url=env[1].database_url,
        schema=env[0].engine.get_execution_options().get("schema_translate_map", {}).get(None),
        data_root=str(tmp_path), owner=env[3], other=env[4], project=env[5],
        resource=env[6], output=str(output))
    driver = Path(__file__).with_name("fixtures") / "csv_report_dag_upgrade.py"
    child = subprocess.run([sys.executable, str(driver.resolve())], cwd=archive,
        env={**os.environ, "PYTHONPATH": str(archive / "src") + os.pathsep + str(archive / "tests"), "LIVE": "0"},
        input=json.dumps(body), text=True, capture_output=True, timeout=60)
    (tmp_path / "old-f13-driver.log").write_text(child.stdout + child.stderr)
    assert child.returncode == 0, child.stdout + child.stderr
    old = json.loads(output.read_text())
    assert Path(old["module_path"]).resolve() == old_module.resolve()
    assert old["module_sha256"] == os.environ["SIM2ACT_REPORT_DAG_OLD_MODULE_SHA256"]
    assert old["result"]["execution_version"] == adapter.VERSION and old["result"]["output"]["sum"] == "15"
    names = list(snapshot(env))
    before = raw_history_hashes(env[0], names)
    i, rel, a = old["instance"], old["release"], old["accepted"]
    read = env[2].get(f"/api/internal/instances/{i['id']}/runs/{a['run_id']}")
    assert read.status_code == 409 and read.json()["error"]["code"] == "VERSION_CONFLICT", read.text
    assert env[2].get("/api/internal/releases/" + rel["id"]).status_code == 409
    assert env[2].get("/api/internal/instances/" + i["id"]).status_code == 409
    assert raw_history_hashes(env[0], names) == before
    _, _, _, _, fresh = release(env, with_report=True)
    new_i = create(env, fresh)
    new, _ = enqueue(env, new_i, fresh, "amount", "after-upgrade")
    work(env, new)
    assert adapter.inspect_job(env[0], env[3], new["run_id"], limits(env))["output"]["sum"] == "30"
    with env[0].engine.connect() as c:
        old_run = c.execute(select(runs).where(runs.c.id == a["run_id"])).mappings().one()
        assert old_run["result"] == old["result"]["proof"]["result"] and old_run["status"] == "SUCCEEDED"
    (tmp_path / "upgrade-proof.json").write_text(json.dumps(dict(old_sha="f13ff8d7661490a7e42a1f7ce3e9179bda54da4b",
        old_module_sha256=old["module_sha256"], old_rows_unchanged_on_refusal=True,
        old_current_readback="VERSION_CONFLICT", fresh_source_required=True,
        old_run_id=a["run_id"], new_run_id=new["run_id"], old_version=adapter.VERSION), indent=2))
