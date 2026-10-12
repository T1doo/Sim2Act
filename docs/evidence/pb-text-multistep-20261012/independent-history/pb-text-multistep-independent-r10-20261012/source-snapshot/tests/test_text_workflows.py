"""Actual closed non-CSV task, persisted four receipts and cold exact extraction."""

import copy
import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, insert, select, update

from sim2act import text_workflows as flow
from sim2act.api import create_app
from sim2act.contracts import Limits
from sim2act.db import (
    Store,
    app_drafts,
    attempts,
    delivery_graph_requests,
    events,
    fingerprint,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_run_bindings,
    new_id,
    operation_intents,
    operations,
    runs,
)
from sim2act.worker import Worker


class NoModel:
    def request(self, *args, **kwargs):
        raise AssertionError("Four-step text must never request a model")


def material(env, content="Amber assigned to Lee\nViolet due Friday\nAmber review pending\n", fmt="txt"):
    client, pid = env[2], env[5]
    response = client.post(f"/api/projects/{pid}/resources", json=dict(name="unseen." + fmt, format=fmt, content=content))
    assert response.status_code == 201, response.text
    rid = response.json()["id"]
    body = dict(title="Own four-node task", goal="Retrieve both terms independently and assemble exact citations when selected",
        known=["Literal case-sensitive retrieval"], assumptions=["User selects both terms"],
        unresolved=["Semantic meaning unverified"], constraints=["Keep complete lines", "Never summarize"],
        acceptance_checks=["Compare both independent citation sets to source", "Check report branch separately"], resource_refs=[rid])
    made = client.post(f"/api/projects/{pid}/goal-cards", json=body)
    assert made.status_code == 201, made.text
    return rid, made.json()


def draft(env, rid=None, card=None, source_run=None, key="create-four"):
    if rid is None:
        rid, card = material(env)
    client, pid = env[2], env[5]
    reply = client.get(f"/api/projects/{pid}/text-workflow-options", params=dict(card_id=card["id"], **(dict(source_run_id=source_run) if source_run else {})))
    assert reply.status_code == 200, reply.text
    p = reply.json()
    body = dict(card_id=card["id"], expected_goal_version=p["goal_version"], expected_goal_fingerprint=p["goal_fingerprint"],
        resource_id=rid, expected_source_hash=p["source_hash"], source_run_id=source_run,
        expected_proof_fingerprint=p["source_proof_fingerprint"], name="Actual two-search task",
        consent="CREATE_THIS_EXACT_FOUR_STEP_TEXT_APP_WITH_THIS_CURRENT_GOAL", request_key=key)
    result = client.post(f"/api/projects/{pid}/text-workflows", json=body)
    assert result.status_code == 201, result.text
    return result.json(), body


def instance(env, aid, sample=None):
    client = env[2]
    reply = client.get(f"/api/apps/{aid}")
    assert reply.status_code == 200, reply.text
    value = reply.json()
    sample = sample or dict(term_a="Amber", term_b="Violet", emit_report=True)
    approval = client.post(f"/api/internal/apps/{aid}/release-approvals", json=dict(expected_draft_fingerprint=value["fingerprint"], sample_input=sample))
    assert approval.status_code == 201, approval.text
    a = approval.json()
    reply = client.post(f"/api/internal/approvals/{a['id']}/commit", json=dict(fingerprint=a["fingerprint"]))
    assert reply.status_code == 200, reply.text
    release = reply.json()
    reply = client.post(f"/api/internal/releases/{release['id']}/instances", json=dict(expected_release_fingerprint=release["fingerprint"], request_key="new-instance"))
    assert reply.status_code == 201, reply.text
    return release, reply.json()


def enqueue(env, release, inst, value=None, key="actual-task"):
    reply = env[2].post(f"/api/internal/instances/{inst['id']}/runs", json=dict(expected_revision=inst["revision"],
        expected_release_fingerprint=release["fingerprint"], input=value or dict(term_a="Amber", term_b="Violet", emit_report=True), request_key=key))
    assert reply.status_code == 202, reply.text
    return reply.json()["run_id"]


def inspect(env, inst, rid):
    return env[2].get(f"/api/internal/instances/{inst['id']}/runs/{rid}")


def once(env, settings=None):
    worker = Worker(env[0], settings or env[1])
    worker.model = NoModel()
    assert worker.once()
    return worker


@pytest.mark.parametrize("fmt", ["txt", "md"])
@pytest.mark.parametrize("emit", [True, False])
def test_actual_four_nodes_and_partial_branch(env, fmt, emit):
    rid, card = material(env, fmt=fmt)
    made, _ = draft(env, rid, card)
    release, inst = instance(env, made["id"])
    job_id = enqueue(env, release, inst, dict(term_a="Amber", term_b="Violet", emit_report=emit))
    once(env)
    reply = inspect(env, inst, job_id)
    assert reply.status_code == 200, reply.text
    value = reply.json()
    assert value["status"] == ("SUCCEEDED" if emit else "PARTIAL"), value
    assert [s["step_id"] for s in value["steps"]] == flow.STEPS
    assert [s["status"] for s in value["steps"]] == ["VERIFIED"] * 3 + ["VERIFIED" if emit else "SKIPPED"]
    with env[0].tx() as c:
        ops = c.execute(select(operations).where(operations.c.run_id == job_id)).mappings().all()
        assert len(ops) == (4 if emit else 3)
        assert len({o["id"] for o in ops}) == len(ops)
        assert all(o["status"] == "VERIFIED" for o in ops)
        assert all(c.execute(select(operation_intents.c.request).where(operation_intents.c.operation_id == o["id"])).scalar() for o in ops)
    proof = env[2].get(f"/api/internal/app-run-jobs/{job_id}/text-workflow-proof")
    assert proof.status_code == (200 if emit else 409), proof.text
    if emit:
        assert [q["start_line"] for q in value["result"]["citations_a"]] == [1, 3]
        assert [q["start_line"] for q in value["result"]["citations_b"]] == [2]
        assert value["result_version"] == 1
    else:
        assert value["result"] is None and value["result_version"] is None and value["known_effects"] == []


def test_actual_task_extracted_to_unseen_material_cold_no_model(env):
    made, body = draft(env)
    release, inst = instance(env, made["id"])
    source_run = enqueue(env, release, inst)
    once(env)
    assert inspect(env, inst, source_run).json()["status"] == "SUCCEEDED"
    target_rid, target_card = material(env, "Cedar new owner\nQuartz tomorrow\nCedar reserved\n", "md")
    extracted, extract_body = draft(env, target_rid, target_card, source_run, "extract-four")
    assert extracted["id"] != made["id"] and extracted["owner_acceptance"] == "PENDING"
    target_release, target_instance = instance(env, extracted["id"], dict(term_a="Cedar", term_b="Quartz", emit_report=True))
    cold = Store(env[1].database_url, test_only=True)
    with TestClient(create_app(cold, env[1])) as client:
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        cold_env = (cold, env[1], client, *env[3:])
        recovered = client.get(f"/api/projects/{env[5]}/text-workflow-requests/extract-four")
        assert recovered.status_code == 200 and recovered.json()["id"] == extracted["id"]
        job_id = enqueue(cold_env, target_release, target_instance, dict(term_a="Quartz", term_b="Cedar", emit_report=True), "new-input-cold")
        once(cold_env)
        result = inspect(cold_env, target_instance, job_id)
        assert result.status_code == 200, result.text
        assert result.json()["status"] == "SUCCEEDED" and result.json()["result"]["resource_id"] == target_rid
        assert result.json()["result"]["term_a"] == "Quartz"
        assert all("Amber" not in q["quote"] for q in result.json()["result"]["citations_b"])
    cold.engine.dispose()


@pytest.mark.parametrize("terms", [("missing-a", "missing-b"), ("Amber", "Amber")])
def test_no_hits_and_equal_terms_still_two_actual_searches(env, terms):
    made, _ = draft(env)
    release, inst = instance(env, made["id"])
    rid = enqueue(env, release, inst, dict(term_a=terms[0], term_b=terms[1], emit_report=True))
    once(env)
    reply = inspect(env, inst, rid)
    assert reply.status_code == 200 and reply.json()["status"] == "SUCCEEDED", reply.text
    value = reply.json()["result"]
    if terms[0] == "missing-a":
        assert value["citations_a"] == value["citations_b"] == []
        assert value["text"].count("No literal matches") == 2
    with env[0].tx() as c:
        ops = c.execute(select(operations).where(operations.c.run_id == rid, operations.c.call_id.in_(["lookup_a", "lookup_b"]))).mappings().all()
        assert len(ops) == 2 and ops[0]["id"] != ops[1]["id"]


@pytest.mark.parametrize("bad", [1, "true", None])
def test_invalid_boolean_failed_history_no_success(env, bad):
    made, _ = draft(env)
    release, inst = instance(env, made["id"])
    rid = enqueue(env, release, inst, dict(term_a="Amber", term_b="Violet", emit_report=bad))
    once(env)
    with env[0].tx() as c:
        job = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert job["status"] == "FAILED" and job["error"]["code"] == "INVALID_INPUT"
        assert c.execute(select(operations.c.id).where(operations.c.run_id == rid)).first() is None
        assert c.execute(select(internal_instance_data.c.version).where(internal_instance_data.c.instance_id == inst["id"])).first() is None
    reply = inspect(env, inst, rid)
    assert reply.status_code == 200 and reply.json()["status"] == "FAILED", reply.text
    assert env[2].get(f"/api/internal/instances/{inst['id']}").status_code == 200


@pytest.mark.parametrize("mutation", ["delete_typed", "delete_node", "wrong_quote", "wrong_intent"])
def test_actual_success_cannot_survive_history_corruption(env, mutation):
    made, _ = draft(env)
    release, inst = instance(env, made["id"])
    rid = enqueue(env, release, inst)
    once(env)
    assert inspect(env, inst, rid).json()["status"] == "SUCCEEDED"
    with env[0].tx() as c:
        op = c.execute(select(operations).where(operations.c.run_id == rid, operations.c.call_id == "lookup_b")).mappings().one()
        if mutation == "delete_typed":
            c.execute(delete(internal_instance_data).where(internal_instance_data.c.instance_id == inst["id"]))
        elif mutation == "delete_node":
            c.execute(delete(operations).where(operations.c.id == op["id"]))
        elif mutation == "wrong_quote":
            value = copy.deepcopy(op["receipt"])
            value["data"]["citations"][0]["quote"] = "forged"
            value["output_fingerprint"] = fingerprint(value["data"])
            c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=value))
        else:
            value = c.execute(select(operation_intents.c.request).where(operation_intents.c.operation_id == op["id"])).scalar()
            value["args"]["term"] = "Amber"
            c.execute(update(operation_intents).where(operation_intents.c.operation_id == op["id"]).values(request=value))
            c.execute(update(operations).where(operations.c.id == op["id"]).values(fingerprint=fingerprint(value)))
    expected = 400 if mutation == "wrong_quote" else 409
    response = inspect(env, inst, rid)
    assert response.status_code == expected and response.json()["error"]["code"] == ("VERIFICATION_FAILED" if mutation == "wrong_quote" else "VERSION_CONFLICT")
    assert env[2].get(f"/api/internal/instances/{inst['id']}").status_code == expected
    assert env[2].get(f"/api/internal/app-run-jobs/{rid}/text-workflow-proof").status_code == expected


def claimed(env, rid):
    worker = Worker(env[0], env[1], NoModel())
    run = worker.store.claim(worker.id, worker.s.lease_seconds)
    assert run and run["id"] == rid
    return worker, run


@pytest.mark.parametrize("who", ["user", "app"])
def test_permission_change_between_real_nodes_no_partial_success(env, who):
    made, body = draft(env)
    release, inst = instance(env, made["id"])
    rid = enqueue(env, release, inst)
    worker, run = claimed(env, rid)
    assert flow.advance(worker, run)
    principal = env[3] if who == "user" else inst["runtime_id"]
    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.principal_id == principal, grants.c.resource_id == body["resource_id"],
            grants.c.tool_ref == "resource.read").values(revoked=True))
    flow.process_job(worker, run)
    with env[0].tx() as c:
        row = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert row["status"] == "WAITING_RESOURCE" and row["result"] is None
        assert len(c.execute(select(operations.c.id).where(operations.c.run_id == rid)).all()) == 1
        assert c.execute(select(internal_instance_data.c.version).where(internal_instance_data.c.instance_id == inst["id"])).first() is None
    # Read revoked content fails; owner cancel remains possible via metadata only.
    assert inspect(env, inst, rid).status_code == 403
    control = env[2].get(f"/api/internal/instances/{inst['id']}/runs/{rid}/control-status")
    assert control.status_code == 200 and control.json()["content_access"] is False
    stop = env[2].post(f"/api/internal/instances/{inst['id']}/runs/{rid}/commands",
        json=dict(command="cancel", version=row["version"]))
    assert stop.status_code == 200 and stop.json()["status"] == "CANCELLED", stop.text


def test_current_goal_change_between_real_nodes_blocks_commit(env):
    made, body = draft(env)
    release, inst = instance(env, made["id"])
    rid = enqueue(env, release, inst)
    worker, run = claimed(env, rid)
    assert flow.advance(worker, run)
    card = env[2].get(f"/api/goal-cards/{body['card_id']}").json()
    content = card["content"]
    content["title"] = "Changed goal after first real receipt"
    reply = env[2].put(f"/api/goal-cards/{body['card_id']}", json=dict(**content, expected_version=card["version"]))
    assert reply.status_code == 200, reply.text
    flow.process_job(worker, run)
    with env[0].tx() as c:
        row = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert row["status"] == "FAILED" and row["error"]["code"] == "VERSION_CONFLICT"
        assert row["result"] is None
        assert len(c.execute(select(operations.c.id).where(operations.c.run_id == rid)).all()) == 1


def test_cold_prefix_resume_preserves_operations_and_final_cas(env):
    made, _ = draft(env)
    release, inst = instance(env, made["id"])
    rid = enqueue(env, release, inst)
    worker, run = claimed(env, rid)
    assert flow.advance(worker, run)
    with env[0].tx() as c:
        first = c.execute(select(operations).where(operations.c.run_id == rid)).mappings().one()
        c.execute(update(runs).where(runs.c.id == rid).values(lease_until=0))
    cold = Store(env[1].database_url, test_only=True)
    fresh = Worker(cold, env[1], NoModel())
    claimed_run = cold.claim(fresh.id, fresh.s.lease_seconds)
    assert claimed_run["fence"] > run["fence"]
    from sim2act.errors import DomainError
    with pytest.raises(DomainError):
        flow.advance(worker, run)
    flow.process_job(fresh, claimed_run)
    reply = inspect(env, inst, rid)
    assert reply.status_code == 200 and reply.json()["status"] == "SUCCEEDED", reply.text
    with cold.tx() as c:
        saved = c.execute(select(operations).where(operations.c.id == first["id"])).mappings().one()
        assert dict(saved) == dict(first)
        assert len(c.execute(select(operations.c.id).where(operations.c.run_id == rid)).all()) == 4
        assert len(c.execute(select(internal_instance_data.c.version).where(internal_instance_data.c.instance_id == inst["id"])).all()) == 1
    cold.engine.dispose()


def test_queued_cancel_and_unrun_instance_are_honest_empty_history(env):
    made, _ = draft(env)
    release, inst = instance(env, made["id"])
    assert env[2].get(f"/api/internal/instances/{inst['id']}").status_code == 200
    rid = enqueue(env, release, inst)
    reply = inspect(env, inst, rid)
    assert reply.status_code == 200, reply.text
    stop = env[2].post(f"/api/internal/instances/{inst['id']}/runs/{rid}/commands",
        json=dict(command="cancel", version=reply.json()["version"]))
    assert stop.status_code == 200 and stop.json()["status"] == "CANCELLED"
    worker = Worker(env[0], env[1], NoModel())
    assert worker.once() is False
    assert inspect(env, inst, rid).json()["steps"] == []
    assert env[2].get(f"/api/internal/instances/{inst['id']}").status_code == 200


def test_runtime_lower_budget_keeps_real_prefix_no_success(env):
    made, _ = draft(env)
    release, inst = instance(env, made["id"])
    rid = enqueue(env, release, inst)
    once(env, replace(env[1], max_tools=3))
    with env[0].tx() as c:
        row = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert row["status"] == "FAILED" and row["result"] is None
        assert row["error"]["code"] == "VERSION_CONFLICT"
        assert c.execute(select(internal_instance_data.c.version).where(internal_instance_data.c.instance_id == inst["id"])).first() is None


@pytest.mark.parametrize("change", ["condition", "wiring", "effect", "limits", "locks", "ref", "schema"])
def test_private_compiler_rejects_entire_noncanonical_contract(env, change):
    made, _ = draft(env)
    with env[0].tx() as c:
        value = copy.deepcopy(c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == made["id"])).scalar())
    if change == "condition":
        value["manifest"]["workflow"][3]["when"]["value"] = False
    elif change == "wiring":
        value["manifest"]["workflow"][2]["inputs"]["term"]["field"] = "term_a"
    elif change == "effect":
        value["actions"][3]["effect"] = "project_write"
    elif change == "limits":
        value["actions"][1]["limits"]["max_tools"] = 2
    elif change == "locks":
        value["manifest"]["dependency_lock"].pop()
    elif change == "ref":
        value["actions"][3]["executor"]["ref"] = "arbitrary.python"
    else:
        value["actions"][2]["output_schema"]["properties"]["revision"]["type"] = "boolean"
    from sim2act.errors import DomainError
    with pytest.raises(DomainError):
        flow.compile_candidate(value, Limits(**{k: getattr(env[1], k) for k in Limits.model_fields}))


def test_unknown_creation_recovery_read_only_and_wrong_owner(env):
    made, body = draft(env)
    before = env[2].get(f"/api/projects/{env[5]}/text-workflow-requests/{body['request_key']}")
    assert before.status_code == 200 and before.json()["id"] == made["id"]
    unknown = env[2].get(f"/api/projects/{env[5]}/text-workflow-requests/unseen-original-key")
    assert unknown.status_code == 400 and unknown.json()["error"]["code"] == "OUTCOME_UNKNOWN"
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    assert env[2].get(f"/api/projects/{env[5]}/text-workflow-requests/{body['request_key']}").status_code == 403
    assert env[2].get(f"/api/apps/{made['id']}").status_code == 403


@pytest.mark.parametrize("number", [True, 1.0])
def test_app_run_output_strict_numbers_reject_width_equality(env, number):
    made, _ = draft(env)
    release, inst = instance(env, made["id"])
    rid = enqueue(env, release, inst)
    once(env)
    with env[0].tx() as c:
        aid = c.execute(select(internal_run_bindings.c.app_run_id).where(internal_run_bindings.c.run_id == rid)).scalar()
        output = c.execute(select(internal_app_runs.c.output).where(internal_app_runs.c.id == aid)).scalar()
        output["citations_a"][0]["start_line"] = number
        c.execute(update(internal_app_runs).where(internal_app_runs.c.id == aid).values(output=output))
    reply = inspect(env, inst, rid)
    assert reply.status_code in {400, 409}, reply.text


@pytest.mark.parametrize("deleted", ["binding", "app_run"])
def test_failed_history_missing_independent_anchor_rejected(env, deleted):
    made, _ = draft(env)
    release, inst = instance(env, made["id"])
    rid = enqueue(env, release, inst, dict(term_a="", term_b="Violet", emit_report=True))
    once(env)
    with env[0].tx() as c:
        binding = c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == rid)).mappings().one()
        assert c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar() == "FAILED"
        table, where = (internal_run_bindings, internal_run_bindings.c.run_id == rid) if deleted == "binding" else (internal_app_runs, internal_app_runs.c.id == binding["app_run_id"])
        c.execute(delete(table).where(where))
    reply = env[2].get(f"/api/internal/instances/{inst['id']}")
    assert reply.status_code == 409, reply.text


@pytest.mark.parametrize("site", ["scope", "job_binding", "cross_project"])
def test_rejected_scope_never_evaluates_original_private_cells(env, site):
    from sql_private_barrier import PrivateReadBarrier


    made, body = draft(env)
    release, inst = instance(env, made["id"])
    rid = enqueue(env, release, inst)
    once(env)
    other, other_card = None, None
    if site == "cross_project":
        other = env[2].post("/api/projects", json=dict(name="Same owner, other project")).json()["id"]
        other_resource = env[2].post(f"/api/projects/{other}/resources",
            json=dict(name="target.txt", format="txt", content="Jade independent\n")).json()["id"]
        other_card = env[2].post(f"/api/projects/{other}/goal-cards", json=dict(title="Other valid own target",
            goal="Independent literals", known=[], assumptions=[], unresolved=[], constraints=["No inference"],
            acceptance_checks=["Exact citations"], resource_refs=[other_resource])).json()["id"]
    with env[0].tx() as c:
        if site == "scope":
            c.execute(update(grants).where(grants.c.resource_id == body["resource_id"],
                grants.c.principal_id == env[3], grants.c.tool_ref == "resource.read").values(revoked=True))
            row = c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.app_id == made["id"],
                delivery_graph_requests.c.kind == flow.META)).mappings().one()
            value = copy.deepcopy(row["snapshot"])
            value["request"]["resource_id"] = env[6]
            value["response"]["resource_id"] = env[6]
            c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.app_id == made["id"],
                delivery_graph_requests.c.kind.in_([flow.META, flow.META + "_seal"])).values(snapshot=value, fingerprint=fingerprint(value),
                    request_fingerprint=fingerprint(value["request"])))
            c.execute(insert(grants).values(id=new_id("grant"), principal_id=inst["runtime_id"],
                project_id=env[5], resource_id=env[6], tool_ref="resource.read", expires_at=time.time() + 1000,
                revision=1, revoked=False))
        elif site == "job_binding":
            c.execute(update(grants).where(grants.c.resource_id == body["resource_id"],
                grants.c.principal_id == env[3], grants.c.tool_ref == "resource.read").values(revoked=True))
            c.execute(update(internal_run_bindings).where(internal_run_bindings.c.run_id == rid).values(app_run_id="foreign-id"))
    protected = PrivateReadBarrier(env[0], {rid}, {body["resource_id"]})
    protected.rules.update({
        "app_drafts": (app_drafts, "id", {made["id"]}, {"candidate"}),
        "internal_app_runs": (internal_app_runs, "instance_id", {inst["id"]}, {"input", "output", "error"}),
        "internal_run_bindings": (internal_run_bindings, "run_id", {rid}, {"snapshot"}),
        "internal_instance_data": (internal_instance_data, "instance_id", {inst["id"]}, {"data"}),
    })
    # JSON projections are metadata but SQLite evaluates the underlying JSON cell;
    # omit candidate and binding from this barrier, retain all full text/result cells.
    protected.rules.pop("app_drafts")
    protected.rules.pop("internal_run_bindings")
    with protected:
        if site == "scope":
            reply = env[2].get(f"/api/apps/{made['id']}")
        elif site == "job_binding":
            reply = inspect(env, inst, rid)
        else:
            reply = env[2].get(f"/api/projects/{other}/text-workflow-options",
                params=dict(card_id=other_card, source_run_id=rid))
        assert reply.status_code in {403, 409}, reply.text
        assert protected.blocked == []


def test_missing_typed_version_pointer_rejected(env):
    made, _ = draft(env)
    release, inst = instance(env, made["id"])
    enqueue(env, release, inst)
    once(env)
    with env[0].tx() as c:
        from sim2act.db import internal_instances
        c.execute(update(internal_instances).where(internal_instances.c.id == inst["id"]).values(data_version=0))
    assert env[2].get(f"/api/internal/instances/{inst['id']}").status_code == 409


@pytest.mark.parametrize("which", ["numeric_input", "attempt_ledger", "queued_after_step", "error"])
def test_independent_review_persisted_execution_corruption_rejected(env, which):
    made, _ = draft(env)
    release, inst = instance(env, made["id"])
    rid = enqueue(env, release, inst)
    if which == "queued_after_step":
        worker, run = claimed(env, rid)
        assert flow.advance(worker, run)
    else:
        once(env)
    with env[0].tx() as c:
        aid = c.execute(select(internal_run_bindings.c.app_run_id).where(internal_run_bindings.c.run_id == rid)).scalar()
        if which == "numeric_input":
            value = c.execute(select(internal_app_runs.c.input).where(internal_app_runs.c.id == aid)).scalar()
            value["emit_report"] = 1
            c.execute(update(internal_app_runs).where(internal_app_runs.c.id == aid).values(input=value))
        elif which == "attempt_ledger":
            c.execute(insert(attempts).values(id=new_id("attempt"), run_id=rid, created_at=time.time(),
                mode="mock", request_model="intern-s2", status="SUCCEEDED", reserved_tokens=1))
        elif which == "queued_after_step":
            c.execute(update(internal_app_runs).where(internal_app_runs.c.id == aid).values(status="QUEUED"))
        else:
            c.execute(update(internal_app_runs).where(internal_app_runs.c.id == aid).values(error=dict(code="UNEXPLAINED")))
    assert inspect(env, inst, rid).status_code == 409
    assert env[2].get(f"/api/internal/instances/{inst['id']}").status_code == 409


def test_deleted_run_scope_and_accepted_bad_binding_revocation_before_private_read(env):
    from sql_private_barrier import PrivateReadBarrier
    made, body = draft(env)
    release, inst = instance(env, made["id"])
    rid = enqueue(env, release, inst)
    once(env)
    with env[0].tx() as c:
        c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id == rid,
            delivery_graph_requests.c.kind.in_([flow.RUN_META, flow.RUN_META + "_seal"])))
        c.execute(delete(events).where(events.c.run_id == rid, events.c.kind == "ACCEPTED"))
        c.execute(update(internal_run_bindings).where(internal_run_bindings.c.run_id == rid).values(app_run_id="bad-pointer"))
        c.execute(update(grants).where(grants.c.resource_id == body["resource_id"],
            grants.c.principal_id == env[3], grants.c.tool_ref == "resource.read").values(revoked=True))
    with PrivateReadBarrier(env[0], {rid}, {body["resource_id"]}) as barrier:
        reply = inspect(env, inst, rid)
        assert reply.status_code == 403, reply.text
        assert barrier.blocked == []
