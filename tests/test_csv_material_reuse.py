"""New material uses actual registered plans/worker/receipts and separate history."""

import copy

import pytest
from sqlalchemy import delete, select, update
from test_csv_dag import NoModel
from test_csv_dag_instances import create, enqueue, release, work
from test_delivery_graph_apps import snapshot

from sim2act import csv_material_reuse as material
from sim2act.db import (
    Store,
    delivery_graph_requests,
    fingerprint,
    grants,
    internal_instances,
    internal_releases,
    runs,
)
from sim2act.worker import Worker


def setup_material(env, with_report=True):
    client, pid = env[2], env[5]
    target = client.post(
        f"/api/projects/{pid}/resources",
        json=dict(
            name="new-price.csv",
            format="csv",
            content="label,price,units\nnew-A,7,3\nnew-B,19,8\nnew-C,14,6\n",
        ),
    ).json()["id"]
    made = client.post(
        f"/api/projects/{pid}/apps/csv-preview",
        json=dict(
            name="Existing new-material app", goal="Independent new input", resource_id=target
        ),
    ).json()
    aid = made["id"]
    _, old_resource, _, _, rel = release(env, with_report=with_report)
    old = create(env, rel)
    accepted, _ = enqueue(env, old, rel)
    work(env, accepted)
    app = client.get(f"/api/apps/{aid}").json()
    anchor = client.post(
        f"/api/projects/{pid}/apps/{aid}/delivery-graph/derive",
        json=dict(expected_candidate_fingerprint=app["fingerprint"], request_key="target-anchor"),
    ).json()
    body = dict(
        expected_release_fingerprint=rel["fingerprint"],
        target_app_id=aid,
        expected_candidate_fingerprint=app["fingerprint"],
        expected_graph_fingerprint=anchor["graph_fingerprint"],
        expected_resource_id=target,
        expected_source_hash=app["candidate"]["source_hash"],
        column="price",
        request_key="another-material",
    )
    return rel, old, old_resource, app, body


def path(rel):
    return f"/api/internal/releases/{rel['id']}/csv-material-plans"


def accepted_target(env, rel, body):
    reply = env[2].post(path(rel), json=body)
    assert reply.status_code == 201, reply.text
    value = reply.json()
    plan = value["plan"]
    url = f"/api/projects/{env[5]}/apps/{body['target_app_id']}/csv-dag/{plan['request_key']}/runs"
    confirm = dict(
        expected_plan_fingerprint=plan["plan_fingerprint"],
        consent="CONFIRM_EXACT_OFFLINE_CSV_DAG",
        request_key="target-run",
    )
    reply = env[2].post(url, json=confirm)
    assert reply.status_code == 202, reply.text
    return value, reply.json(), url, confirm


@pytest.mark.parametrize("with_report", [False, True])
def test_cold_new_material_actual_new_source_release_instance_and_preserved_old_rows(
    env, with_report
):
    from fastapi.testclient import TestClient

    from sim2act.api import create_app

    rel, old, old_rid, target, body = setup_material(env, with_report)
    before = snapshot(env)
    options = env[2].get(f"/api/internal/releases/{rel['id']}/csv-materials")
    assert options.status_code == 200 and [v["resource_id"] for v in options.json()["items"]] == [
        body["expected_resource_id"]
    ]
    assert fingerprint(snapshot(env)) == fingerprint(before)
    value, accepted, url, confirm = accepted_target(env, rel, body)
    assert value["binding"]["limits"] == rel["snapshot"]["execution_source"]["limits"]
    assert (
        value["plan"]["definition"]["manifest"]["data_bindings"][0]["resource_ref"]
        == body["expected_resource_id"]
    )
    assert (
        env[2].post(path(rel), json=body).json()["plan"]["plan_fingerprint"]
        == value["plan"]["plan_fingerprint"]
    )
    assert env[2].post(url, json=confirm).json()["run_id"] == accepted["run_id"]
    w = Worker(env[0], env[1], NoModel())
    job = env[0].claim(w.id, env[1].lease_seconds)
    assert job["id"] == accepted["run_id"]
    w.process(job)
    proof = env[2].get(f"/api/csv-dag/runs/{job['id']}")
    assert proof.status_code == 200, proof.text
    proof = proof.json()
    assert proof["status"] == "SUCCEEDED" and len(proof["steps"]) == (3 if with_report else 2)
    output = next(iter(proof["result"]["output_by_step"].values()))
    assert output["resource_id"] == body["expected_resource_id"] != old_rid
    assert (
        output["source_hash"] == body["expected_source_hash"]
        and output["count"] == 3
        and output["sum"] == "40"
    )
    if with_report:
        assert output["text"] == "列 price；行数 3；合计 40"
    p = env[2].post(
        f"/api/csv-dag/runs/{job['id']}/release-approvals",
        json=dict(
            expected_plan_fingerprint=value["plan"]["plan_fingerprint"],
            request_key="target-release",
        ),
    )
    assert p.status_code == 201, p.text
    a = p.json()
    new = (
        env[2]
        .post(f"/api/internal/approvals/{a['id']}/commit", json=dict(fingerprint=a["fingerprint"]))
        .json()
    )
    i = create(env, new)
    cold = Store(env[1].database_url, test_only=True)
    if not cold.sqlite:
        cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    try:
        client = TestClient(create_app(cold, env[1]))
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        assert client.get(f"/api/internal/instances/{i['id']}").status_code == 200
        accepted = client.post(
            f"/api/internal/instances/{i['id']}/runs",
            json=dict(
                expected_revision=1,
                expected_release_fingerprint=new["fingerprint"],
                input={"column": "units"},
                request_key="cold-new-result",
            ),
        )
        assert accepted.status_code == 202, accepted.text
        worker = Worker(cold, env[1], NoModel())
        queued = cold.claim(worker.id, env[1].lease_seconds)
        worker.process(queued)
        detail = client.get(f"/api/internal/instances/{i['id']}")
        assert detail.status_code == 200, detail.text
        actual = detail.json()["data"][0]["data"]["result"]
        assert (
            actual["resource_id"] == body["expected_resource_id"]
            and actual["column"] == "units"
            and actual["sum"] == "17"
            and actual["count"] == 3
        )
        client.close()
    finally:
        cold.engine.dispose()
    after = snapshot(env)
    for name in ("principals", "grants", "app_drafts", "resources"):
        assert fingerprint(before[name]) == fingerprint(after[name]), name
    for table, key in ((internal_instances, old["id"]), (internal_releases, rel["id"])):
        with env[0].engine.connect() as c:
            saved = dict(c.execute(select(table).where(table.c.id == key)).mappings().one())
        assert saved == next(v for v in before[table.name] if v["id"] == key)
    assert (
        env[2]
        .get(f"/api/internal/instances/{old['id']}")
        .json()["data"][0]["data"]["result"]["sum"]
        == "15"
    )


@pytest.mark.parametrize(
    "attack", ["column", "resource", "hash", "version", "runtime-grant", "bytes"]
)
def test_new_material_rejects_changed_binding_before_any_write(env, attack):
    rel, _, _, target, body = setup_material(env)
    body = copy.deepcopy(body)
    if attack == "column":
        body["column"] = "label"
    elif attack == "resource":
        body["expected_resource_id"] = "res_" + "0" * 32
    elif attack == "hash":
        body["expected_source_hash"] = "0" * 64
    elif attack == "version":
        body["expected_candidate_fingerprint"] = "0" * 64
    else:
        with env[0].tx() as c:
            if attack == "runtime-grant":
                c.execute(
                    update(grants)
                    .where(
                        grants.c.principal_id == target["runtime_id"],
                        grants.c.resource_id == body["expected_resource_id"],
                    )
                    .values(revoked=True)
                )
            else:
                from sim2act.db import resources

                c.execute(
                    update(resources)
                    .where(resources.c.id == body["expected_resource_id"])
                    .values(content="price\n999\n")
                )
    before = fingerprint(snapshot(env))
    reply = env[2].post(path(rel), json=body)
    assert reply.status_code in {400, 403, 409}, reply.text
    assert fingerprint(snapshot(env)) == before


def test_material_origin_pair_deletion_cannot_downgrade_accepted_target_run(env):
    rel, _, _, _, body = setup_material(env)
    value, accepted, _, _ = accepted_target(env, rel, body)
    with env[0].tx() as c:
        c.execute(
            delete(delivery_graph_requests).where(
                delivery_graph_requests.c.app_id == body["target_app_id"],
                delivery_graph_requests.c.kind.in_([material.KIND, material.KIND + "_seal"]),
            )
        )
    before = fingerprint(snapshot(env))
    reply = env[2].get(f"/api/csv-dag/runs/{accepted['run_id']}")
    assert reply.status_code == 409, reply.text
    assert fingerprint(snapshot(env)) == before


def test_target_revocation_between_real_steps_preserves_only_read_receipt(env):
    rel, old, _, target, body = setup_material(env)
    _, accepted, _, _ = accepted_target(env, rel, body)
    worker = Worker(env[0], env[1], NoModel())
    job = env[0].claim(worker.id, env[1].lease_seconds)
    from sim2act import csv_dag as dag

    assert dag.advance(worker, job)
    with env[0].tx() as c:
        c.execute(
            update(grants)
            .where(
                grants.c.principal_id == target["runtime_id"],
                grants.c.resource_id == body["expected_resource_id"],
            )
            .values(revoked=True)
        )
    worker.process(job)
    with env[0].engine.connect() as c:
        saved = c.execute(select(runs).where(runs.c.id == job["id"])).mappings().one()
        assert (
            saved["status"] == "WAITING_RESOURCE"
            and saved["result"] is None
            and saved["context"]["tools"] == 1
        )
    assert env[2].get(f"/api/internal/instances/{old['id']}").status_code == 200


@pytest.mark.parametrize(
    "attack", ["column", "target", "source-grant", "target-version", "owner", "budget"]
)
def test_complete_intent_current_authority_and_budget_reject_zero_write(env, attack):
    from test_internal_lifecycle import limits

    from sim2act.contracts import Limits
    from sim2act.db import app_drafts
    from sim2act.errors import DomainError

    rel, old, _, target, body = setup_material(env)
    if attack in {"column", "target"}:
        first = env[2].post(path(rel), json=body)
        assert first.status_code == 201, first.text
        body = copy.deepcopy(body)
        if attack == "column":
            body["column"] = "units"
        else:
            body["target_app_id"] = rel["snapshot"]["draft"]["id"]
    elif attack == "source-grant":
        with env[0].tx() as c:
            c.execute(
                update(grants)
                .where(grants.c.principal_id == rel["snapshot"]["draft"]["runtime_id"])
                .values(revoked=True)
            )
    elif attack == "target-version":
        candidate = copy.deepcopy(target["candidate"])
        candidate["goal"]["known"] += " changed"
        with env[0].tx() as c:
            c.execute(
                update(app_drafts)
                .where(app_drafts.c.id == target["id"])
                .values(candidate=candidate, fingerprint=fingerprint(candidate))
            )
    elif attack == "owner":
        env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    before = fingerprint(snapshot(env))
    if attack == "budget":
        cap = limits(env).model_dump()
        cap["max_tool_calls"] = 2
        with pytest.raises(DomainError):
            material.propose(
                env[0], env[3], rel["id"], material.MaterialInput(**body), Limits(**cap)
            )
    else:
        reply = env[2].post(path(rel), json=body)
        assert reply.status_code in {400, 403, 409}, reply.text
    assert fingerprint(snapshot(env)) == before
    if attack != "owner":
        reply = env[2].post(
            f"/api/internal/instances/{old['id']}/runs",
            json=dict(
                expected_revision=1,
                expected_release_fingerprint=rel["fingerprint"],
                input={"column": "price", "resource_id": body["expected_resource_id"]},
                request_key="old-cannot-rebind",
            ),
        )
        assert reply.status_code in {400, 403, 409}, reply.text
        assert fingerprint(snapshot(env)) == before


@pytest.mark.parametrize("attack", ["one-seal", "both-seals", "joint-column", "joint-target"])
def test_material_origin_reconstructs_real_source_and_target_not_just_joint_hashes(env, attack):
    rel, _, _, _, body = setup_material(env)
    value, accepted, _, _ = accepted_target(env, rel, body)
    key = value["plan"]["request_key"]
    with env[0].tx() as c:
        if attack.endswith("seals") or attack == "one-seal":
            kinds = (
                [material.KIND + "_seal"]
                if attack == "one-seal"
                else [material.KIND, material.KIND + "_seal"]
            )
            c.execute(
                delete(delivery_graph_requests).where(
                    delivery_graph_requests.c.app_id == body["target_app_id"],
                    delivery_graph_requests.c.kind.in_(kinds),
                )
            )
        else:
            saved = (
                c.execute(
                    select(delivery_graph_requests).where(
                        delivery_graph_requests.c.app_id == body["target_app_id"],
                        delivery_graph_requests.c.kind == material.KIND,
                        delivery_graph_requests.c.request_key == key,
                    )
                )
                .mappings()
                .one()
            )
            changed = copy.deepcopy(saved["snapshot"])
            if attack == "joint-column":
                changed["response"]["column"] = "units"
            else:
                changed["response"]["target"]["resource_id"] = "res_" + "0" * 32
            c.execute(
                update(delivery_graph_requests)
                .where(
                    delivery_graph_requests.c.app_id == body["target_app_id"],
                    delivery_graph_requests.c.kind.in_([material.KIND, material.KIND + "_seal"]),
                    delivery_graph_requests.c.request_key == key,
                )
                .values(snapshot=changed, fingerprint=fingerprint(changed))
            )
    before = fingerprint(snapshot(env))
    for url in [
        f"{path(rel)}/{body['target_app_id']}/{key}",
        f"/api/csv-dag/runs/{accepted['run_id']}",
    ]:
        reply = env[2].get(url)
        assert reply.status_code == 409, reply.text
        assert fingerprint(snapshot(env)) == before


def test_reserved_material_key_cannot_strip_origin_and_plan_marker(env):
    rel, _, _, _, body = setup_material(env)
    value = env[2].post(path(rel), json=body).json()
    key = value["plan"]["request_key"]
    with env[0].tx() as c:
        c.execute(
            delete(delivery_graph_requests).where(
                delivery_graph_requests.c.app_id == body["target_app_id"],
                delivery_graph_requests.c.kind.in_([material.KIND, material.KIND + "_seal"]),
            )
        )
        saved = (
            c.execute(
                select(delivery_graph_requests).where(
                    delivery_graph_requests.c.app_id == body["target_app_id"],
                    delivery_graph_requests.c.kind == "csv_dag_plan",
                    delivery_graph_requests.c.request_key == key,
                )
            )
            .mappings()
            .one()
        )
        changed = copy.deepcopy(saved["snapshot"])
        plan = changed["response"]
        del plan["material_reuse"]
        del plan["plan_fingerprint"]
        plan["plan_fingerprint"] = fingerprint(plan)
        c.execute(
            update(delivery_graph_requests)
            .where(
                delivery_graph_requests.c.app_id == body["target_app_id"],
                delivery_graph_requests.c.kind.in_(["csv_dag_plan", "csv_dag_plan_seal"]),
                delivery_graph_requests.c.request_key == key,
            )
            .values(snapshot=changed, fingerprint=fingerprint(changed))
        )
    before = fingerprint(snapshot(env))
    base = f"/api/projects/{env[5]}/apps/{body['target_app_id']}/csv-dag/{key}"
    reply = env[2].get(base)
    assert reply.status_code == 409, reply.text
    reply = env[2].post(
        base + "/runs",
        json=dict(
            expected_plan_fingerprint=plan["plan_fingerprint"],
            consent="CONFIRM_EXACT_OFFLINE_CSV_DAG",
            request_key="cannot-downgrade",
        ),
    )
    assert reply.status_code == 409, reply.text
    assert fingerprint(snapshot(env)) == before


def test_actual_50b_source_upgrade_preserves_old_raw_history_and_requires_fresh_source(
    env, tmp_path
):
    from test_csv_dag_upgrade import (
        test_actual_old_source_upgrade_retains_history_and_requires_new_exact_confirmation,
    )

    test_actual_old_source_upgrade_retains_history_and_requires_new_exact_confirmation(
        env,
        tmp_path,
        "SIM2ACT_MATERIAL_OLD_ARCHIVE",
        "50b10417a99a070f6bcd614471cc00ec102b7836",
        "28c710a19e12070b787b1fcb2215547496d82cd99254dd9b5b74f27432ab140b",
    )
