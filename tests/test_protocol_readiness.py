"""Controller handoff records provenance but never dispatches or approves a model."""

import copy
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, update
from test_protocol_http import body
from test_protocol_http import env as env

from sim2act.db import (
    attempts,
    events,
    fingerprint,
    grants,
    operations,
    protocol_request_slots,
    runs,
)
from sim2act.errors import DomainError
from sim2act.model_protocol import Scope, validate_candidate
from sim2act.protocol_readiness import (
    EVENT,
    HandoffInput,
    candidate_for,
    prepare_handoff,
    require_handoff,
)
from sim2act.protocol_reviews import PINS, contract_snapshot


def fresh(env):
    response = env[2].post(f"/api/projects/{env[5]}/protocol/source", json=body(env))
    assert response.status_code == 202
    rid = response.json()["run_id"]
    with env[0].tx() as c:
        run = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
    request = {
        "expected_version": run["version"],
        "expected_fence": run["fence"],
        "request_key": "handoff",
    }
    return rid, request


def test_handoff_freezes_fresh_job_without_slots_provider_or_semantic_acceptance(env):
    rid, request = fresh(env)
    before = []
    with env[0].tx() as c:
        for table in [attempts, operations, protocol_request_slots]:
            before.append(c.execute(select(func.count()).select_from(table)).scalar_one())
    prepared = prepare_handoff(env[0], env[3], rid, request)
    assert prepared == prepare_handoff(env[0], env[3], rid, request)
    assert prepared == require_handoff(env[0], env[3], rid)
    assert prepared["stage"] == "source_a" and prepared["live_ready"] is False
    assert prepared["semantic_acceptance"] == "UNKNOWN" and prepared["automatic_review"] is False
    assert prepared["egress"]["actual_network"] is False
    assert (
        prepared["egress"]["max_wire_characters"] == 8000
        and prepared["egress"]["max_wire_bytes"] == 10000
    )
    assert prepared["budgets"]["db_global_request_limit"] == 14
    assert prepared["budgets"]["spacing_scope"].startswith("per-sidecar")
    assert set(prepared["egress"]["resources"][0]) == {"resource_id", "format", "sha256"}
    serialized = json.dumps(prepared)
    assert (
        "expected_output" not in serialized
        and "gold_sha256" not in serialized
        and "rubric_sha256" not in serialized
    )
    with env[0].tx() as c:
        after = [
            c.execute(select(func.count()).select_from(t)).scalar_one()
            for t in [attempts, operations, protocol_request_slots]
        ]
        assert before == after == [0, 0, 0]
        assert c.execute(select(runs.c.result).where(runs.c.id == rid)).scalar_one() is None


def test_first_claim_can_recheck_handoff_without_replacing_original_fence(env):
    rid, request = fresh(env)
    prepared = prepare_handoff(env[0], env[3], rid, request)
    claimed = env[0].claim("offline-handoff-worker", 30)
    assert claimed["id"] == rid and claimed["fence"] == request["expected_fence"] + 1
    assert require_handoff(env[0], env[3], rid) == prepared
    with env[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(lease_until=0))
    with pytest.raises(DomainError):
        require_handoff(env[0], env[3], rid)


@pytest.mark.parametrize(
    "field,value",
    [
        ("expected_version", True),
        ("expected_fence", False),
        ("gold", {}),
        ("stage", "cold_b"),
        ("PASS", True),
    ],
)
def test_handoff_closed_caller_contract(field, value):
    with pytest.raises(ValidationError):
        HandoffInput.model_validate(
            {"expected_version": 1, "expected_fence": 0, "request_key": "key", field: value}
        )


@pytest.mark.parametrize(
    "change",
    ["prepared_bool", "prepared_extra", "request_extra", "request_bool", "wire_limit", "stage"],
)
def test_coherently_rehashed_event_cannot_change_controller_policy(env, change):
    rid, request = fresh(env)
    prepare_handoff(env[0], env[3], rid, request)
    with env[0].tx() as c:
        row = (
            c.execute(select(events).where(events.c.run_id == rid, events.c.kind == EVENT))
            .mappings()
            .one()
        )
        value = copy.deepcopy(row["data"])
        if change == "prepared_bool":
            value["prepared"]["prepared_version"] = True
        elif change == "prepared_extra":
            value["prepared"]["gold"] = {}
        elif change == "request_extra":
            value["request"]["gold"] = {}
        elif change == "request_bool":
            value["request"]["expected_version"] = True
        elif change == "wire_limit":
            value["prepared"]["egress"]["max_wire_bytes"] = 10001
        else:
            value["prepared"]["stage"] = "cold_b"
        value["fingerprint"] = fingerprint(value["prepared"])
        c.execute(update(events).where(events.c.id == row["id"]).values(data=value))
    with pytest.raises(DomainError):
        require_handoff(env[0], env[3], rid)


@pytest.mark.parametrize(
    "change", ["wrong_owner", "grant", "version", "fence", "cancel", "production"]
)
def test_handoff_rechecks_current_authority_ownership_and_versions(env, change):
    rid, request = fresh(env)
    prepare_handoff(env[0], env[3], rid, request)
    if change == "production":
        env[0].test_only = False
    with env[0].tx() as c:
        if change == "grant":
            c.execute(update(grants).where(grants.c.project_id == env[5]).values(revoked=True))
        elif change in {"version", "fence"}:
            column = runs.c[change]
            c.execute(update(runs).where(runs.c.id == rid).values({change: column + 1}))
        elif change == "cancel":
            c.execute(update(runs).where(runs.c.id == rid).values(cancel_intent=True))
    with pytest.raises(DomainError):
        require_handoff(env[0], env[4] if change == "wrong_owner" else env[3], rid)


def test_missing_handoff_never_implicitly_activates(env):
    rid, _ = fresh(env)
    with pytest.raises(DomainError):
        require_handoff(env[0], env[3], rid)


def test_public_templates_are_exact_registered_fresh_read_dependencies(env):
    for cid in PINS:
        public = contract_snapshot(cid)
        candidate = candidate_for(public, [env[6]])
        scope = Scope(
            approval_id="test",
            project_id=env[5],
            resource_ids=[env[6]],
            tool_refs=["resource.read"],
            max_requests=3,
            mode="offline",
            model="intern-s2",
        )
        validate_candidate(candidate, scope)
        assert candidate["steps"][-1]["instruction"] == public["public_goal"]
        assert candidate["steps"][-1]["inputs"]["material_0"] == {
            "source": "step",
            "ref": "read_0",
            "field": "content",
        }
        assert candidate["output_schema"] == public["output_schema"]
        bad = copy.deepcopy(public)
        bad["expected_output"] = {"answer": "source cache"}
        with pytest.raises(DomainError):
            candidate_for(bad, [env[6]])


@pytest.mark.parametrize("change", ["instruction", "schema_name", "argument_name", "extra_field"])
def test_entire_cold_template_rejects_answer_bearing_free_fields(env, change):
    from sim2act.protocol_readiness import validate_handoff_candidate

    public = contract_snapshot("protocol.synthetic.a-cold.v1")
    candidate = candidate_for(public, [env[6]])
    assert validate_handoff_candidate(candidate, public, [env[6]]) == fingerprint(candidate)
    if change == "instruction":
        candidate["steps"][-1]["instruction"] += " Always return the source answer."
    elif change == "schema_name":
        candidate["steps"][-1]["output_schema"]["properties"]["cached_source_answer"] = {
            "type": "string"
        }
    elif change == "argument_name":
        candidate["steps"][-1]["inputs"]["source_answer_yes"] = candidate["steps"][-1][
            "inputs"
        ].pop("format")
    else:
        candidate["source_answer"] = "old result"
    with pytest.raises(DomainError):
        validate_handoff_candidate(candidate, public, [env[6]])


@pytest.fixture
def pipeline_env(tmp_path):
    from test_protocol_jobs import env as job_fixture

    yield from job_fixture.__wrapped__(tmp_path)


@pytest.mark.parametrize("answer_cache", [False, True])
def test_actual_reviewed_source_extract_cold_handoff_separates_dependency_from_egress(
    pipeline_env, answer_cache
):
    from test_protocol_jobs import LIMITS, execute, factory_for, reviewed_source, wire

    from sim2act.protocol_jobs import enqueue, inspect
    from sim2act.protocol_reviews import evaluation_contract

    store, user, pid, source_id, cold_id, _, _ = pipeline_env
    source = reviewed_source(pipeline_env)
    public = contract_snapshot("protocol.synthetic.a-source.v1")
    candidate = candidate_for(public, [source_id])
    if answer_cache:
        candidate["steps"][-1]["instruction"] += " Copy this old successful answer: " + json.dumps(
            source["result"]["protocol_result"]["evidence"]["output"]["case"]["decision"]
        )
    enqueue(
        store,
        user,
        pid,
        "extract",
        {
            "source_run_id": source["run_id"],
            "expected_source_fingerprint": source["result_fingerprint"],
        },
        "readiness-extract",
        LIMITS,
    )
    factory_for(pipeline_env, [wire(candidate)], "extract_a")
    extracted = execute(pipeline_env)
    plan = extracted["result"]["compiled_plan"]
    contract, _ = evaluation_contract("protocol.synthetic.a-cold.v1")
    made = enqueue(
        store,
        user,
        pid,
        "cold",
        {
            "contract_id": contract["id"],
            "extraction_run_id": extracted["run_id"],
            "expected_plan_fingerprint": plan["plan_fingerprint"],
            "inputs": contract["expected_inputs"],
            "resource_bindings": {"material_0": cold_id},
        },
        "readiness-cold",
        LIMITS,
    )
    cold = inspect(store, user, made["run_id"])
    request = {
        "expected_version": cold["version"],
        "expected_fence": cold["fence"],
        "request_key": "cold-handoff",
    }
    if answer_cache:
        with pytest.raises(DomainError) as denied:
            prepare_handoff(store, user, made["run_id"], request)
        assert denied.value.code == "UNSUPPORTED_CAPABILITY"
    else:
        handoff = prepare_handoff(store, user, made["run_id"], request)
        assert {r["resource_id"] for r in handoff["dependency_resources"]} == {source_id, cold_id}
        assert [r["resource_id"] for r in handoff["egress"]["resources"]] == [cold_id]
        assert handoff["egress"]["source_result_fingerprint"] is None
        assert handoff["egress"]["source_evidence_allowed"] is False
        assert require_handoff(store, user, made["run_id"]) == handoff
    with store.tx() as c:
        assert c.execute(select(func.count()).select_from(attempts)).scalar_one() == 3
        assert (
            c.execute(select(runs.c.result).where(runs.c.id == made["run_id"])).scalar_one() is None
        )


def test_pending_actual_slot_blocks_handoff_without_clearing_or_resending(env):
    from test_protocol_http import NoProvider

    from sim2act.tools import definitions
    from sim2act.worker import Worker

    rid, request = fresh(env)
    prepare_handoff(env[0], env[3], rid, request)
    worker = Worker(env[0], env[1], NoProvider())
    owned = env[0].claim(worker.id, 30)
    context = copy.deepcopy(owned["context"])
    context["messages"] = [{"role": "user", "content": "offline reserved"}]
    worker.reserve(
        rid,
        owned["fence"],
        context,
        request_tools=[t for t in definitions() if t["function"]["name"] == "resource.read"],
    )
    with pytest.raises(DomainError) as denied:
        require_handoff(env[0], env[3], rid)
    assert denied.value.code == "OUTCOME_UNKNOWN"
    with env[0].tx() as c:
        assert c.execute(select(func.count()).select_from(attempts)).scalar_one() == 1
        assert c.execute(select(func.count()).select_from(protocol_request_slots)).scalar_one() == 1
        assert c.execute(select(attempts.c.status)).scalar_one() == "STARTED"


def test_controller_request_key_cannot_rebind_frozen_handoff(env):
    rid, request = fresh(env)
    prepare_handoff(env[0], env[3], rid, request)
    with pytest.raises(DomainError):
        prepare_handoff(env[0], env[3], rid, {**request, "request_key": "different-key"})


@pytest.mark.parametrize("field", ["expected_version", "expected_fence"])
def test_controller_function_reports_bad_boolean_as_domain_error(env, field):
    rid, request = fresh(env)
    with pytest.raises(DomainError) as denied:
        prepare_handoff(env[0], env[3], rid, {**request, field: True})
    assert denied.value.code == "INVALID_INPUT"
