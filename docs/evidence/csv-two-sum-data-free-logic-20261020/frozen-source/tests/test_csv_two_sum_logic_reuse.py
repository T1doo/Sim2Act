"""Explicit dual authority, retired source, actual new target and cold Worker."""

import copy
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select, update
from test_csv_dag import NoModel
from test_csv_dag_instances import create, work
from test_csv_logic_reuse import accept, plan_path, retire_old, revoke_logic
from test_csv_two_sum_instances import check_output, enqueue, release
from test_delivery_graph_apps import snapshot

from sim2act import csv_dag as dag
from sim2act import csv_dag_instances as instances
from sim2act import csv_logic_reuse as logic
from sim2act.api import create_app
from sim2act.db import (
    Store,
    delivery_graph_requests,
    fingerprint,
    grants,
    internal_instance_data,
    runs,
)
from sim2act.worker import Worker

TARGET = "label,net,units\nfresh-A,-4.5,2\nfresh-B,12,7\nfresh-C,1.25,4\n"
COLUMNS = dict(total_a="net", total_b="units")


@pytest.fixture(autouse=True)
def no_model_transport(monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail("Dual logic must not call a model transport")

    for cls in (httpx.HTTPTransport, httpx.AsyncHTTPTransport, httpx.MockTransport):
        for name in ("handle_request", "handle_async_request"):
            if hasattr(cls, name):
                monkeypatch.setattr(cls, name, denied)


def authorize(env, rel, *, consent=logic.TWO_SUM_CONSENT, key="dual-logic"):
    body = dict(expected_release_fingerprint=rel["fingerprint"], consent=consent, request_key=key)
    return env[2].post(
        f"/api/internal/releases/{rel['id']}/csv-logic-authorizations", json=body
    ), body


def setup_logic(env):
    _, old_rid, _, old_job, rel = release(env)
    old_instance = create(env, rel)
    accepted, _ = enqueue(env, old_instance, rel)
    work(env, accepted)
    response, auth = authorize(env, rel)
    assert response.status_code == 201, response.text
    obj = response.json()["logic"]
    client, pid = env[2], env[5]
    resource = client.post(
        f"/api/projects/{pid}/resources",
        json=dict(name="fresh-dual.csv", format="csv", content=TARGET),
    ).json()["id"]
    app = client.post(
        f"/api/projects/{pid}/apps/csv-preview",
        json=dict(name="New target", goal="New results only", resource_id=resource),
    ).json()
    app = client.get(f"/api/apps/{app['id']}").json()
    retire_old(env, old_rid)
    anchor = client.post(
        f"/api/projects/{pid}/apps/{app['id']}/delivery-graph/derive",
        json=dict(expected_candidate_fingerprint=app["fingerprint"], request_key="retired-anchor"),
    ).json()
    body = dict(
        expected_logic_fingerprint=obj["fingerprint"],
        target_app_id=app["id"],
        expected_candidate_fingerprint=app["fingerprint"],
        expected_graph_fingerprint=anchor["graph_fingerprint"],
        expected_resource_id=resource,
        expected_source_hash=app["candidate"]["source_hash"],
        columns=COLUMNS.copy(),
        request_key="fresh-dual-plan",
    )
    return obj, rel, old_rid, old_job, old_instance, app, body, auth


def make_release(env, plan, accepted):
    work(env, accepted)
    proof = env[2].get(f"/api/csv-dag/runs/{accepted['run_id']}")
    assert proof.status_code == 200 and proof.json()["status"] == "SUCCEEDED", proof.text
    response = env[2].post(
        f"/api/csv-dag/runs/{accepted['run_id']}/release-approvals",
        json=dict(
            expected_plan_fingerprint=plan["plan_fingerprint"], request_key="new-dual-release"
        ),
    )
    assert response.status_code == 201, response.text
    a = response.json()
    response = env[2].post(
        f"/api/internal/approvals/{a['id']}/commit", json=dict(fingerprint=a["fingerprint"])
    )
    assert response.status_code == 200, response.text
    return response.json(), proof.json()


def test_authority_retired_source_real_dual_target_cold_swap_and_preserved_history(env, tmp_path):
    obj, rel, old_rid, old_job, old_instance, _, body, auth = setup_logic(env)
    public = json.dumps(obj)
    for value in (
        old_rid,
        old_job["id"],
        rel["id"],
        "amount",
        "quantity",
        "private_audit",
        rel["snapshot"]["execution_source"]["source_hash"],
    ):
        assert value not in public
    assert obj["recipe"] == logic.canonical(instances.TWO_SUM_VERSION)
    assert obj["data_schema"] == logic.result_schema(instances.TWO_SUM_VERSION)
    assert obj["limits"] == rel["snapshot"]["execution_source"]["limits"]
    assert env[2].get(f"/api/internal/releases/{rel['id']}").status_code != 200
    cached = env[2].post(f"/api/internal/releases/{rel['id']}/csv-logic-authorizations", json=auth)
    assert cached.status_code == 201 and cached.json()["cached"] and cached.json()["logic"] == obj
    before = snapshot(env)
    assert authorize(env, rel, key="cannot-mint-after-retirement")[0].status_code != 201
    assert fingerprint(snapshot(env)) == fingerprint(before)
    sql = []

    def watch(conn, cursor, statement, parameters, context, executemany):
        if not statement.lstrip().upper().startswith("SELECT"):
            return
        sql.append(dict(statement=statement, parameters=parameters))
        text, params = statement.lower(), str(parameters)
        assert not ("resources" in text and old_rid in params), statement
        assert not (
            old_job["id"] in params
            and any(v in text for v in ("runs.result", "runs.context", "operations."))
        ), statement

    event.listen(env[0].engine, "before_cursor_execute", watch)
    cold = None
    try:
        options = env[2].get(f"/api/internal/csv-logics/{obj['id']}/materials")
        assert options.status_code == 200, options.text
        assert [v["resource_id"] for v in options.json()["items"]] == [body["expected_resource_id"]]
        plan, accepted = accept(env, obj, body)
        original_node_cap = rel["snapshot"]["execution_source"]["aggregate_nodes"]["total_a"][
            "limits"
        ]
        assert all(
            all(action["limits"][k] <= value for k, value in original_node_cap.items())
            for action in plan["definition"]["actions"]
        )
        assert (
            env[2].post(plan_path(obj), json=body).json()["plan"]["plan_fingerprint"]
            == plan["plan_fingerprint"]
        )
        changed = copy.deepcopy(body)
        changed["columns"]["total_b"] = "net"
        frozen = fingerprint(snapshot(env))
        assert env[2].post(plan_path(obj), json=changed).status_code == 409
        assert fingerprint(snapshot(env)) == frozen
        new, proof = make_release(env, plan, accepted)
        check_output(
            proof["result"]["output_by_step"], TARGET, body["expected_resource_id"], COLUMNS
        )
        assert new["snapshot"]["execution_source"]["default_columns"] == COLUMNS
        instance = create(env, new)
        cold = Store(env[1].database_url, test_only=True)
        cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
        event.listen(cold.engine, "before_cursor_execute", watch)
        with TestClient(create_app(cold, env[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            assert client.get(f"/api/projects/{env[5]}/csv-logics").json()["items"] == [obj]
            swapped = dict(total_a="units", total_b="net")
            response = client.post(
                f"/api/internal/instances/{instance['id']}/runs",
                json=dict(
                    expected_revision=1,
                    expected_release_fingerprint=new["fingerprint"],
                    input={"columns": swapped},
                    request_key="cold-swapped",
                ),
            )
            assert response.status_code == 202, response.text
            rid = response.json()["run_id"]
            assert rid not in (old_job["id"], proof["id"])
            worker = Worker(cold, env[1], NoModel())
            job = cold.claim(worker.id, env[1].lease_seconds)
            assert job["id"] == rid
            worker.process(job)
            response = client.get(f"/api/internal/instances/{instance['id']}")
            assert response.status_code == 200, response.text
            detail = response.json()
            assert detail["data_version"] == 1 and detail["runs"][0]["status"] == "SUCCEEDED"
            check_output(
                detail["data"][0]["data"]["result"], TARGET, body["expected_resource_id"], swapped
            )
            assert detail["runs"][0]["proof"]["model_requests"] == 0
        after = snapshot(env)
        for table in ("principals", "grants", "app_drafts", "resources"):
            assert before[table] == after[table], table
        for table in (
            "internal_releases",
            "internal_instances",
            "internal_instance_data",
            "internal_app_runs",
            "internal_approvals",
        ):
            assert all(row in after[table] for row in before[table]), table
        assert old_instance["id"] != instance["id"]
    finally:
        event.remove(env[0].engine, "before_cursor_execute", watch)
        if cold:
            event.remove(cold.engine, "before_cursor_execute", watch)
            cold.engine.dispose()
    (tmp_path / "source-selects.jsonl").write_text(
        "".join(json.dumps(row, default=str) + "\n" for row in sql)
    )
    (tmp_path / "proof.json").write_text(
        json.dumps(
            dict(
                logic=obj,
                new_release=new,
                target=proof,
                cold_instance=detail,
                original_history_preserved=True,
                source_resource_selects=0,
                source_run_body_or_operations_selects=0,
                model_requests=0,
            ),
            indent=2,
        )
    )


@pytest.mark.parametrize(
    "columns",
    [
        None,
        {},
        {"total_a": "net"},
        {"total_a": "net", "wrong": "units"},
        {"total_a": "net", "total_b": "units", "extra": "net"},
        {"total_a": True, "total_b": "units"},
        {"total_a": "label", "total_b": "units"},
        {"total_a": {"column": "net"}, "total_b": "units"},
    ],
)
def test_dual_input_closed_and_atomic(env, columns):
    obj, _, _, _, _, _, body, _ = setup_logic(env)
    if columns is None:
        body.pop("columns")
        body["column"] = "net"
    else:
        body["columns"] = columns
    before = fingerprint(snapshot(env))
    assert env[2].post(plan_path(obj), json=body).status_code in (400, 409, 422)
    assert fingerprint(snapshot(env)) == before


def test_explicit_dual_consent_required_before_any_authority_write(env):
    _, _, _, _, rel = release(env)
    before = fingerprint(snapshot(env))
    assert authorize(env, rel, consent=logic.CONSENT)[0].status_code == 409
    assert fingerprint(snapshot(env)) == before


def test_authority_joint_request_reseal_cannot_change_dual_consent(env):
    obj, _, _, _, _, _, _, _ = setup_logic(env)
    with env[0].tx() as c:
        rows = (
            c.execute(
                select(delivery_graph_requests).where(
                    delivery_graph_requests.c.kind.in_([logic.AUTH_KIND, logic.AUTH_KIND + "_seal"])
                )
            )
            .mappings()
            .all()
        )
        for row in rows:
            changed = copy.deepcopy(row["snapshot"])
            changed["request"]["consent"] = logic.CONSENT
            c.execute(
                update(delivery_graph_requests)
                .where(
                    delivery_graph_requests.c.kind == row["kind"],
                    delivery_graph_requests.c.request_key == row["request_key"],
                )
                .values(
                    snapshot=changed,
                    fingerprint=fingerprint(changed),
                    request_fingerprint=fingerprint(changed["request"]),
                )
            )
    before = fingerprint(snapshot(env))
    assert env[2].get(f"/api/internal/csv-logics/{obj['id']}").status_code == 409
    assert fingerprint(snapshot(env)) == before


@pytest.mark.parametrize(
    "cause,stage",
    [
        (cause, stage)
        for cause in ["revoke", "expire", "target-grant"]
        for stage in ["queued", "first-sum"]
    ]
    + [("expire", "final-typed")],
)
def test_independent_authority_and_target_gates_prevent_partial_commit(
    env, monkeypatch, cause, stage
):
    obj, _, _, _, _, app, body, _ = setup_logic(env)
    plan, accepted = accept(env, obj, body)
    if stage == "final-typed":
        new, _ = make_release(env, plan, accepted)
        instance = create(env, new)
        accepted, _ = enqueue(env, instance, new, COLUMNS)
    worker = Worker(env[0], env[1], NoModel())
    job = env[0].claim(worker.id, env[1].lease_seconds)

    def deny():
        if cause == "revoke":
            revoke_logic(env, obj)
        elif cause == "expire":
            monkeypatch.setattr(logic, "time", SimpleNamespace(time=lambda: obj["expires_at"] + 1))
        else:
            with env[0].tx() as c:
                c.execute(
                    update(grants)
                    .where(grants.c.principal_id == app["runtime_id"])
                    .values(revoked=True)
                )

    if stage == "first-sum":
        assert dag.advance(worker, job) and dag.advance(worker, job)
    if stage == "final-typed":
        original = instances.commit_result

        def reject_after_write(*args, **kwargs):
            original(*args, **kwargs)
            # Expiry is the in-transaction authority guard; DB revocation uses its own transaction.
            monkeypatch.setattr(logic, "time", SimpleNamespace(time=lambda: obj["expires_at"] + 1))

        monkeypatch.setattr(instances, "commit_result", reject_after_write)
    else:
        deny()
    worker.process(job)
    with env[0].engine.connect() as c:
        saved = c.execute(select(runs).where(runs.c.id == job["id"])).mappings().one()
        assert saved["status"] != "SUCCEEDED" and saved["result"] is None
        assert saved["context"]["tools"] == (
            0 if stage == "queued" else 2 if stage == "first-sum" else 3
        )
        if stage == "final-typed":
            assert not c.execute(
                select(internal_instance_data).where(
                    internal_instance_data.c.instance_id == instance["id"]
                )
            ).first()


@pytest.mark.parametrize("attack", ["owner", "hash", "target-grant", "mixed-input"])
def test_dual_logic_target_current_gate_and_exact_contract_zero_writes(env, attack):
    obj, _, _, _, _, app, body, _ = setup_logic(env)
    if attack == "owner":
        env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    elif attack == "hash":
        body["expected_source_hash"] = "0" * 64
    elif attack == "mixed-input":
        body["column"] = "net"
    else:
        with env[0].tx() as c:
            c.execute(
                update(grants)
                .where(grants.c.principal_id == app["runtime_id"])
                .values(revoked=True)
            )
    before = fingerprint(snapshot(env))
    assert env[2].post(plan_path(obj), json=body).status_code in (400, 403, 409, 422)
    assert fingerprint(snapshot(env)) == before


def test_source_private_node_names_are_normalized_out_of_authority(env, monkeypatch):
    import test_csv_two_sum_instances as source

    original = source.composition()
    names = dict(read="private_reader", total_a="private_sum_one", total_b="private_sum_two")
    for node in original["nodes"]:
        node["step_id"] = names[node["step_id"]]
        node["depends_on"] = [names[v] for v in node["depends_on"]]
        for value in node["inputs"].values():
            if value["source"] == "step":
                value["ref"] = names[value["ref"]]
            elif value["source"] == "input":
                value["field"] = node["step_id"] + "_column"
    monkeypatch.setattr(source, "composition", lambda: copy.deepcopy(original))
    _, _, _, _, rel = source.release(env)
    response, _ = authorize(env, rel)
    assert response.status_code == 201, response.text
    obj = response.json()["logic"]
    assert all(name not in json.dumps(obj) for name in names.values())
    assert obj["recipe"] == logic.canonical(instances.TWO_SUM_VERSION)
    assert obj["data_schema"] == logic.result_schema(instances.TWO_SUM_VERSION)


def test_dual_consent_cannot_implicitly_authorize_single_sum(env):
    from test_csv_dag_instances import release as scalar_release

    _, _, _, _, rel = scalar_release(env)
    before = fingerprint(snapshot(env))
    assert authorize(env, rel)[0].status_code == 409
    assert fingerprint(snapshot(env)) == before


def test_two_logic_sums_may_use_same_target_numeric_column(env):
    obj, _, _, _, _, _, body, _ = setup_logic(env)
    body["columns"] = dict(total_a="net", total_b="net")
    plan, accepted = accept(env, obj, body)
    new, proof = make_release(env, plan, accepted)
    check_output(
        proof["result"]["output_by_step"], TARGET, body["expected_resource_id"], body["columns"]
    )
    assert new["snapshot"]["execution_source"]["default_columns"] == body["columns"]


def test_double_resigned_origin_cannot_change_second_target_column(env):
    obj, _, _, _, _, _, body, _ = setup_logic(env)
    plan, _ = accept(env, obj, body)
    with env[0].tx() as c:
        rows = (
            c.execute(
                select(delivery_graph_requests).where(
                    delivery_graph_requests.c.kind.in_([logic.ORIGIN, logic.ORIGIN + "_seal"])
                )
            )
            .mappings()
            .all()
        )
        for row in rows:
            changed = copy.deepcopy(row["snapshot"])
            changed["response"]["columns"]["total_b"] = "net"
            c.execute(
                update(delivery_graph_requests)
                .where(
                    delivery_graph_requests.c.kind == row["kind"],
                    delivery_graph_requests.c.request_key == row["request_key"],
                )
                .values(snapshot=changed, fingerprint=fingerprint(changed))
            )
    before = fingerprint(snapshot(env))
    response = env[2].get(plan_path(obj) + f"/{body['target_app_id']}/{plan['request_key']}")
    assert response.status_code == 409, response.text
    assert fingerprint(snapshot(env)) == before


def test_derived_instance_recipe_rechecks_second_node_before_any_origin_write(env):
    from sim2act.column_patches import read_pair
    from sim2act.contracts import Limits
    from sim2act.errors import DomainError

    obj, _, _, _, _, _, body, _ = setup_logic(env)
    plan, accepted = accept(env, obj, body)
    new, _ = make_release(env, plan, accepted)
    create(env, new)
    before = fingerprint(snapshot(env))
    with env[0].tx() as c:
        original, source = read_pair(
            c, env[3], body["target_app_id"], "csv_dag_plan", plan["request_key"], dag.PlanInput
        )
        value = original.model_dump(exclude_none=True)
        value["request_key"] = logic.INSTANCE_PREFIX + "f" * 48
        value["composition"]["nodes"][-1]["inputs"]["resource_id"]["ref"] = "total_a"
        with pytest.raises(DomainError):
            logic.prepare_instance_plan(
                env[0],
                c,
                env[3],
                env[5],
                body["target_app_id"],
                source,
                dag.PlanInput(**value),
                Limits(**obj["limits"]),
            )
    assert fingerprint(snapshot(env)) == before


def test_legacy_single_column_invalid_numeric_selection_keeps_original_400(env):
    from test_csv_logic_reuse import setup_logic as scalar_setup

    obj, _, _, _, _, _, body, _ = scalar_setup(env)
    body["column"] = "label"
    before = fingerprint(snapshot(env))
    response = env[2].post(plan_path(obj), json=body)
    assert response.status_code == 400 and "INVALID_INPUT" in response.text, response.text
    assert "Choose a current target numeric column" in response.text
    assert fingerprint(snapshot(env)) == before
