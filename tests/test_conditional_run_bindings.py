"""Actual HTTP/Intern MockTransport/Worker evidence, independently authored finite cases."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from sqlalchemy import delete, func, select, update

from sim2act.conditional_checks import CONTRACT, SOURCE_HASH
from sim2act.conditional_runs import (
    ANCHOR_EVENT,
    CHECK_EVENT,
    GOAL,
    SOURCE,
    candidate_for,
    contract_snapshot,
    inputs_for,
)
from sim2act.db import (
    attempts,
    events,
    fingerprint,
    grants,
    operations,
    principals,
    protocol_jobs,
    protocol_request_pools,
    protocol_request_slots,
    runs,
)
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider, initialize_ledger
from sim2act.protocol_api import ProtocolAttemptRunner, provider_stage
from sim2act.protocol_pool import initialize_pools
from sim2act.worker import Worker

POLICY = Path("docs/evidence/model-protocol-preparation-20261006/materials/a-source/policy.txt")


@pytest.fixture
def env(env):
    initialize_pools(env[0], offline_limit=14)
    ids = []
    for name in ["bounded public rules", "fresh rules binding"]:
        response = env[2].post(
            f"/api/projects/{env[5]}/resources",
            json={"name": name, "format": "txt", "content": POLICY.read_text()},
        )
        assert response.status_code == 201
        ids.append(response.json()["id"])
    return (*env[:6], *ids)


def facts(amount=680, **changes):
    return {
        "kind": "HYPOTHETICAL_EMPLOYEE",
        "trip_ended": True,
        "amount": amount,
        "receipt_present": True,
        "approved": False,
        "elapsed_days": 2,
        **changes,
    }


def report(states=("TRUE", "TRUE", "FALSE"), decision="BLOCK", actions=None):
    lines = POLICY.read_text().splitlines()
    return {
        "findings": [
            {"rule_id": r, "applies": state, "citation": {"line": line, "quote": lines[line - 1]}}
            for r, state, line in zip(["R1", "R2", "R3"], states, [3, 4, 5], strict=True)
        ],
        "decision": decision,
        "next_actions": actions or ["obtain_prior_approval"],
        "deadline_days": 10,
        "absolute_date": "UNKNOWN",
        "receipt_restarts_deadline": False,
        "explanation": "Hand-authored mock response; explanation is NOT_CHECKED.",
    }


def envelope(value=None, resource=None):
    message = {"role": "assistant", "content": json.dumps(value)}
    if resource:
        message = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "read-current-rules",
                    "type": "function",
                    "function": {
                        "name": "resource.read",
                        "arguments": json.dumps({"resource_id": resource}),
                    },
                }
            ],
        }
    return {
        "model": "intern-s2",
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        "choices": [{"finish_reason": "tool_calls" if resource else "stop", "message": message}],
    }


def base(env):
    return f"/api/projects/{env[5]}/conditional-runs"


def source_body(env, **changes):
    return {
        "resource_id": env[6],
        "expected_source_hash": SOURCE_HASH,
        "expected_contract_fingerprint": fingerprint(CONTRACT),
        "goal": GOAL,
        "scenario": facts(),
        "request_key": "bounded-source",
        **changes,
    }


def get(env, rid):
    response = env[2].get(base(env) + "/" + rid)
    assert response.status_code == 200, response.text
    return response.json()


def factory(env, tmp_path, responses, wires):
    def build(worker, run, snapshot):
        ledger = tmp_path / (run["id"] + ".json")
        initialize_ledger(ledger, snapshot["scope"])
        clock = [1000.0]

        def handler(request):
            wire = json.loads(request.content)
            wires.append(wire)
            assert str(request.url) == "https://chat.intern-ai.org.cn/api/v1/chat/completions"
            assert wire["max_tokens"] == 1024 and wire["stream"] is False
            assert len(request.content) <= 10000
            clock[0] += 7
            return httpx.Response(200, json=responses.pop(0))

        model = InternModel(
            replace(env[1], live_enabled=True, token="synthetic-offline"),
            transport=httpx.MockTransport(handler),
        )

        def authorize(_):
            with env[0].tx() as c:
                env[0].guard(c, run["id"], run["fence"])
                for ref in snapshot["scope"]["resource_ids"]:
                    env[0].authorize(
                        c,
                        run["principal_id"],
                        run["runtime_id"],
                        run["project_id"],
                        ref,
                        "resource.read",
                    )
            return True

        provider = BudgetedProvider(
            model,
            ledger,
            snapshot["scope"],
            provider_stage(snapshot),
            authorize=authorize,
            clock=lambda: clock[0],
        )
        return ProtocolAttemptRunner(worker, run, snapshot, provider)

    return build


def work(env, tmp_path, responses, wires):
    worker = Worker(
        env[0], env[1], protocol_runner_factory=factory(env, tmp_path, responses, wires)
    )
    assert worker.once()
    assert responses == []


def prepared(env, tmp_path, *, scenario=None, output=None, key="bounded-source"):
    queued = env[2].post(
        base(env) + "/source", json=source_body(env, scenario=scenario or facts(), request_key=key)
    )
    assert queued.status_code == 202, queued.text
    rid = queued.json()["run_id"]
    wires = []
    work(env, tmp_path, [envelope(resource=env[6]), envelope(output or report())], wires)
    result = get(env, rid)
    assert result["status"] == "WAITING_APPROVAL", result
    assert (
        result["semantic_status"] == "UNKNOWN"
        and result["overall_run_acceptance"] == "NOT_ACCEPTED"
    )
    check_body = {
        "expected_result_fingerprint": result["result_fingerprint"],
        "expected_version": result["version"],
        "expected_fence": result["fence"],
        "request_key": "finite-check",
    }
    response = env[2].post(base(env) + "/" + rid + "/checks", json=check_body)
    assert response.status_code == 201, response.text
    return rid, result, response.json(), wires, check_body


def extract_body(rid, result, check, **changes):
    return {
        "source_run_id": rid,
        "expected_source_fingerprint": result["result_fingerprint"],
        "expected_check_fingerprint": check["fingerprint"],
        "request_key": "bounded-extract",
        **changes,
    }


def test_actual_source_check_extract_new_scenario_cold_chain_no_authority_or_success_promotion(
    env, tmp_path
):
    with env[0].tx() as c:
        before = fingerprint([dict(x) for x in c.execute(select(grants)).mappings()])
        identities = c.execute(select(func.count()).select_from(principals)).scalar_one()
    rid, source, checked, wires, check_body = prepared(env, tmp_path)
    assert checked["value"]["checks"]["check_status"] == "PASS"
    assert checked["value"]["candidate_eligible"] is True
    assert checked["value"]["checks"]["decision"] == "BLOCK"
    assert get(env, rid)["status"] == "WAITING_APPROVAL"
    assert env[2].post(base(env) + "/" + rid + "/checks", json=check_body).json() == checked
    assert env[2].post(base(env) + "/source", json=source_body(env)).json()["run_id"] == rid
    # Original successful-source gate remains intact and cannot reinterpret finite checks as semantic PASS.
    old = env[2].post(
        f"/api/projects/{env[5]}/protocol/extract",
        json={
            "source_run_id": rid,
            "expected_source_fingerprint": source["result_fingerprint"],
            "request_key": "old-gate",
        },
    )
    assert old.status_code == 400, old.text
    response = env[2].post(base(env) + "/extract", json=extract_body(rid, source, checked))
    assert response.status_code == 202, response.text
    eid = response.json()["run_id"]
    template = candidate_for(contract_snapshot(SOURCE, inputs_for(facts())), env[6])
    work(env, tmp_path, [envelope(template)], wires)
    compiled = get(env, eid)
    assert compiled["status"] == "SUCCEEDED" and compiled["semantic_status"] == "NOT_RUN"
    plan = compiled["result"]["compiled_plan"]
    assert plan["source_check_fingerprint"] == checked["fingerprint"]
    cold_body = {
        "extraction_run_id": eid,
        "expected_plan_fingerprint": plan["plan_fingerprint"],
        "resource_id": env[7],
        "scenario": facts(500),
        "request_key": "new-scenario",
    }
    cold = env[2].post(base(env) + "/cold", json=cold_body)
    assert cold.status_code == 202, cold.text
    cid = cold.json()["run_id"]
    cold_report = report(("TRUE", "FALSE", "FALSE"), "ALLOW", ["submit_claim_and_receipt"])
    work(env, tmp_path, [envelope(cold_report)], wires)
    actual = get(env, cid)
    assert actual["status"] == "WAITING_APPROVAL" and actual["semantic_status"] == "UNKNOWN"
    assert actual["result"]["protocol_result"]["evidence"]["output"] == cold_report
    cold_check = env[2].post(
        base(env) + "/" + cid + "/checks",
        json={
            "expected_result_fingerprint": actual["result_fingerprint"],
            "expected_version": actual["version"],
            "expected_fence": actual["fence"],
            "request_key": "fresh-check",
        },
    )
    assert cold_check.status_code == 201, cold_check.text
    assert cold_check.json()["value"]["candidate_eligible"] is True
    assert cold_check.json()["fingerprint"] != checked["fingerprint"]
    assert len(wires) == 4
    cold_wire = json.dumps(wires[-1], ensure_ascii=False)
    assert (
        env[6] not in cold_wire
        and "obtain_prior_approval"
        not in json.dumps(wires[-1]["messages"][-1].get("content", "")).split("report_schema_json")[
            0
        ]
    )
    assert "actual_checked_report" not in cold_wire
    # The pinned public policy itself contains an original 680 case; cold facts
    # are the separate explicit scenario, never the prior checked Report.
    cold_node = json.loads(wires[-1]["messages"][-1]["content"])
    assert json.loads(cold_node["inputs"]["scenario_json"])["amount"] == 500
    assert not any("expected_output" in json.dumps(w) or "gold_sha" in json.dumps(w) for w in wires)
    with env[0].tx() as c:
        slots = list(c.execute(select(protocol_request_slots)).mappings())
        actual_attempts = list(c.execute(select(attempts)).mappings())
        assert len(slots) == len(actual_attempts) == 4
        assert {x["attempt_id"] for x in slots} == {x["id"] for x in actual_attempts}
        assert len({x["pool_id"] for x in slots}) == 1
        assert {x["phase"] for x in slots} == {"source", "extract", "cold"}
        assert c.execute(select(func.count()).select_from(operations)).scalar_one() == 2
        assert fingerprint([dict(x) for x in c.execute(select(grants)).mappings()]) == before
        assert c.execute(select(func.count()).select_from(principals)).scalar_one() == identities
        assert (
            c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one()
            == "WAITING_APPROVAL"
        )
        pool = (
            c.execute(
                select(protocol_request_pools).where(
                    protocol_request_pools.c.id == slots[0]["pool_id"]
                )
            )
            .mappings()
            .one()
        )
        assert pool["request_limit"] == 14


@pytest.mark.parametrize(
    "scenario,output",
    [
        (
            facts(500, approved=None),
            report(("TRUE", "FALSE", "FALSE"), "ALLOW", ["submit_claim_and_receipt"]),
        ),
        (
            facts(500, elapsed_days=11),
            report(("TRUE", "FALSE", "FALSE"), "UNKNOWN", ["clarify_late_policy"]),
        ),
        (facts(), report(("TRUE", "TRUE", "FALSE"), "ALLOW", ["submit_claim_and_receipt"])),
    ],
)
def test_unknown_facts_uncovered_late_goal_and_wrong_report_cannot_extract(
    env, tmp_path, scenario, output
):
    rid, result, checked, wires, _ = prepared(env, tmp_path, scenario=scenario, output=output)
    assert checked["value"]["candidate_eligible"] is False
    denied = env[2].post(base(env) + "/extract", json=extract_body(rid, result, checked))
    assert denied.status_code == 400, denied.text
    assert len(wires) == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("goal", "uncovered question"),
        ("expected_source_hash", "0" * 64),
        ("expected_contract_fingerprint", "0" * 64),
        ("report", {}),
        ("candidate", {}),
        ("gold", {}),
        ("decision", "PASS"),
    ],
)
def test_closed_opt_in_scope_source_rejects_uncovered_and_caller_verdict(env, field, value):
    response = env[2].post(base(env) + "/source", json=source_body(env, **{field: value}))
    assert response.status_code in {403, 409, 422}
    with env[0].tx() as c:
        assert c.execute(select(func.count()).select_from(attempts)).scalar_one() == 0


@pytest.mark.parametrize(
    "change",
    [
        "wrong_check",
        "wrong_run",
        "old_result",
        "version",
        "fence",
        "principal",
        "project",
        "revoked",
        "check_payload",
        "anchor",
        "attempt_response",
        "operation",
    ],
)
def test_persisted_bound_checks_reject_replay_auth_and_technical_evidence_tamper(
    env, tmp_path, change
):
    rid, result, checked, wires, check_body = prepared(env, tmp_path)
    body = extract_body(rid, result, checked)
    if change == "wrong_check":
        body["expected_check_fingerprint"] = "0" * 64
    elif change == "wrong_run":
        body["source_run_id"] = "run_" + "a" * 32
    elif change == "old_result":
        body["expected_source_fingerprint"] = "0" * 64
    elif change in {"version", "fence"}:
        altered = {**check_body, "expected_" + change: result[change] + 1}
        assert env[2].post(base(env) + "/" + rid + "/checks", json=altered).status_code == 409
        return
    elif change == "principal":
        env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    elif change == "project":
        pid = env[2].post("/api/projects", json={"name": "other own project"}).json()["id"]
        response = env[2].post(f"/api/projects/{pid}/conditional-runs/extract", json=body)
        assert response.status_code == 403
        return
    else:
        with env[0].tx() as c:
            if change == "revoked":
                c.execute(
                    delete(grants).where(
                        grants.c.resource_id == env[6], grants.c.tool_ref == "resource.read"
                    )
                )
            elif change == "check_payload":
                record = copy.deepcopy(checked)
                record["value"]["input_fingerprint"] = "0" * 64
                record["fingerprint"] = fingerprint(record["value"])
                # Coherently alter BOTH event rows; actual Run recomputation must still reject.
                c.execute(
                    update(events)
                    .where(events.c.kind == CHECK_EVENT, events.c.run_id == rid)
                    .values(data=record)
                )
                c.execute(
                    update(events)
                    .where(events.c.kind == ANCHOR_EVENT, events.c.run_id == record["check_id"])
                    .values(data=record)
                )
                body["expected_check_fingerprint"] = record["fingerprint"]
            elif change == "anchor":
                c.execute(
                    delete(events).where(
                        events.c.run_id == checked["check_id"], events.c.kind == ANCHOR_EVENT
                    )
                )
            elif change == "attempt_response":
                row = (
                    c.execute(
                        select(attempts).where(
                            attempts.c.run_id == rid, attempts.c.response.is_not(None)
                        )
                    )
                    .mappings()
                    .all()[-1]
                )
                modified = copy.deepcopy(row["response"])
                modified["choices"][0]["message"]["content"] = json.dumps({"unrelated": True})
                c.execute(
                    update(attempts).where(attempts.c.id == row["id"]).values(response=modified)
                )
            else:
                c.execute(
                    update(operations)
                    .where(operations.c.run_id == rid)
                    .values(tool_ref="artifact.save_text")
                )
    response = env[2].post(base(env) + "/extract", json=body)
    assert response.status_code in {400, 403, 409}, response.text
    assert len(wires) == 2


def test_concurrent_idempotent_checks_and_changed_key_request_reject(env, tmp_path):
    rid, _, checked, _, request = prepared(env, tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(
            pool.map(
                lambda _: env[2].post(base(env) + "/" + rid + "/checks", json=request), range(2)
            )
        )
    assert all(r.status_code == 201 and r.json() == checked for r in replies)
    with env[0].tx() as c:
        assert (
            c.execute(
                select(func.count())
                .select_from(events)
                .where(events.c.kind == CHECK_EVENT, events.c.run_id == rid)
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                select(func.count())
                .select_from(events)
                .where(events.c.kind == ANCHOR_EVENT, events.c.run_id == checked["check_id"])
            ).scalar_one()
            == 1
        )
    altered = {**request, "expected_result_fingerprint": "0" * 64}
    assert env[2].post(base(env) + "/" + rid + "/checks", json=altered).status_code == 409


@pytest.mark.parametrize(
    "field,value",
    [
        ("findings", []),
        ("findings", report()["findings"][:2]),
        ("explanation", ""),
        ("next_actions", []),
        ("deadline_days", True),
        ("unexpected", "data"),
    ],
)
def test_invalid_actual_report_stops_before_completion_check_or_candidate(
    env, tmp_path, field, value
):
    output = {**report(), field: value}
    response = env[2].post(base(env) + "/source", json=source_body(env))
    rid = response.json()["run_id"]
    wires = []
    work(env, tmp_path, [envelope(resource=env[6]), envelope(output)], wires)
    actual = get(env, rid)
    assert actual["status"] == "FAILED" and actual["result"] is None
    assert actual["semantic_status"] == "UNKNOWN"
    rejected = env[2].post(
        base(env) + "/" + rid + "/checks",
        json={
            "expected_result_fingerprint": "0" * 64,
            "expected_version": actual["version"],
            "expected_fence": actual["fence"],
            "request_key": "no-bad-report",
        },
    )
    assert rejected.status_code in {400, 409}
    with env[0].tx() as c:
        assert (
            c.execute(
                select(func.count()).select_from(events).where(events.c.kind == CHECK_EVENT)
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize("mutation", ["instruction", "answer", "extra_step"])
def test_model_candidate_without_exact_covered_template_stops_and_no_cold(env, tmp_path, mutation):
    rid, result, checked, wires, _ = prepared(env, tmp_path)
    queued = env[2].post(base(env) + "/extract", json=extract_body(rid, result, checked))
    eid = queued.json()["run_id"]
    candidate = candidate_for(contract_snapshot(SOURCE, inputs_for(facts())), env[6])
    if mutation == "instruction":
        candidate["steps"][1]["instruction"] = "Always return the prior BLOCK decision"
    elif mutation == "answer":
        candidate["steps"][1]["instruction"] += json.dumps(report())
    else:
        extra = copy.deepcopy(candidate["steps"][1])
        extra["id"] = "uncovered_language"
        candidate["steps"].append(extra)
    work(env, tmp_path, [envelope(candidate)], wires)
    failed = get(env, eid)
    assert failed["status"] == "FAILED" and failed["result"] is None
    assert get(env, rid)["status"] == "WAITING_APPROVAL"
    with env[0].tx() as c:
        assert c.execute(select(func.count()).select_from(attempts)).scalar_one() == 3


def test_actual_other_run_check_cannot_replace_current_report_binding(env, tmp_path):
    first, first_result, first_check, _, _ = prepared(env, tmp_path, key="first")
    second, second_result, second_check, _, _ = prepared(env, tmp_path, key="second")
    response = env[2].post(
        base(env) + "/extract", json=extract_body(second, second_result, first_check)
    )
    assert response.status_code == 400
    # Replay both sealed copies onto the other Run; source evidence remains bound to the original Run.
    with env[0].tx() as c:
        env[0].event(c, second, CHECK_EVENT, first_check)
    response = env[2].post(
        base(env) + "/extract", json=extract_body(second, second_result, first_check)
    )
    assert response.status_code == 409
    assert (
        first != second
        and first_result["result_fingerprint"] != second_result["result_fingerprint"]
    )
    assert first_check["fingerprint"] != second_check["fingerprint"]


def test_revoke_after_extract_enqueue_stops_before_new_model_request(env, tmp_path):
    rid, result, checked, wires, _ = prepared(env, tmp_path)
    queued = env[2].post(base(env) + "/extract", json=extract_body(rid, result, checked))
    eid = queued.json()["run_id"]
    with env[0].tx() as c:
        c.execute(
            delete(grants).where(
                grants.c.resource_id == env[6], grants.c.tool_ref == "resource.read"
            )
        )
    worker = Worker(env[0], env[1], protocol_runner_factory=factory(env, tmp_path, [], wires))
    assert worker.once()
    assert len(wires) == 2
    with env[0].tx() as c:
        assert c.execute(select(runs.c.status).where(runs.c.id == eid)).scalar_one() in {
            "FAILED",
            "WAITING_RESOURCE",
        }
        assert c.execute(select(func.count()).select_from(attempts)).scalar_one() == 2


def test_legacy_catalog_and_namespace_reject_bounded_contract_and_caller_report(env):
    assert len(env[2].get(f"/api/projects/{env[5]}/protocol/contracts").json()["items"]) == 4
    response = env[2].post(
        f"/api/projects/{env[5]}/protocol/source",
        json={
            "goal": GOAL,
            "inputs": inputs_for(facts()),
            "resource_ids": [env[6]],
            "contract_id": SOURCE,
            "request_key": "not-opt-in",
        },
    )
    assert response.status_code == 400
    queued = env[2].post(base(env) + "/source", json=source_body(env))
    rid = queued.json()["run_id"]
    response = env[2].post(
        base(env) + "/" + rid + "/checks",
        json={
            "expected_result_fingerprint": "0" * 64,
            "expected_version": 1,
            "expected_fence": 1,
            "request_key": "forged",
            "report": report(),
        },
    )
    assert response.status_code == 422
    assert env[2].get(base(env) + "/" + rid).json()["status"] == "QUEUED"


def test_application_role_actual_bound_chain_uses_existing_crud_only(env, runtime_role, tmp_path):
    from fastapi.testclient import TestClient

    from sim2act.api import create_app
    from sim2act.db import Store

    store = Store(runtime_role, test_only=True)  # Deliberately no initialize or migration.
    settings = replace(env[1], database_url=runtime_role)
    client = TestClient(create_app(store, settings))
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    role_env = (store, settings, client, *env[3:])
    try:
        test_actual_source_check_extract_new_scenario_cold_chain_no_authority_or_success_promotion(
            role_env, tmp_path
        )
    finally:
        client.close()
        store.engine.dispose()


@pytest.mark.parametrize(
    "mutation",
    [
        "FAILED",
        "PARTIAL",
        "RECONCILING",
        "unknown_attempt",
        "resource_hash",
        "actual_report",
        "tool_trace",
        "completion_bool",
    ],
)
def test_source_known_receipt_and_current_material_cannot_be_replaced(env, tmp_path, mutation):
    from sim2act.db import resources

    rid, result, checked, wires, _ = prepared(env, tmp_path)
    with env[0].tx() as c:
        if mutation in {"FAILED", "PARTIAL", "RECONCILING"}:
            c.execute(update(runs).where(runs.c.id == rid).values(status=mutation))
        elif mutation == "unknown_attempt":
            c.execute(update(attempts).where(attempts.c.run_id == rid).values(status="STARTED"))
        elif mutation == "resource_hash":
            c.execute(update(resources).where(resources.c.id == env[6]).values(hash="0" * 64))
        elif mutation == "completion_bool":
            row = (
                c.execute(
                    select(events).where(
                        events.c.run_id == rid, events.c.kind == "PROTOCOL_COMPLETED"
                    )
                )
                .mappings()
                .one()
            )
            seal = {**row["data"], "completed_fence": True}
            c.execute(update(events).where(events.c.id == row["id"]).values(data=seal))
        else:
            row = (
                c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == rid))
                .mappings()
                .one()
            )
            modified = copy.deepcopy(row["result_snapshot"])
            evidence = modified["protocol_result"]["evidence"]
            if mutation == "actual_report":
                evidence["output"] = report(
                    ("TRUE", "FALSE", "FALSE"), "ALLOW", ["submit_claim_and_receipt"]
                )
            else:
                evidence["tool_trace"] = []
            # Coherent job+Run snapshot hash still lacks independent original completion anchor.
            fp = fingerprint(modified)
            c.execute(
                update(protocol_jobs)
                .where(protocol_jobs.c.run_id == rid)
                .values(result_snapshot=modified, result_fingerprint=fp)
            )
            c.execute(update(runs).where(runs.c.id == rid).values(result=modified))
    response = env[2].post(base(env) + "/extract", json=extract_body(rid, result, checked))
    assert response.status_code in {400, 403, 409}, response.text
    assert len(wires) == 2
