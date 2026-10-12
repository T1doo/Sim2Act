"""Independent frozen answer set and real API/persistent graph patch regressions."""

import copy
import csv
import io
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_delivery_graph_apps import path, snapshot
from test_internal_lifecycle import limits

from sim2act.api import create_app
from sim2act.column_patches import DefinitionInput, propose
from sim2act.db import Store, app_drafts, fingerprint, grants, resources
from sim2act.db import delivery_graph_requests as requests
from sim2act.delivery_graph_apps import DeriveInput, derive, set_lock

CSV = Path(__file__).with_name("fixtures") / "column-binding.csv"


def setup(env):
    client, pid = env[2], env[5]
    # New isolated resource, not replacement of the existing fixture/source.
    rid = client.post(f"/api/projects/{pid}/resources", json=dict(
        name="column-binding.csv", format="csv", content=CSV.read_text())).json()["id"]
    made = client.post(f"/api/projects/{pid}/apps/csv-preview", json=dict(
        name="binding fixture", goal="engineering case only", resource_id=rid)).json()
    aid = made["id"]
    old_preview = client.post(f"/api/apps/{aid}/previews", json=dict(
        input={"column": "amount"}, request_key="original-amount")).json()
    assert old_preview["status"] == "SUCCEEDED" and old_preview["output"]["sum"] == "30"
    inspected = client.get(f"/api/apps/{aid}").json()
    graph = client.post(path(env, aid) + "/derive", json=dict(
        expected_candidate_fingerprint=inspected["fingerprint"], request_key="baseline")).json()
    node = next(n for n in graph["graph"]["nodes"] if n["key"] == "action:aggregate")
    body = dict(expected_candidate_fingerprint=inspected["fingerprint"],
                expected_graph_fingerprint=graph["graph_fingerprint"], request_key="new-definition",
                kind="csv.column-binding.v1", baseline_column="amount", column="quantity",
                change=dict(node_id=node["id"], expected_revision=node["revision"],
                            expected_content_fingerprint=node["content_fingerprint"]))
    return aid, rid, graph, body, old_preview


def url(env, aid):
    return path(env, aid) + "/column-patches"


def check_body(patch, key="checks"):
    return dict(expected_patch_fingerprint=patch["patch_fingerprint"], request_key=key)


def assert_domain_unchanged(before, after):
    for name in before:
        if name != "delivery_graph_requests":
            assert sorted(before[name], key=fingerprint) == sorted(after[name], key=fingerprint), name


def test_new_definition_draft_exact_check_cold_history_and_preserved_objects(env, tmp_path):
    aid, _, graph, body, old_preview = setup(env)
    before = snapshot(env)
    reply = env[2].post(url(env, aid), json=body)
    assert reply.status_code == 201, reply.text
    patch = reply.json()
    assert patch["checks_status"] == "NOT_RUN" and patch["state"] == "DRAFT_PATCH"
    assert patch["definition"]["baseline_input"] == {"column": "amount"}
    assert patch["definition"]["column_binding"]["value"] == "quantity"
    # Hand-frozen expected changed/retained classes, independent of graph traversal.
    changed = {"ACTION", "ARTIFACT", "VIEW", "CHECK", "MANIFEST"}
    retained = {"GOAL", "SOURCE", "REQUIREMENT"}
    original = {n["id"]: n for n in graph["graph"]["nodes"]}
    assert {n["id"] for n in patch["modified_objects"]} == {
        n["id"] for n in original.values() if n["kind"] in changed}
    assert patch["preserved_objects"] == [
        n for n in graph["graph"]["nodes"] if n["kind"] in retained]
    for n in patch["graph"]["nodes"]:
        assert n["id"] in original and n["revision"] == original[n["id"]]["revision"] + (n["kind"] in changed)
    assert_domain_unchanged(before, snapshot(env))
    reject_before = snapshot(env)
    wrong = env[2].post(url(env, aid) + "/new-definition/checks", json=dict(
        expected_patch_fingerprint="0" * 64, request_key="wrong-version"))
    assert wrong.status_code == 409 and snapshot(env) == reject_before
    result = env[2].post(url(env, aid) + "/new-definition/checks", json=check_body(patch))
    assert result.status_code == 201, result.text
    result = result.json()
    # Independent CSV reader and decimal arithmetic, no product aggregate helper.
    rows = list(csv.DictReader(io.StringIO(CSV.read_text())))
    for kind, column in (("baseline", "amount"), ("patched", "quantity")):
        expected = sum((Decimal(row[column]) for row in rows), Decimal(0))
        assert result["outputs"][kind]["sum"] == str(expected)
        assert result["outputs"][kind]["count"] == len(rows)
    assert result["outputs"]["baseline"]["sum"] == "30"
    assert result["outputs"]["patched"]["sum"] == "15"
    assert result["checks_status"] == "PASS" and result["state"] == "CHECKED_CANDIDATE"
    assert result["revalidation_scope"] == "APP"  # Unknown semantic completeness retained.
    assert len(result["revalidated_nodes"]) == len(original)
    assert result["executed_checks"] == [n["id"] for n in original.values() if n["kind"] == "CHECK"]
    assert result["preserved_objects"] == patch["preserved_objects"]
    assert result["semantic_status"] == "UNKNOWN" and result["owner_acceptance"] == "PENDING"
    assert result["publishable"] is False and result["formal_publication_enabled"] is False
    assert result["model_requests"] == result["business_writes"] == 0
    after = snapshot(env)
    assert_domain_unchanged(before, after)
    # Independent Store/client reading the same disk-backed fixture, no preseeded results.
    store = Store(env[1].database_url, test_only=True) if env[0].sqlite else env[0]
    cold = TestClient(create_app(store, env[1]))
    cold.headers["Authorization"] = "Bearer synthetic-test-A"
    try:
        history = cold.get(url(env, aid)).json()
        assert history["items"][0]["patch"] == {k: v for k, v in patch.items() if k != "cached"}
        assert history["items"][0]["checks"] == [{k: v for k, v in result.items() if k != "cached"}]
        assert cold.post(url(env, aid), json=body).json()["cached"] is True
        assert cold.post(url(env, aid) + "/new-definition/checks", json=check_body(patch)).json()["cached"] is True
        assert cold.get(f"/api/apps/{aid}").json()["history"][0] == old_preview
        assert snapshot(env) == after
        (tmp_path / "independent-answer.json").write_text(__import__("json").dumps(dict(
            expected_amount="30", expected_quantity="15", patch=patch, checks=result,
            missed_updates=0, unnecessary_changes=0,
            expected_modified_ids=sorted(n["id"] for n in original.values() if n["kind"] in changed),
            expected_preserved_ids=sorted(n["id"] for n in original.values() if n["kind"] in retained)), indent=2))
    finally:
        cold.close()
        if store is not env[0]:
            store.engine.dispose()


@pytest.mark.parametrize("attack", ["column", "same_column", "schema", "scope", "candidate", "node", "bool_revision", "stale_graph", "permission", "code", "kind"])
def test_closed_definition_negative_cases_zero_write(env, attack):
    aid, _, _, body, _ = setup(env)
    if attack == "column":
        body["column"] = "item"
    elif attack == "same_column":
        body["column"] = "amount"
    elif attack in {"schema", "scope", "permission", "code"}:
        body[attack] = {"authorized": True}
    elif attack == "candidate":
        body["expected_candidate_fingerprint"] = "0" * 64
    elif attack == "node":
        body["change"]["node_id"] = body["change"]["node_id"].replace("action_", "node_")
    elif attack == "bool_revision":
        body["change"]["expected_revision"] = True
    elif attack == "stale_graph":
        body["expected_graph_fingerprint"] = "0" * 64
    else:
        body["kind"] = "arbitrary.code"
    before = snapshot(env)
    assert env[2].post(url(env, aid), json=body).status_code >= 400
    assert snapshot(env) == before


@pytest.mark.parametrize("attack", ["owner_revoke", "runtime_revoke", "source", "source_rehash", "lock", "identity", "project", "definition_tamper", "check_tamper", "same_key"])
def test_saved_patch_and_check_invalidation_zero_write(env, attack):
    aid, rid, graph, body, _ = setup(env)
    patch = env[2].post(url(env, aid), json=body).json()
    result = env[2].post(url(env, aid) + "/new-definition/checks", json=check_body(patch))
    assert result.status_code == 201, result.text
    with env[0].tx() as c:
        if attack.endswith("revoke"):
            principal = env[3] if attack == "owner_revoke" else c.execute(
                select(app_drafts.c.runtime_id).where(app_drafts.c.id == aid)).scalar_one()
            c.execute(update(grants).where(grants.c.principal_id == principal,
                                          grants.c.resource_id == rid).values(revoked=True))
        elif attack.startswith("source"):
            content = CSV.read_text().replace("20,8", "21,8")
            values = {"content": content}
            if attack == "source_rehash":
                values["hash"] = __import__("hashlib").sha256(content.encode()).hexdigest()
            c.execute(update(resources).where(resources.c.id == rid).values(**values))
        elif attack.endswith("tamper"):
            kind = "column_patch" if attack == "definition_tamper" else "column_check"
            row = c.execute(select(requests).where(requests.c.app_id == aid, requests.c.kind == kind)).mappings().first()
            value = copy.deepcopy(row["snapshot"])
            value["response"]["owner_acceptance"] = "ACCEPTED"
            c.execute(update(requests).where(requests.c.app_id == aid, requests.c.kind == kind).values(
                snapshot=value, fingerprint=fingerprint(value)))
    if attack == "lock":
        set_lock(env[0], env[3], env[5], aid, dict(
            expected_graph_fingerprint=graph["graph_fingerprint"], request_key="lock",
            change=body["change"], locked=True), limits(env))
        fresh = derive(env[0], env[3], env[5], aid, DeriveInput(
            expected_candidate_fingerprint=body["expected_candidate_fingerprint"], request_key="locked-anchor"), limits(env))
        body["expected_graph_fingerprint"] = fresh["graph_fingerprint"]
        node = next(n for n in fresh["graph"]["nodes"] if n["id"] == body["change"]["node_id"])
        body["change"]["expected_content_fingerprint"] = node["content_fingerprint"]
        body["request_key"] = "locked-proposal"
    elif attack == "identity":
        env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    target_url = url(env, aid)
    if attack == "project":
        other = env[2].post("/api/projects", json={"name": "other"}).json()["id"]
        target_url = target_url.replace(env[5], other)
    before = snapshot(env)
    if attack == "same_key":
        altered = {**body, "column": "amount", "baseline_column": "quantity"}
        assert env[2].post(target_url, json=altered).status_code == 409
    elif attack == "lock":
        blocked = env[2].post(target_url, json=body)
        assert blocked.status_code == 400 and blocked.json()["error"]["code"] == "LOCK_CONFLICT"
    else:
        assert env[2].get(target_url).status_code >= 400
    confirmation = check_body(patch)
    if attack == "same_key":
        confirmation["expected_patch_fingerprint"] = "0" * 64
    replay = env[2].post(target_url + "/new-definition/checks", json=confirmation)
    assert replay.status_code >= 400
    assert snapshot(env) == before


def test_duplicate_definition_and_checks_serialized_by_existing_project_lock(env):
    aid, _, _, body, _ = setup(env)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: propose(env[0], env[3], env[5], aid,
                            DefinitionInput.model_validate(body), limits(env)), range(2)))
    assert sorted(r["cached"] for r in results) == [False, True]
    after = snapshot(env)
    assert env[2].post(url(env, aid), json=body).json()["cached"]
    assert snapshot(env) == after


def test_old_patch_invalidates_after_lock_cycle_without_hiding_new_draft(env):
    aid, _, graph, body, _ = setup(env)
    original = env[2].post(url(env, aid), json=body).json()
    for locked in (True, False):
        node = next(n for n in graph["graph"]["nodes"] if n["id"] == body["change"]["node_id"])
        set_lock(env[0], env[3], env[5], aid, dict(
            expected_graph_fingerprint=graph["graph_fingerprint"], request_key=f"lock-{locked}",
            change=dict(node_id=node["id"], expected_revision=node["revision"],
                        expected_content_fingerprint=node["content_fingerprint"]), locked=locked), limits(env))
        graph = derive(env[0], env[3], env[5], aid, DeriveInput(
            expected_candidate_fingerprint=body["expected_candidate_fingerprint"],
            request_key=f"derive-{locked}"), limits(env))
    body["expected_graph_fingerprint"] = graph["graph_fingerprint"]
    body["request_key"] = "fresh-definition"
    fresh = env[2].post(url(env, aid), json=body)
    assert fresh.status_code == 201, fresh.text
    history = env[2].get(url(env, aid)).json()
    assert [v["patch"]["request_key"] for v in history["items"]] == ["fresh-definition"]
    assert history["invalidated"] == [dict(request_key="new-definition", state="INVALIDATED", reason="VERSION_CONFLICT")]
    before = snapshot(env)
    assert env[2].post(url(env, aid) + "/new-definition/checks", json=check_body(original)).status_code == 409
    assert snapshot(env) == before


def test_coherently_resigned_saved_check_cannot_promote_false_result(env):
    aid, _, _, body, _ = setup(env)
    patch = env[2].post(url(env, aid), json=body).json()
    assert env[2].post(url(env, aid) + "/new-definition/checks", json=check_body(patch)).status_code == 201
    with env[0].tx() as c:
        for kind in ("column_check", "column_check_seal"):
            row = c.execute(select(requests).where(requests.c.app_id == aid, requests.c.kind == kind)).mappings().one()
            value = copy.deepcopy(row["snapshot"])
            response = value["response"]
            response["outputs"]["patched"]["sum"] = "30"
            response["check_fingerprint"] = fingerprint({k: v for k, v in response.items() if k != "check_fingerprint"})
            c.execute(update(requests).where(requests.c.app_id == aid, requests.c.kind == kind).values(
                snapshot=value, fingerprint=fingerprint(value)))
    before = snapshot(env)
    assert env[2].get(url(env, aid)).status_code == 409
    assert env[2].post(url(env, aid) + "/new-definition/checks", json=check_body(patch)).status_code == 409
    assert snapshot(env) == before


@pytest.mark.parametrize("kind", ["column_patch", "column_check"])
def test_history_capacity_rejects_extra_acceptance_but_keeps_original_keys(env, monkeypatch, kind):
    import sim2act.column_patches as patches
    assert patches.HISTORY_LIMIT == 50
    # Two real accepted records exercise the same serial capacity boundary;
    # no forged fixture receipts and no change to the deployed limit of 50.
    monkeypatch.setattr(patches, "HISTORY_LIMIT", 2)
    aid, _, _, body, _ = setup(env)
    patch = env[2].post(url(env, aid), json=body).json()
    if kind == "column_patch":
        assert env[2].post(url(env, aid), json={**body, "request_key": "second"}).status_code == 201
        before = snapshot(env)
        rejected = env[2].post(url(env, aid), json={**body, "request_key": "third"})
        retry = env[2].post(url(env, aid), json=body)
    else:
        for key in ("checks", "second"):
            assert env[2].post(url(env, aid) + "/new-definition/checks", json=check_body(patch, key)).status_code == 201
        before = snapshot(env)
        rejected = env[2].post(url(env, aid) + "/new-definition/checks", json=check_body(patch, "third"))
        retry = env[2].post(url(env, aid) + "/new-definition/checks", json=check_body(patch))
    assert rejected.status_code == 400 and rejected.json()["error"]["code"] == "INVALID_INPUT"
    assert retry.json()["cached"] is True
    assert snapshot(env) == before
    history = env[2].get(url(env, aid)).json()
    assert len(history["items"] if kind == "column_patch" else history["items"][0]["checks"]) == 2


def test_project_unknown_dependencies_block_execution_without_rewriting(env, monkeypatch):
    from sim2act import delivery_graph_apps as adapter
    aid, _, _, body, _ = setup(env)
    real_build = adapter.build

    def project_unknown(*args, **kwargs):
        saved, writes = real_build(*args, **kwargs)
        saved["context"]["unknown_dependencies"][0]["scope"] = "PROJECT"
        with env[0].engine.connect() as c:
            candidate = c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
        saved["graph"] = adapter.core.derive_manifest_graph(
            candidate["manifest"], candidate["actions"], saved["source_versions"],
            {n["key"]: n["id"] for n in saved["graph"]["nodes"]}, saved["context"], limits(env))
        saved["context"]["graph_fingerprint"] = saved["graph"]["graph_fingerprint"]
        return saved, writes

    monkeypatch.setattr(adapter, "build", project_unknown)
    graph = derive(env[0], env[3], env[5], aid, DeriveInput(
        expected_candidate_fingerprint=body["expected_candidate_fingerprint"],
        request_key="project-unknown-anchor"), limits(env))
    body["expected_graph_fingerprint"] = graph["graph_fingerprint"]
    before = snapshot(env)
    denied = env[2].post(url(env, aid), json=body)
    assert denied.status_code >= 400 and denied.json()["error"]["code"] == "UNSUPPORTED_CAPABILITY"
    assert snapshot(env) == before
