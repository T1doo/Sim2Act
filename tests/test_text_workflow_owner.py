"""Actual closed-text Worker and per-Run simulated owner declarations.

Synthetic TXT/MD only. These engineering declarations never establish real
semantic acceptance, formal publication, native-browser or real-model coverage.
"""

import copy
import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from sql_private_barrier import PrivateReadBarrier
from sqlalchemy import select, update
from test_pb_natural_use_read_gates import TypedPrivateBarrier
from test_text_workflows import draft, enqueue, inspect, instance, material, once

from sim2act.api import create_app
from sim2act.db import (
    Store,
    attempts,
    fingerprint,
    goal_cards,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_run_bindings,
    meta,
    natural_owner_records,
    natural_owner_seals,
    operation_intents,
    operations,
    resources,
    runs,
)

VERSION = "owner.text-four-step.v1"
SOURCE = "Amber assigned to Lee\nViolet due Friday\nAmber review pending\n"
REASON = "SIMULATED engineering declaration; real semantic acceptance not run"


def snapshot(store, *, owner=True):
    """Test-only direct storage inspection, never a product authorization path."""
    excluded = set() if owner else {"natural_owner_records", "natural_owner_seals"}
    with store.tx() as c:
        return {
            table.name: sorted(
                (dict(row) for row in c.execute(select(table)).mappings()),
                key=lambda row: json.dumps(row, sort_keys=True, default=str),
            )
            for table in meta.sorted_tables
            if table.name not in excluded
        }


def owner_rows(store, rid):
    with store.tx() as c:
        return {
            table.name: [dict(row) for row in c.execute(select(table).where(
                table.c.run_id == rid)).mappings()]
            for table in (natural_owner_records, natural_owner_seals)
        }


@pytest.fixture
def evidence(env, tmp_path):
    """Retain actual request/response bodies, including failed observations."""
    requests = []
    facts = dict(actual_worker=True, real_model_requests=0,
        semantic_acceptance="NOT_RUN", native_browser="NOT_RUN")

    def record(response):
        response.read()
        request = response.request
        raw = request.content.decode("utf-8") if request.content else None
        requests.append(dict(method=request.method, url=str(request.url),
            request=json.loads(raw) if raw else None,
            status=response.status_code, response=response.text))

    env[2].event_hooks["response"].append(record)
    try:
        yield facts, record
    finally:
        env[2].event_hooks["response"].remove(record)
        (tmp_path / "text-owner-http.json").write_text(
            json.dumps(requests, ensure_ascii=False, indent=2), encoding="utf-8")
        (tmp_path / "text-owner-proof.json").write_text(
            json.dumps(facts, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def flow(env, *, emit=True):
    resource, card = material(env, SOURCE, "md")
    app, creation = draft(env, resource, card)
    release, inst = instance(env, app["id"])
    value = dict(term_a="Amber", term_b="Violet", emit_report=emit)
    rid = enqueue(env, release, inst, value, "owner-first-input")
    once(env)
    response = inspect(env, inst, rid)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == ("SUCCEEDED" if emit else "PARTIAL")
    path = f"/api/internal/instances/{inst['id']}/runs/{rid}/text-owner-review"
    return dict(resource=resource, card=card, app=app, creation=creation,
        release=release, instance=inst, input=value, run_id=rid,
        result=response.json(), path=path)


def state(client, path, key=None):
    response = client.get(path, params={"request_key": key} if key else {})
    assert response.status_code == 200, response.text
    return response.json()


def prepare(client, path, key="owner-preview"):
    current = state(client, path)
    assert current["content_access"], current
    body = dict(command="PREPARE", request_key=key,
        expected_sequence=current["sequence"],
        expected_contract_fingerprint=fingerprint(current["current"]))
    response = client.post(path + "-requests", json=body)
    assert response.status_code == 201, response.text
    recovered = state(client, path, key)["recovered"]
    assert recovered["payload"]["request"] == body
    assert recovered["id"] == response.json()["record"]["id"]
    return recovered, body


def decision(review, key="owner-decision"):
    return dict(command="DECIDE", request_key=key,
        expected_sequence=review["sequence"], review_id=review["id"],
        review_fingerprint=review["fingerprint"], choices=[
            dict(item_id=item["id"], decision="ACCEPT", reason=REASON)
            for item in review["payload"]["contract"]["items"]])


def assert_actual_contract(env, data, contract, *, version):
    assert contract["version"] == VERSION
    assert contract["principal_id"] == env[3] and contract["project_id"] == env[5]
    assert contract["app_id"] == data["app"]["id"]
    assert contract["instance_id"] == data["instance"]["id"]
    assert contract["run_id"] == data["run_id"]
    assert contract["release_id"] == data["release"]["id"]
    assert contract["release_fingerprint"] == data["release"]["fingerprint"]
    assert contract["source_goal"]["card_id"] == data["card"]["id"]
    assert contract["source_goal"]["version"] == data["card"]["version"]
    assert contract["goal"] == data["card"]["snapshot"]["content"]
    assert contract["material"]["resource_id"] == data["resource"]
    assert contract["material"]["hash"] == data["creation"]["expected_source_hash"]
    assert contract["material"]["content"] == SOURCE
    assert contract["input"] == data["input"]
    assert contract["output"] == data["result"]["result"]
    assert contract["output_fingerprint"] == fingerprint(contract["output"])
    assert contract["output"]["term_a"] == data["input"]["term_a"]
    assert contract["output"]["term_b"] == data["input"]["term_b"]
    assert contract["instance_revision"] == data["instance"]["revision"]
    assert contract["result_version"] == version
    assert contract["technical_semantic_status"] == "UNKNOWN"
    assert not contract["formal_publication_enabled"]
    ids = [item["id"] for item in contract["items"]]
    assert len(ids) == len(set(ids))
    assert "title" in ids and "goal" in ids
    for field in ("known", "assumptions", "unresolved", "constraints", "acceptance_checks"):
        for n, text in enumerate(contract["goal"][field], 1):
            assert dict(id=f"{field}.{n}", text=text) in contract["items"]
    assert "source-and-report" in ids and "technical-boundary" in ids
    assert [receipt["step_id"] for receipt in contract["actual_operations"]] == [
        "read", "lookup_a", "lookup_b", "report"]
    assert all(receipt["status"] == "VERIFIED" for receipt in contract["actual_operations"])
    with env[0].tx() as c:
        operations_rows = c.execute(select(operations).where(
            operations.c.run_id == data["run_id"])).mappings().all()
        assert len(operations_rows) == 4
        by_id = {row["id"]: row for row in operations_rows}
        for receipt in contract["actual_operations"]:
            operation = by_id[receipt["operation_id"]]
            assert operation["status"] == "VERIFIED" and operation["receipt"] == receipt
            intent = c.execute(select(operation_intents.c.request).where(
                operation_intents.c.operation_id == operation["id"])).scalar_one()
            assert fingerprint(intent) == operation["fingerprint"]
        binding = c.execute(select(internal_run_bindings).where(
            internal_run_bindings.c.run_id == data["run_id"])).mappings().one()
        assert binding["app_run_id"] == contract["app_run_id"]
        actual = c.execute(select(internal_app_runs).where(
            internal_app_runs.c.id == binding["app_run_id"])).mappings().one()
        assert actual["instance_id"] == data["instance"]["id"]
        typed = c.execute(select(internal_instance_data).where(
            internal_instance_data.c.instance_id == data["instance"]["id"],
            internal_instance_data.c.run_id == actual["id"])).mappings().one()
        assert typed["fingerprint"] == contract["typed_fingerprint"] == fingerprint(typed["data"])
        assert typed["data"]["result"] == contract["output"]
        assert typed["version"] == actual["result_version"] == version
        assert not c.execute(select(attempts.c.id)).first()
    return contract


def test_actual_two_inputs_same_instance_explicit_review_cold_recovery_no_inheritance(env, evidence):
    facts, record = evidence
    data = flow(env)
    path = data["path"]
    initial = state(env[2], path)
    assert initial["owner_acceptance"] == "PENDING" and initial["sequence"] == 0
    product_before = snapshot(env[0], owner=False)
    review, prepared = prepare(env[2], path)
    first = assert_actual_contract(env, data, review["payload"]["contract"], version=1)
    intent = decision(review)
    incomplete = {**intent, "request_key": "incomplete-declaration", "choices": intent["choices"][:-1]}
    rejected = env[2].post(path + "-requests", json=incomplete)
    assert rejected.status_code in (400, 409, 422), rejected.text
    assert state(env[2], path)["sequence"] == 1
    accepted = env[2].post(path + "-requests", json=intent)
    assert accepted.status_code == 201, accepted.text
    assert state(env[2], path)["owner_acceptance"] == "ACCEPTED"
    assert snapshot(env[0], owner=False) == product_before
    cold = Store(env[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, env[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            client.event_hooks["response"].append(record)
            before_recovery = snapshot(cold)
            recovered_preview = state(client, path, prepared["request_key"])["recovered"]
            assert recovered_preview == review
            recovered = state(client, path, intent["request_key"])
            assert recovered["owner_acceptance"] == "ACCEPTED"
            assert recovered["recovered"]["payload"]["request"] == intent
            assert recovered["recovered"]["id"] == accepted.json()["record"]["id"]
            assert client.post(path + "-requests", json=intent).json()["record"] == accepted.json()["record"]
            changed = copy.deepcopy(intent)
            changed["choices"][0]["reason"] = "A distinct explicit intent"
            assert client.post(path + "-requests", json=changed).status_code == 409
            assert snapshot(cold) == before_recovery
    finally:
        cold.engine.dispose()
    original_history = owner_rows(env[0], data["run_id"])
    value = dict(term_a="Violet", term_b="Amber", emit_report=True)
    second_run = enqueue(env, data["release"], data["instance"], value, "owner-second-input")
    duplicate_before = snapshot(env[0])
    duplicate = env[2].post(f"/api/internal/instances/{data['instance']['id']}/runs", json=dict(
        expected_revision=data["instance"]["revision"],
        expected_release_fingerprint=data["release"]["fingerprint"],
        input=value, request_key="owner-second-input"))
    assert duplicate.status_code == 202 and duplicate.json()["run_id"] == second_run, duplicate.text
    assert duplicate.json()["cached"] and snapshot(env[0]) == duplicate_before
    once(env)
    response = inspect(env, data["instance"], second_run)
    assert response.status_code == 200 and response.json()["status"] == "SUCCEEDED", response.text
    second_path = path.replace(data["run_id"], second_run)
    second = state(env[2], second_path)
    assert second["owner_acceptance"] == "PENDING" and second["sequence"] == 0 and second["history"] == []
    second_data = {**data, "run_id": second_run, "input": value, "result": response.json()}
    second_contract = assert_actual_contract(env, second_data, second["current"], version=2)
    assert second_contract["output"]["text"] != first["output"]["text"]
    old = state(env[2], path, intent["request_key"])
    assert old["owner_acceptance"] == "STALE" and not old["content_access"]
    assert "current" not in old and "payload" not in old["recovered"]
    assert owner_rows(env[0], data["run_id"]) == original_history
    assert owner_rows(env[0], second_run) == {"natural_owner_records": [], "natural_owner_seals": []}
    with env[0].tx() as c:
        assert c.execute(select(runs.c.status).where(runs.c.id.in_([
            data["run_id"], second_run]))).scalars().all() == ["SUCCEEDED", "SUCCEEDED"]
    facts.update(first_contract=first, accepted=accepted.json(), original_history=original_history,
        cold_preview=recovered_preview, cold_decision=recovered, second_contract=second_contract,
        old_state=old, second_state=second, actual_complete_runs=2,
        same_business_instance=data["instance"]["id"], owner_history_preserved=True,
        source_grants_unchanged=True, no_additional_product_writes_from_declarations=True)


def test_partial_false_branch_has_no_report_and_cannot_be_signed(env, evidence):
    facts, _ = evidence
    data = flow(env, emit=False)
    value = data["result"]
    assert value["result"] is None and value["result_version"] is None
    assert [step["status"] for step in value["steps"]] == ["VERIFIED"] * 3 + ["SKIPPED"]
    pending = state(env[2], data["path"])
    assert pending["owner_acceptance"] == "PENDING" and not pending["content_access"]
    assert "current" not in pending and pending["sequence"] == 0
    before = snapshot(env[0])
    response = env[2].post(data["path"] + "-requests", json=dict(command="PREPARE",
        request_key="do-not-sign-partial", expected_sequence=0,
        expected_contract_fingerprint="0" * 64))
    assert response.status_code == 409, response.text
    assert snapshot(env[0]) == before
    with env[0].tx() as c:
        assert len(c.execute(select(operations.c.id).where(operations.c.run_id == data["run_id"])).all()) == 3
        assert not c.execute(select(internal_instance_data.c.run_id).where(
            internal_instance_data.c.instance_id == data["instance"]["id"])).first()
        assert not c.execute(select(attempts.c.id)).first()
    facts.update(actual_partial_run=data["run_id"], steps=value["steps"], state=pending,
        prepare=response.json(), owner_ledger_untouched=True, missing_report_rejected=True)


def test_foreign_account_and_instance_rejected_before_private_body(env, evidence):
    facts, _ = evidence
    data = flow(env)
    review, prepared = prepare(env[2], data["path"])
    other = env[2].post(f"/api/internal/releases/{data['release']['id']}/instances", json=dict(
        expected_release_fingerprint=data["release"]["fingerprint"], request_key="owner-other-instance"))
    assert other.status_code == 201, other.text
    wrong = data["path"].replace(data["instance"]["id"], other.json()["id"])
    before = snapshot(env[0])
    checks = []
    original_auth = env[2].headers["Authorization"]
    try:
        with TypedPrivateBarrier(env[0], data["run_id"], review["payload"]["contract"]["app_run_id"],
                data["resource"]) as barrier:
            barrier.rules["natural_owner_records"] = (natural_owner_records, "id", {review["id"]}, {"payload"})
            old_path = data["path"].replace("/text-owner-review", "/spec-owner-review")
            stop_body = dict(command="CANCEL", request_key="old-family-stop", expected_sequence=1,
                target_id=review["id"], target_fingerprint=review["fingerprint"],
                reason="This old family endpoint must not cancel a four-step review")
            for method, body in [("GET", None), ("POST", prepared), ("POST", stop_body)]:
                response = env[2].request(method,
                    old_path + ("-requests" if method == "POST" else ""),
                    **({"json": body} if body else {}))
                assert response.status_code == 400, response.text
                assert response.json()["error"]["code"] == "UNSUPPORTED_CAPABILITY"
                checks.append(dict(scope="old-natural-family", method=method,
                    request=body, status=response.status_code, response=response.json()))
            for label, auth, path in [
                ("wrong-instance", original_auth, wrong),
                ("other-account", "Bearer synthetic-test-B", data["path"]),
            ]:
                env[2].headers["Authorization"] = auth
                for method in ("GET", "POST"):
                    response = env[2].request(method,
                        path + ("-requests" if method == "POST" else ""),
                        **({"json": decision(review, "foreign-decision")} if method == "POST" else {}))
                    assert response.status_code in (403, 409), response.text
                    checks.append(dict(scope=label, method=method, status=response.status_code,
                        response=response.json()))
            assert not barrier.blocked and not barrier.full_binding_reads
            facts.update(checks=checks, blocked=barrier.blocked,
                full_binding_reads=barrier.full_binding_reads, statements=barrier.statements,
                scope_before_private_bodies=True)
    finally:
        env[2].headers["Authorization"] = original_auth
    assert snapshot(env[0]) == before


def test_revoked_material_returns_metadata_and_allows_metadata_cancel(env, evidence):
    facts, _ = evidence
    data = flow(env)
    review, _ = prepare(env[2], data["path"])
    with env[0].tx() as c:
        victim = c.execute(select(grants).where(grants.c.principal_id == data["instance"]["runtime_id"],
            grants.c.resource_id == data["resource"], grants.c.tool_ref == "resource.read")).mappings().one()
        c.execute(update(grants).where(grants.c.id == victim["id"]).values(
            revoked=True, revision=victim["revision"] + 1))
    with TypedPrivateBarrier(env[0], data["run_id"], review["payload"]["contract"]["app_run_id"],
            data["resource"]) as barrier:
        barrier.rules["natural_owner_records"] = (natural_owner_records, "id", {review["id"]}, {"payload"})
        stale = state(env[2], data["path"], "owner-preview")
        assert stale["owner_acceptance"] == "STALE" and not stale["content_access"]
        assert "current" not in stale and "record" not in stale and "payload" not in stale["recovered"]
        rejected = env[2].post(data["path"] + "-requests", json=decision(review))
        assert rejected.status_code in (403, 409), rejected.text
        stop_body = dict(command="CANCEL", request_key="metadata-stop", expected_sequence=1,
            target_id=review["id"], target_fingerprint=review["fingerprint"],
            reason="Stop this exact review after material read authority was revoked")
        stopped = env[2].post(data["path"] + "-requests", json=stop_body)
        assert stopped.status_code == 201, stopped.text
        final = state(env[2], data["path"], "metadata-stop")
        assert final["owner_acceptance"] == "CANCELLED" and not final["content_access"]
        assert "payload" not in final["recovered"]
        assert not barrier.blocked and not barrier.full_binding_reads
        facts.update(stale=stale, rejected=rejected.json(), stopped=stopped.json(), final=final,
            blocked=barrier.blocked, full_binding_reads=barrier.full_binding_reads,
            statements=barrier.statements, authorization_before_private_bodies=True,
            metadata_stop_after_revocation=True)


@pytest.mark.parametrize("change", ["goal", "source", "typed"])
def test_changed_current_context_invalidates_preview_before_owner_payload(env, evidence, change):
    facts, _ = evidence
    data = flow(env)
    review, _ = prepare(env[2], data["path"])
    with env[0].tx() as c:
        if change == "goal":
            c.execute(update(goal_cards).where(goal_cards.c.id == data["card"]["id"]).values(
                version=data["card"]["version"] + 1))
        elif change == "source":
            content = SOURCE + "Cobalt synthetic material drift\n"
            c.execute(update(resources).where(resources.c.id == data["resource"]).values(
                content=content, hash=hashlib.sha256(content.encode("utf-8")).hexdigest()))
        else:
            c.execute(update(internal_instance_data).where(
                internal_instance_data.c.run_id == review["payload"]["contract"]["app_run_id"]).values(
                fingerprint="0" * 64))
    before = snapshot(env[0])
    # Verification may read currently authorized source/typed execution proof to
    # discover drift. Only the obsolete owner payload is barred in this case.
    with PrivateReadBarrier(env[0], set()) as barrier:
        barrier.rules["natural_owner_records"] = (natural_owner_records, "id", {review["id"]}, {"payload"})
        stale = state(env[2], data["path"], "owner-preview")
        assert stale["owner_acceptance"] == "STALE" and not stale["content_access"]
        assert "current" not in stale and "record" not in stale and "payload" not in stale["recovered"]
        response = env[2].post(data["path"] + "-requests", json=decision(review))
        assert response.status_code in (400, 409), response.text
        assert not barrier.blocked
        facts.update(change=change, state=stale, rejected=response.json(), blocked=barrier.blocked,
            evaluated=barrier.evaluated, statements=barrier.statements,
            obsolete_owner_payload_not_read=True)
    assert snapshot(env[0]) == before
