"""Same adopted CSV instance, authorized B, real Worker/NoModel only.

The B/App grants below are explicit test-only preconditions. They are frozen
before measuring the product operation; no product path may create authority.
"""

import hashlib
import json
import re
from contextlib import contextmanager

import pytest
from conftest import env as env
from fastapi.testclient import TestClient
from sqlalchemy import event, insert, select, update
from test_csv_column_revisions import adopt
from test_csv_goal_revisions import approve, drive, ready, start
from test_csv_goal_revisions import raw_trace as raw_trace
from test_csv_owner_review import choices, endpoint
from test_internal_lifecycle import limits
from test_spec_app_operations import snapshot

from sim2act import app_jobs as jobs
from sim2act import csv_goal_revisions as revision
from sim2act import csv_material_revisions as material
from sim2act.api import create_app
from sim2act.db import (
    Store,
    attempts,
    fingerprint,
    grants,
    internal_instances,
    new_id,
    operation_intents,
    operations,
    reservations,
    resources,
    run_contracts,
    runs,
)

B_CONTENT = "amount,quantity\n1.20,7\n2.35,11\n"
B_HASH = hashlib.sha256(B_CONTENT.encode("utf-8")).hexdigest()
HISTORY_TABLES = (
    "app_drafts", "internal_releases", "run_contracts", "internal_run_bindings",
    "internal_app_runs", "internal_instance_data", "operations", "operation_intents",
    "internal_owner_records", "csv_owner_records", "csv_owner_seals",
    "delivery_graph_requests", "goal_card_versions", "delivery_graph_anchors",
    "delivery_graph_source_versions",
)


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def prepared(env):
    """Four NoModel Runs on positive path, including old A accepted history."""
    data, aid, base, instance, path, _, old_value, goal = ready(env, prior=True)
    old_check = start(data, path, old_value)
    drive(data, old_check["run_id"])
    v2 = approve(data, path, old_value)
    current = adopt(data, instance, path, old_value, v2)
    assert current["revision"] == 2 and current["data_version"] == 1
    response = data[2].post(f"/api/projects/{data[5]}/resources", json={
        "name": "already-authorized-B.csv", "format": "csv", "content": B_CONTENT,
    })
    assert response.status_code == 201, response.text
    bid = response.json()["id"]
    # Test fixture only: clone two exact source authorities to the existing
    # App runtime. Owner/project runtime authority came from fixture resource.
    with data[0].tx() as c:
        originals = [dict(row) for row in c.execute(select(grants).where(
            grants.c.principal_id == current["runtime_id"],
            grants.c.resource_id == data[6],
        )).mappings()]
        assert {row["tool_ref"] for row in originals} == {"resource.read", "data.aggregate_csv"}
        assert len(originals) == 2
        for row in originals:
            c.execute(insert(grants).values(**{**row, "id": new_id("grant"), "resource_id": bid}))
        for tool in ("resource.read", "data.aggregate_csv"):
            data[0].authorize(c, data[3], current["runtime_id"], data[5], bid, tool)
    # Re-freeze the original canonical graph's authorization baseline through
    # its actual public derive contract, never by modifying its stored seal.
    refreshed = data[2].post(f"/api/projects/{data[5]}/apps/{aid}/delivery-graph/derive", json={
        "request_key": "material-fixture-authority-baseline",
        "expected_candidate_fingerprint": base["snapshot"]["draft"]["fingerprint"],
    })
    assert refreshed.status_code == 201, refreshed.text
    material_path = f"/api/internal/instances/{current['id']}/csv-material-revisions"
    response = data[2].get(material_path + "/context")
    assert response.status_code == 200, response.text
    ctx = response.json()["context"]
    selected = [row for row in response.json()["materials"] if row["resource_id"] == bid]
    assert len(selected) == 1 and selected[0]["hash"] == B_HASH
    assert "quantity" in selected[0]["columns"]
    assert ctx["parent"]["column"] == "quantity" and ctx["goal"]["version"] == 2
    body = dict(request_key="replace-material-B", expected_revision=current["revision"],
        expected_data_version=current["data_version"], expected_release_fingerprint=v2["fingerprint"],
        expected_graph_fingerprint=ctx["graph_fingerprint"], goal_version=2,
        goal_fingerprint=ctx["goal"]["fingerprint"], baseline_column="quantity", column="quantity",
        resource_id=bid, source_hash=B_HASH)
    return data, aid, base, current, path, material_path, body, v2, old_value, goal


def proposal(seed):
    data, _, _, _, _, path, body, *_ = seed
    response = data[2].post(path + "/previews", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def preserve(before, after):
    for table in HISTORY_TABLES:
        assert all(row in after[table] for row in before[table]), table


def reject_without_writes(data, invoke, expected):
    before = snapshot(data[0])
    response = invoke()
    assert response.status_code == expected, response.text
    assert snapshot(data[0]) == before
    return {"status": response.status_code, "body": response.json(), "database_fingerprint": fingerprint(before)}


@contextmanager
def no_private_bodies(store):
    """Reject full private cells; allow scalar JSON identifier projections.

    This is deliberately bounded to the fresh HTTP rejected call. It does not
    exempt arbitrary journal families or silently ignore SQL discovery reads.
    """
    statements = []
    private = re.compile(r"(?:^|[\s,])(?:app_drafts\.candidate|goal_card_versions\.snapshot|"
        r"goal_cards\.content|delivery_graph_requests\.snapshot|internal_releases\.snapshot|"
        r"run_contracts\.snapshot|internal_run_bindings\.snapshot|"
        r"runs\.(?:context|goal|result|resource_refs|error)|resources\.(?:content|hash))(?=[\s,])", re.I)

    def observe(conn, cursor, statement, parameters, context, many):
        if not statement.lstrip().upper().startswith("SELECT"):
            return
        fields = re.split(r"\sFROM\s", statement, maxsplit=1, flags=re.I)[0]
        statements.append({"sql": statement, "parameters": repr(parameters)})
        assert not private.search(fields), "Private body before revoked A/B source gate: " + statement

    event.listen(store.engine, "before_cursor_execute", observe)
    try:
        yield statements
    finally:
        event.remove(store.engine, "before_cursor_execute", observe)


def test_authorized_B_same_instance_check_cas_result_pending_and_immutable_A(env, tmp_path):
    seed = prepared(env)
    data, aid, base, current, path, material_path, body, v2, old_value, goal = seed
    before = snapshot(data[0])
    value = proposal(seed)
    assert value["namespace"] == material.VERSION
    assert value["input"] == value["baseline_input"] == {"column": "quantity"}
    assert value["material"] == {"resource_id": body["resource_id"], "hash": B_HASH, "format": "csv", "revision": 1}
    assert value["context"]["source"]["resource_id"] == data[6]
    assert value["context"]["goal"]["snapshot"]["content"]["resource_refs"] == [data[6]]
    assert value["effective_candidate"]["goal"] == goal
    assert value["effective_candidate"]["manifest"]["data_bindings"][0]["resource_ref"] == body["resource_id"]
    assert value["effective_candidate"]["source_hash"] == B_HASH
    assert value["spec_revision"] == 3
    assert value["effective_fingerprint"] != old_value["effective_fingerprint"]
    assert data[2].post(material_path + "/previews", json=body).json() == value
    accepted = start(data, path, value)
    assert accepted["check_instance_id"] != current["id"]
    unchanged = data[2].get(f"/api/internal/instances/{current['id']}").json()
    assert (unchanged["revision"], unchanged["data_version"], unchanged["release_id"]) == (2, 1, v2["id"])
    drive(data, accepted["run_id"])
    check_run = jobs.inspect_job(data[0], data[3], accepted["run_id"])
    assert check_run["result"]["sum"] == "18" and check_run["result"]["count"] == 2
    version = approve(data, path, value)
    assert version["snapshot"]["draft"] == base["snapshot"]["draft"]
    adopted = adopt(data, current, path, value, version)
    assert (adopted["id"], adopted["runtime_id"], adopted["source_app_id"]) == (current["id"], current["runtime_id"], aid)
    assert adopted["revision"] == 3 and adopted["data_version"] == 1
    request = dict(expected_revision=3, expected_release_fingerprint=version["fingerprint"],
        input={"column": "quantity"}, request_key="B-first-business-result", csv_review="FREEZE_SUM_ONLY_WITHOUT_MD")
    response = data[2].post(f"/api/internal/instances/{current['id']}/runs", json=request)
    assert response.status_code == 202, response.text
    fresh = response.json()
    assert data[2].post(f"/api/internal/instances/{current['id']}/runs", json=request).json() == fresh
    drive(data, fresh["run_id"])
    result = jobs.inspect_job(data[0], data[3], fresh["run_id"])
    assert result["status"] == "SUCCEEDED" and result["result_version"] == 2
    assert result["result"]["sum"] == "18" and type(result["result"]["count"]) is int and result["result"]["count"] == 2
    assert result["result"]["resource_id"] == body["resource_id"] and result["result"]["source_hash"] == B_HASH
    pending = data[2].get(endpoint(current, fresh["run_id"]))
    assert pending.status_code == 200, pending.text
    pending = pending.json()
    assert pending["content_access"] and pending["owner_acceptance"] == "PENDING"
    assert pending["sequence"] == 0 and pending["history"] == []
    assert pending["current"]["output"] == result["result"]
    old_prepared = next(row for row in before["csv_owner_records"] if row["kind"] == "PREPARE")
    old_reuse = reject_without_writes(data,
        lambda: data[2].post(endpoint(current, fresh["run_id"]) + "-requests", json=choices(old_prepared)), 409)
    with data[0].tx() as c:
        contract = c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id == fresh["run_id"])).scalar_one()
        check_contract = c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id == accepted["run_id"])).scalar_one()
        op = dict(c.execute(select(operations).where(operations.c.run_id == fresh["run_id"])).mappings().one())
        intent = c.execute(select(operation_intents.c.request).where(operation_intents.c.operation_id == op["id"])).scalar_one()
        assert c.execute(select(attempts.c.id)).first() is None
        assert c.execute(select(reservations.c.id)).first() is None
    for frozen in (contract, check_contract):
        assert frozen["goal"]["resource_refs"] == [body["resource_id"]]
        assert frozen["resources"][0]["resource_id"] == body["resource_id"] and frozen["resources"][0]["content_hash"] == B_HASH
        assert frozen["goal"]["goal"] == goal["goal"]
    assert intent == {"tool": "data.aggregate_csv", "args": {"resource_id": body["resource_id"], "column": "quantity"}}
    assert op["receipt"]["data"] == result["result"]
    # New Store + actual HTTP app proves cold read-only reconstruction, without
    # following a moving current binding for historical A results.
    cold = Store(data[1].database_url, test_only=True)
    read_before = snapshot(data[0])
    try:
        with TestClient(create_app(cold, data[1])) as client:
            client.headers.update({"Authorization": "Bearer synthetic-test-A"})
            old_response = client.get(f"/api/internal/instances/{current['id']}/runs/{data[2].csv_previous_run['run_id']}")
            assert old_response.status_code == 200, old_response.text
            assert old_response.json()["result"]["sum"] == "30"
            new_response = client.get(f"/api/internal/instances/{current['id']}/runs/{fresh['run_id']}")
            assert new_response.status_code == 200 and new_response.json()["result"] == result["result"]
            assert client.get(endpoint(current, fresh["run_id"])).status_code == 200
    finally:
        cold.engine.dispose()
    assert snapshot(data[0]) == read_before
    after = snapshot(data[0])
    preserve(before, after)
    for table in ("grants", "principals", "app_drafts"):
        assert after[table] == before[table], table
    new_instances = {row["id"] for row in after["internal_instances"]} - {row["id"] for row in before["internal_instances"]}
    assert new_instances == {accepted["check_instance_id"]}
    dump(tmp_path / "actual-material-delivery.json", dict(
        B_bytes=B_CONTENT, B_sha256=B_HASH, request=body, preview=value, check=accepted,
        check_result=check_run, version=version, adopted=adopted, new_run=result,
        contract=contract, check_contract=check_contract, operation=op, intent=intent,
        pending=pending, rejected_old_acceptance=old_reuse, old_A_raw_rows_preserved=True,
        unchanged_authority_tables=["grants", "principals", "app_drafts"], model_attempts=0, reservations=0))


def test_material_preview_rejects_wrong_hash_data_version_and_ungranted_B_without_writes(env, tmp_path):
    seed = prepared(env)
    data, _, _, current, _, material_path, body, *_ = seed
    evidence = {}
    for label, changes in (
        ("wrong_hash", {"source_hash": "0" * 64}),
        ("stale_data_version", {"expected_data_version": current["data_version"] + 1}),
    ):
        evidence[label] = reject_without_writes(data,
            lambda changes=changes, label=label: data[2].post(material_path + "/previews",
                json={**body, **changes, "request_key": label}), 409)
    ungranted = data[2].post(f"/api/projects/{data[5]}/resources", json={
        "name": "project-only-no-app-grant.csv", "format": "csv", "content": "amount,quantity\n3,19\n",
    })
    assert ungranted.status_code == 201, ungranted.text
    target = ungranted.json()["id"]
    cold = Store(data[1].database_url, test_only=True)
    ungranted_body = {**body, "resource_id": target,
        "source_hash": hashlib.sha256(b"amount,quantity\n3,19\n").hexdigest(),
        "request_key": "ungranted-B"}
    statements = []
    evidence["ungranted_B_request"] = ungranted_body
    try:
        with TestClient(create_app(cold, data[1])) as client:
            client.headers.update({"Authorization": "Bearer synthetic-test-A"})
            # The first submission must gate B before reading the old Goal,
            # candidate, Release or proposal body, even with a cold Store.
            with no_private_bodies(cold) as statements:
                evidence["ungranted_B"] = reject_without_writes(data,
                    lambda: client.post(material_path + "/previews", json=ungranted_body), 403)
    finally:
        cold.engine.dispose()
        evidence["ungranted_B_sql_before_private_body"] = statements
        dump(tmp_path / "actual-material-early-rejections.json", evidence)


@pytest.mark.parametrize("which", ["A", "B"])
def test_revoked_A_B_cold_preview_checks_and_metadata_cancel_precede_private_bodies(env, tmp_path, which):
    seed = prepared(env)
    data, _, _, current, path, _, body, *_ = seed
    value = proposal(seed)
    accepted = start(data, path, value)
    with data[0].tx() as c:
        version = c.execute(select(runs.c.version).where(runs.c.id == accepted["run_id"])).scalar_one()
    rid = data[6] if which == "A" else body["resource_id"]
    listed = data[2].get(f"/api/projects/{data[5]}/grants")
    assert listed.status_code == 200, listed.text
    selected = [row for row in listed.json() if row["principal_id"] == current["runtime_id"]
        and row["resource_id"] == rid and row["tool_ref"] == "resource.read" and not row["revoked"]]
    assert len(selected) == 1, selected
    revoked = data[2].post("/api/grants/" + selected[0]["id"] + "/revoke", json={
        "command": "revoke", "version": selected[0]["revision"],
    })
    assert revoked.status_code == 200, revoked.text
    cold = Store(data[1].database_url, test_only=True)
    evidence = {"which": which, "grant": selected[0], "revoked": revoked.json()}
    try:
        with TestClient(create_app(cold, data[1])) as client:
            client.headers.update({"Authorization": "Bearer synthetic-test-A"})
            with no_private_bodies(cold) as statements:
                evidence["cold_preview"] = reject_without_writes(data,
                    lambda: client.get(path + "/previews/" + body["request_key"]), 403)
                evidence["cold_check"] = reject_without_writes(data,
                    lambda: client.get(path + "/checks/" + body["request_key"]), 403)
            evidence["sql_before_private_body"] = statements
            # Original metadata command stays usable even though full body GET
            # is now forbidden. No Worker is started for this revoked CHECK.
            result = client.post(f"/api/internal/instances/{accepted['check_instance_id']}/runs/{accepted['run_id']}/commands",
                json={"command": "cancel", "version": version})
            assert result.status_code == 200, result.text
            evidence["cancel"] = result.json()
    finally:
        cold.engine.dispose()
    with data[0].tx() as c:
        terminal = dict(c.execute(select(runs.c.status, runs.c.cancel_intent).where(runs.c.id == accepted["run_id"])).mappings().one())
        assert terminal == {"status": "CANCELLED", "cancel_intent": True}
        assert c.execute(select(operations.c.id).where(operations.c.run_id == accepted["run_id"])).first() is None
    evidence["terminal"] = terminal
    dump(tmp_path / "actual-material-revoked-cold.json", evidence)


@pytest.mark.parametrize("which", ["A", "B"])
def test_material_hash_drift_after_check_prevents_release_without_writes(env, tmp_path, which):
    seed = prepared(env)
    data, _, _, _, path, _, body, *_ = seed
    value = proposal(seed)
    accepted = start(data, path, value)
    drive(data, accepted["run_id"])
    response = data[2].get(path + "/checks/" + body["request_key"])
    assert response.status_code == 200, response.text
    proof = response.json()
    assert proof["status"] == "PASS"
    # Explicit test-only stored-byte attack on A provenance or B execution
    # material, after genuine B CHECK succeeded. Neither can be silently read
    # as a newly frozen source under the old exact proof.
    rid = data[6] if which == "A" else body["resource_id"]
    original_hash = value["context"]["source"]["hash"] if which == "A" else B_HASH
    changed = "amount,quantity\n10,2\n20,4\n" if which == "A" else "amount,quantity\n1.20,7\n2.35,12\n"
    with data[0].tx() as c:
        c.execute(update(resources).where(resources.c.id == rid).values(
            content=changed, hash=hashlib.sha256(changed.encode()).hexdigest()))
    rejected = reject_without_writes(data,
        lambda: data[2].post(path + "/version-approvals", json={"request_key": body["request_key"],
            "expected_check_fingerprint": proof["check_fingerprint"], "consent": revision.VERSION_CONSENT}), 409)
    dump(tmp_path / "actual-material-hash-drift.json", dict(which=which, resource_id=rid,
        original_hash=original_hash, changed_bytes=changed,
        actual_check=accepted, proof=proof, rejected=rejected))


def test_same_instance_material_adoption_rejects_actual_intervening_data_version(env, tmp_path):
    seed = prepared(env)
    data, _, _, current, path, _, body, v2, *_ = seed
    value = proposal(seed)
    accepted = start(data, path, value)
    drive(data, accepted["run_id"])
    version = approve(data, path, value)
    response = data[2].post(path + "/adoption-approvals", json=dict(
        request_key=body["request_key"], expected_revision=current["revision"],
        target_release_id=version["id"], expected_target_fingerprint=version["fingerprint"]))
    assert response.status_code == 201, response.text
    approval = data[2].get(path + "/adoption-approvals/" + body["request_key"])
    assert approval.status_code == 200, approval.text
    approval = approval.json()
    intervening = jobs.enqueue(data[0], data[3], current["id"], 2, v2["fingerprint"],
        {"column": "quantity"}, "actual-A-after-B-approval", limits(data), csv_review="FREEZE_SUM_ONLY_WITHOUT_MD")
    drive(data, intervening["run_id"])
    result = jobs.inspect_job(data[0], data[3], intervening["run_id"])
    assert result["result"]["sum"] == "5" and result["result_version"] == 2
    rejected = reject_without_writes(data,
        lambda: data[2].post(f"/api/internal/instances/{current['id']}/switch-approvals/{approval['id']}/commit",
            json={"fingerprint": approval["fingerprint"]}), 409)
    with data[0].tx() as c:
        state = dict(c.execute(select(internal_instances).where(internal_instances.c.id == current["id"])).mappings().one())
    assert state["release_id"] == v2["id"] and state["revision"] == 2 and state["data_version"] == 2
    dump(tmp_path / "actual-material-stale-cas.json", dict(value=value, check=accepted, target=version,
        approval=approval, intervening=result, rejected=rejected, actual_instance=state))
