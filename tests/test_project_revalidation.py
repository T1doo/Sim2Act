"""Actual PROJECT checks, immutable old plans and strict no-write rejection."""

import copy
import hashlib
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select, update
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits
from test_report_presentations import env as env
from test_report_presentations import prepared

from sim2act import project_revalidation as checks
from sim2act.db import Store, app_drafts, fingerprint, grants, resources
from sim2act.db import delivery_graph_requests as requests


def setup(env, tmp_path):
    content = "item,amount,quantity\na,1.25,7\nb,2.75,8\n"
    with env[0].tx() as c:
        c.execute(
            update(resources)
            .where(resources.c.project_id == env[5], resources.c.format == "csv")
            .values(content=content, hash=hashlib.sha256(content.encode()).hexdigest())
        )
    app, _, presentation, _, _, wires = prepared(env, tmp_path, peer=True)
    base = presentation.removesuffix("report-presentations") + "scope-checks"
    options = env[2].get(base + "/options", params={"plan_key": "presentation-plan"})
    assert options.status_code == 200, options.text
    options = options.json()
    selections = []
    for item in options["applications"]:
        if not item["supported"]:
            continue
        value = dict(
            app_id=item["app_id"],
            kind=item["kind"],
            expected_graph_fingerprint=item["binding"]["graph_fingerprint"],
        )
        if item["kind"] == "CSV":
            value["input"] = {"column": "quantity"}
        else:
            run = item["runs"][0]
            value.update(
                run_id=run["run_id"],
                expected_run_version=run["version"],
                expected_run_fence=run["fence"],
                expected_result_fingerprint=run["result_fingerprint"],
            )
        selections.append(value)
    body = dict(
        plan_key="presentation-plan",
        expected_plan_fingerprint=options["plan_fingerprint"],
        expected_options_fingerprint=options["options_fingerprint"],
        selections=selections,
        consent=checks.CONSENT,
        request_key="actual-project-check",
    )
    return app, base, options, body, wires


def test_actual_project_csv_independent_sum_and_report_rules_keep_old_jobs(env, tmp_path):
    _, base, options, body, wires = setup(env, tmp_path)
    before = snapshot(env)
    accepted = env[2].post(base, json=body)
    assert accepted.status_code == 201, accepted.text
    value = accepted.json()
    assert value["deterministic_status"] == "PARTIAL"
    assert value["executed_checks_status"] == "PASS"
    assert value["project_revalidation_status"] == "BLOCKED_PARTIAL"
    assert value["project_revalidation_completed"] is False
    assert value["overall_run_acceptance"] == "NOT_ACCEPTED"
    assert value["omissions"] == options["omissions"] and value["omissions"]
    actual = [item["actual"] for item in value["applications"]]
    csv = next(v for v in actual if "output" in v)
    report = next(v for v in actual if "archived_run" in v)
    assert csv["output"]["column"] == "quantity" and csv["output"]["sum"] == "15"
    assert all(v["status"] == "PASS" for v in csv["checks"])
    assert report["archived_run"]["checks"]["check_status"] == "PASS"
    assert report["explanation_status"] == "NOT_CHECKED"
    assert (
        next(v for v in value["global_invariants"] if v["id"] == "dependency_completeness")[
            "status"
        ]
        == "BLOCKED_UNKNOWN"
    )
    assert all(
        v["status"] == "PASS" for item in value["applications"] for v in item["declared_checks"]
    )
    after = snapshot(env)
    for table in before:
        if table != "delivery_graph_requests":
            assert before[table] == after[table], table
    assert len(after["delivery_graph_requests"]) == len(before["delivery_graph_requests"]) + 2
    assert len(wires) == 4
    for method in ("post", "get"):
        response = (
            env[2].post(base, json=body)
            if method == "post"
            else env[2].get(base + "/" + body["request_key"])
        )
        assert response.status_code in (200, 201) and response.json()["cached"], response.text
        assert response.json()["check_fingerprint"] == value["check_fingerprint"]
        assert snapshot(env) == after


@pytest.mark.parametrize(
    "change",
    [
        "consent",
        "missing",
        "duplicate",
        "options",
        "plan",
        "graph",
        "run_version",
        "foreign_run",
        "gold",
        "column",
        "invalid_unicode_key",
    ],
)
def test_bad_project_selection_never_writes(env, tmp_path, change):
    _, base, _, body, _ = setup(env, tmp_path)
    changed = copy.deepcopy(body)
    report = next(v for v in changed["selections"] if v["kind"] == "REPORT")
    csv = next(v for v in changed["selections"] if v["kind"] == "CSV")
    if change == "consent":
        changed["consent"] = "auto"
    elif change == "missing":
        changed["selections"].pop()
    elif change == "duplicate":
        changed["selections"].append(copy.deepcopy(csv))
    elif change in ("options", "plan"):
        changed["expected_" + change + "_fingerprint"] = "0" * 64
    elif change == "graph":
        csv["expected_graph_fingerprint"] = "0" * 64
    elif change == "run_version":
        report["expected_run_version"] = True
    elif change == "foreign_run":
        report["run_id"] = "run_" + "f" * 32
    elif change == "gold":
        csv["expected_sum"] = "15"
    elif change == "invalid_unicode_key":
        changed["request_key"] = "bad\ud800"
    else:
        csv["input"]["column"] = "missing"
    before = snapshot(env)
    response = env[2].post(base, json=changed)
    assert response.status_code in (400, 409, 422), response.text
    assert snapshot(env) == before


@pytest.mark.parametrize("change", ["grant", "source", "seal", "response"])
def test_project_current_source_and_independent_seal_gate(env, tmp_path, change):
    _, base, _, body, _ = setup(env, tmp_path)
    accepted = env[2].post(base, json=body)
    assert accepted.status_code == 201, accepted.text
    with env[0].tx() as c:
        if change == "grant":
            c.execute(
                update(grants)
                .where(grants.c.project_id == env[5], grants.c.tool_ref == "resource.read")
                .values(revoked=True)
            )
        elif change == "source":
            c.execute(
                update(resources)
                .where(resources.c.project_id == env[5], resources.c.format == "csv")
                .values(content="changed")
            )
        else:
            row = (
                c.execute(
                    select(requests).where(
                        requests.c.kind == checks.KIND,
                        requests.c.request_key == body["request_key"],
                    )
                )
                .mappings()
                .one()
            )
            value = copy.deepcopy(row["snapshot"])
            value["response"]["deterministic_status"] = "FAIL"
            c.execute(
                update(requests)
                .where(
                    requests.c.app_id == row["app_id"],
                    requests.c.kind == checks.KIND,
                    requests.c.request_key == body["request_key"],
                )
                .values(snapshot=value, fingerprint=fingerprint(value))
            )
            if change == "response":
                c.execute(
                    update(requests)
                    .where(
                        requests.c.app_id == row["app_id"],
                        requests.c.kind == checks.KIND + "_seal",
                        requests.c.request_key == body["request_key"],
                    )
                    .values(snapshot=value, fingerprint=fingerprint(value))
                )
    before = snapshot(env)
    response = env[2].get(base + "/" + body["request_key"])
    assert response.status_code in (400, 403, 409), response.text
    assert snapshot(env) == before


def test_authorized_underived_peer_is_recorded_but_its_revocation_cannot_be_omitted(env, tmp_path):
    app, base, original_options, body, _ = setup(env, tmp_path)
    resource = (
        env[2]
        .post(
            f"/api/projects/{env[5]}/resources",
            json={
                "name": "underived independent CSV",
                "format": "csv",
                "content": "amount\n3\n",
            },
        )
        .json()["id"]
    )
    peer = (
        env[2]
        .post(
            f"/api/projects/{env[5]}/apps/csv-preview",
            json={
                "name": "authorized underived peer",
                "resource_id": resource,
                "goal": "exact sum",
            },
        )
        .json()
    )
    graph_base = base.removesuffix("scope-checks")
    for item in original_options["applications"]:
        refreshed = env[2].post(
            f"/api/projects/{env[5]}/apps/{item['app_id']}/delivery-graph/derive",
            json={
                "expected_candidate_fingerprint": item["binding"]["candidate_fingerprint"],
                "request_key": "after-new-peer",
            },
        )
        assert refreshed.status_code == 201, refreshed.text
    anchor = env[2].get(graph_base.rstrip("/")).json()
    node = next(n for n in anchor["graph"]["nodes"] if n["kind"] == "VIEW")
    plan = env[2].post(
        graph_base + "plans",
        json={
            "expected_graph_fingerprint": anchor["graph_fingerprint"],
            "request_key": "with-underived",
            "changes": [
                {
                    "node_id": node["id"],
                    "expected_revision": node["revision"],
                    "expected_content_fingerprint": node["content_fingerprint"],
                }
            ],
        },
    )
    assert plan.status_code == 201, plan.text
    choices = env[2].get(base + "/options", params={"plan_key": "with-underived"})
    assert choices.status_code == 200, choices.text
    assert {"app_id": peer["id"], "reason": "GRAPH_NOT_DERIVED"} in choices.json()["omissions"]
    body.update(
        plan_key="with-underived",
        expected_plan_fingerprint=choices.json()["plan_fingerprint"],
        expected_options_fingerprint=choices.json()["options_fingerprint"],
    )
    for selection in body["selections"]:
        item = next(v for v in choices.json()["applications"] if v["app_id"] == selection["app_id"])
        selection["expected_graph_fingerprint"] = item["binding"]["graph_fingerprint"]
    accepted = env[2].post(base, json=body)
    assert accepted.status_code == 201 and accepted.json()["deterministic_status"] == "PARTIAL", (
        accepted.text
    )
    with env[0].tx() as c:
        peer_runtime = c.execute(
            select(app_drafts.c.runtime_id).where(app_drafts.c.id == peer["id"])
        ).scalar_one()
        c.execute(
            update(grants)
            .where(grants.c.principal_id == peer_runtime, grants.c.resource_id == resource)
            .values(revoked=True)
        )
    before = snapshot(env)
    body["request_key"] = "revoked-omission"
    denied = env[2].post(base, json=body)
    assert denied.status_code in (400, 403, 409), denied.text
    assert snapshot(env) == before


def test_project_receipt_cold_store_and_two_connection_same_key_race(env, tmp_path):
    _, base, _, body, _ = setup(env, tmp_path)
    stores = []
    for _ in range(2):
        store = Store(env[1].database_url, test_only=True)
        if not store.sqlite:
            store.engine = store.engine.execution_options(**env[0].engine.get_execution_options())
        stores.append(store)
    try:
        parsed = checks.Confirmation.model_validate(body)
        with ThreadPoolExecutor(max_workers=2) as pool:
            answers = list(
                pool.map(
                    lambda store: checks.submit(
                        store,
                        env[3],
                        env[5],
                        base.split("/apps/")[1].split("/")[0],
                        parsed,
                        limits(env),
                    ),
                    stores,
                )
            )
        assert sorted(v["cached"] for v in answers) == [False, True]
        assert answers[0]["check_fingerprint"] == answers[1]["check_fingerprint"]
        before = snapshot(env)
        aid = base.split("/apps/")[1].split("/")[0]
        receipt = checks.inspect(stores[1], env[3], env[5], aid, body["request_key"], limits(env))
        assert receipt["check_fingerprint"] == answers[0]["check_fingerprint"]
        assert snapshot(env) == before
    finally:
        for store in stores:
            store.engine.dispose()


def test_project_scope_check_crud_only_role(env, tmp_path, runtime_role):
    app, _, _, body, _ = setup(env, tmp_path)
    store = Store(runtime_role, test_only=True)
    try:
        answer = checks.submit(
            store, env[3], env[5], app["id"], checks.Confirmation.model_validate(body), limits(env)
        )
        assert answer["executed_checks_status"] == "PASS"
        before = snapshot(env)
        assert checks.inspect(store, env[3], env[5], app["id"], body["request_key"], limits(env))[
            "cached"
        ]
        assert snapshot(env) == before
    finally:
        store.engine.dispose()


@pytest.mark.parametrize("identity", ["foreign_owner", "foreign_project"])
def test_foreign_scope_receipt_is_rejected_before_write(env, tmp_path, identity):
    _, base, _, body, _ = setup(env, tmp_path)
    if identity == "foreign_owner":
        env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    else:
        other = env[0].project(env[3], "foreign target project")
        base = base.replace(env[5], other)
    before = snapshot(env)
    reply = env[2].post(base, json=body)
    assert reply.status_code in (400, 403, 409), reply.text
    assert snapshot(env) == before


def test_bad_registered_sum_is_recorded_as_real_failed_check(env, tmp_path, monkeypatch):
    _, base, _, body, _ = setup(env, tmp_path)
    actual = checks.authorized_read

    def faulty_sum(*args, **kwargs):
        value = actual(*args, **kwargs)
        if args[5] == "data.aggregate_csv":
            return {**value, "sum": "999"}
        return value

    monkeypatch.setattr(checks, "authorized_read", faulty_sum)
    response = env[2].post(base, json=body)
    assert response.status_code == 201, response.text
    proof = response.json()
    assert proof["deterministic_status"] == proof["executed_checks_status"] == "FAIL"
    csv = next(v for v in proof["applications"] if v["actual"].get("output"))
    assert (
        next(v for v in csv["actual"]["checks"] if v["id"] == "sum.independent")["status"] == "FAIL"
    )
    assert proof["overall_run_acceptance"] == "NOT_ACCEPTED"


def test_project_same_key_changed_input_and_peer_lock_aba_reject_zero_writes(env, tmp_path):
    _, base, options, body, _ = setup(env, tmp_path)
    assert env[2].post(base, json=body).status_code == 201
    changed = copy.deepcopy(body)
    csv = next(v for v in changed["selections"] if v["kind"] == "CSV")
    csv["input"]["column"] = "amount"
    before = snapshot(env)
    denied = env[2].post(base, json=changed)
    assert denied.status_code == 409, denied.text
    assert snapshot(env) == before
    peer_base = f"/api/projects/{env[5]}/apps/{csv['app_id']}/delivery-graph"
    anchor = env[2].get(peer_base).json()
    for locked, revision in ((True, 0), (False, 1)):
        node = next(n for n in anchor["graph"]["nodes"] if n["kind"] == "VIEW")
        lock = env[2].post(
            peer_base + "/manual-locks",
            json={
                "expected_graph_fingerprint": anchor["graph_fingerprint"],
                "expected_graph_revision": anchor["graph_revision"],
                "change": {
                    "node_id": node["id"],
                    "expected_revision": node["revision"],
                    "expected_content_fingerprint": node["content_fingerprint"],
                },
                "expected_lock_revision": revision,
                "locked": locked,
                "request_key": "peer-" + str(locked),
                "consent": "CONFIRM_EXACT_PROJECT_EDIT_LOCK",
            },
        )
        assert lock.status_code == 201, lock.text
        item = next(v for v in options["applications"] if v["app_id"] == csv["app_id"])
        response = env[2].post(
            peer_base + "/derive",
            json={
                "expected_candidate_fingerprint": item["binding"]["candidate_fingerprint"],
                "request_key": "peer-derive-" + str(locked),
            },
        )
        assert response.status_code == 201, response.text
        anchor = response.json()
    before = snapshot(env)
    rejected = env[2].get(base + "/" + body["request_key"])
    assert rejected.status_code == 409, rejected.text
    assert snapshot(env) == before
