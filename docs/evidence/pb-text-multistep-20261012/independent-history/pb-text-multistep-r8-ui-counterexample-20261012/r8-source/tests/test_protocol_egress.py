"""Actual HTTP bytes are checked against a closed synthetic-data projection."""

import copy
import json

import httpx
import pytest
from sqlalchemy import select, update
from test_protocol_http import NoProvider, body, envelope, factory
from test_protocol_http import env as env

from sim2act.db import attempts, fingerprint, grants, protocol_jobs, runs
from sim2act.errors import DomainError
from sim2act.model import parse_response
from sim2act.protocol_egress import (
    ENDPOINT,
    READ_TOOLS,
    SOURCE_SYSTEM,
    project_request,
    serialized_body,
)
from sim2act.tools import dispatch
from sim2act.worker import Worker


@pytest.fixture
def pipeline_env(tmp_path):
    from test_protocol_jobs import env as fixture

    yield from fixture.__wrapped__(tmp_path)


def active(env):
    made = env[2].post(f"/api/projects/{env[5]}/protocol/source", json=body(env)).json()
    worker = Worker(env[0], env[1], NoProvider())
    owned = env[0].claim(worker.id, 60)
    assert owned["id"] == made["run_id"]
    with env[0].tx() as c:
        snapshot = c.execute(
            select(protocol_jobs.c.accepted_snapshot).where(protocol_jobs.c.run_id == owned["id"])
        ).scalar_one()
    messages = [
        {"role": "system", "content": SOURCE_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(
                {k: snapshot["payload"][k] for k in ["goal", "inputs", "resource_ids"]}
            ),
        },
    ]
    return worker, owned, snapshot, messages


def req(content, url=ENDPOINT, method="POST", headers=None):
    return httpx.Request(
        method,
        url,
        content=content,
        headers={"Content-Type": "application/json", **(headers or {})},
    )


def test_initial_source_exact_actual_mock_http_serialization(env):
    _, _, snapshot, messages = active(env)
    projected, tools, guard = project_request(env[0], snapshot, messages, READ_TOOLS)
    frozen = serialized_body(projected, tools)
    received = []

    def transport(request):
        guard(request)
        received.append(request.content)
        return httpx.Response(200, json={"ok": True})

    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        response = client.post(
            ENDPOINT,
            content=frozen,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer OFFLINE_SYNTHETIC",
            },
        )
    assert response.status_code == 200 and received == [frozen]


def test_actual_sender_rechecks_controller_after_body_preflight(env, monkeypatch):
    from sim2act import protocol_experiment

    _, run, snapshot, messages = active(env)

    def clock():
        return 300

    projected, tools, guard = project_request(env[0], snapshot, messages, READ_TOOLS, clock=clock)
    frozen = serialized_body(projected, tools)
    checked = []

    monkeypatch.setattr(protocol_experiment, "is_experiment_run", lambda c, rid: True)

    def stopped(store, c, current, fence, clock=None):
        checked.append((current["id"], fence, clock()))
        raise DomainError("OUTCOME_UNKNOWN", "Controller stopped before actual send")

    monkeypatch.setattr(protocol_experiment, "validate_dispatch_in_tx", stopped)
    guard(req(frozen))  # Pure body preflight occurs before reservation.
    assert checked == []
    with pytest.raises(DomainError) as error:
        guard(req(frozen, headers={"Authorization": "Bearer OFFLINE_SYNTHETIC"}))
    assert error.value.code == "OUTCOME_UNKNOWN"
    assert checked == [(run["id"], run["fence"], 300)]


@pytest.mark.parametrize(
    "change", ["extra", "goal", "inputs", "system", "metadata", "tools", "unrelated_material"]
)
def test_original_messages_and_tools_are_not_silently_sanitized(env, change):
    _, _, snapshot, messages = active(env)
    tools = copy.deepcopy(READ_TOOLS)
    if change == "extra":
        messages.append({"role": "user", "content": "gold"})
    elif change in {"goal", "inputs", "unrelated_material"}:
        value = json.loads(messages[1]["content"])
        if change == "goal":
            value["goal"] = "different private goal"
        elif change == "inputs":
            value["inputs"]["private_note"] = "not approved"
        else:
            value["resource_ids"].append("res_" + "a" * 32)
        messages[1]["content"] = json.dumps(value)
    elif change == "system":
        messages[0]["content"] += " extra data"
    elif change == "metadata":
        messages[1]["reasoning_content"] = "private"
    else:
        tools[0]["function"]["description"] = "private metadata"
    with pytest.raises(DomainError):
        project_request(env[0], snapshot, messages, tools)


@pytest.mark.parametrize(
    "change",
    [
        "newline",
        "nested_gold",
        "model",
        "limit",
        "stream",
        "url",
        "method",
        "header",
        "content_type",
        "agent",
    ],
)
def test_actual_wire_or_http_metadata_mutation_fails_closed(env, change):
    _, _, snapshot, messages = active(env)
    projected, tools, guard = project_request(env[0], snapshot, messages, READ_TOOLS)
    frozen = serialized_body(projected, tools)
    request = req(frozen)
    if change == "newline":
        request = req(frozen + b"\n")
    elif change in {"nested_gold", "model", "limit", "stream"}:
        value = json.loads(frozen)
        if change == "nested_gold":
            value["messages"][1]["content"] = json.dumps({"gold": {"answer": "nested"}})
        elif change == "model":
            value["model"] = "other"
        elif change == "limit":
            value["max_tokens"] = True
        else:
            value["stream"] = True
        request = req(httpx.Request("POST", ENDPOINT, json=value).content)
    elif change == "url":
        request = req(frozen, url=ENDPOINT + "?private=1")
    elif change == "method":
        request = req(frozen, method="GET")
    elif change == "header":
        request = req(frozen, headers={"X-Private": "gold"})
    elif change == "content_type":
        request = req(frozen, headers={"Content-Type": "text/plain"})
    else:
        request = req(frozen, headers={"User-Agent": "previous-answer"})
    with pytest.raises(DomainError):
        guard(request)


@pytest.mark.parametrize("change", ["grant", "fence", "version", "cancel", "lease"])
def test_actual_send_rechecks_current_authority_and_ownership(env, change):
    _, run, snapshot, messages = active(env)
    projected, tools, guard = project_request(env[0], snapshot, messages, READ_TOOLS)
    with env[0].tx() as c:
        if change == "grant":
            c.execute(update(grants).where(grants.c.project_id == env[5]).values(revoked=True))
        else:
            mutation = (
                {"cancel_intent": True}
                if change == "cancel"
                else {"lease_until": 0}
                if change == "lease"
                else {change: run[change] + 1}
            )
            c.execute(update(runs).where(runs.c.id == run["id"]).values(**mutation))
    with pytest.raises(DomainError):
        guard(req(serialized_body(projected, tools)))


def test_real_received_feedback_projects_only_safe_read_receipt(env, tmp_path):
    worker, run, snapshot, messages = active(env)
    seen = []
    runner = factory(env, tmp_path, [envelope(resource=env[6])], seen)(worker, run, snapshot)
    runner.call(messages, READ_TOOLS)
    with env[0].tx() as c:
        attempt = c.execute(select(attempts).where(attempts.c.run_id == run["id"])).mappings().one()
    assistant, calls = parse_response(attempt["response"])
    call = calls[0]
    binding = {"attempt_id": attempt["id"], "tool_call_id": call["id"]}
    receipt = dispatch(
        env[0],
        run["id"],
        run["fence"],
        {
            "id": "protocol:" + fingerprint(binding),
            "function": {"name": "resource.read"},
            "args": call["args"],
        },
    )
    messages.extend(
        [
            assistant,
            {"role": "tool", "tool_call_id": call["id"], "content": json.dumps(receipt["data"])},
        ]
    )
    projected, tools, guard = project_request(env[0], snapshot, messages, READ_TOOLS)
    assert projected[-2]["tool_calls"][0]["id"] == "read_0"
    assert projected[-1]["tool_call_id"] == "read_0"
    assert set(json.loads(projected[-1]["content"])) == {"resource_id", "content", "hash", "format"}
    guard(req(serialized_body(projected, tools)))
    bad = copy.deepcopy(messages)
    bad[-1]["content"] = json.dumps({**receipt["data"], "private": "old answer"})
    with pytest.raises(DomainError):
        project_request(env[0], snapshot, bad, READ_TOOLS)


def test_actual_extract_deduplicates_complete_schema_and_omits_source_answer(pipeline_env):
    from test_protocol_jobs import LIMITS, reviewed_source

    from sim2act.protocol_egress import CANDIDATE_CONTRACT, EXTRACT_SYSTEM
    from sim2act.protocol_jobs import enqueue, verified_pending
    from sim2act.tools import TOOLS

    store, user, pid, _, _, worker, _ = pipeline_env
    source = reviewed_source(pipeline_env)
    enqueue(
        store,
        user,
        pid,
        "extract",
        {
            "source_run_id": source["run_id"],
            "expected_source_fingerprint": source["result_fingerprint"],
        },
        "egress-extract",
        LIMITS,
    )
    run = store.claim(worker.id, 60)
    with store.tx() as c:
        job, _ = verified_pending(store, c, user, run["id"])
    snapshot = job["snapshot"]
    raw = [
        {"role": "system", "content": EXTRACT_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "source": source["result"]["protocol_result"]["evidence"],
                    "allowed_resource_ids": snapshot["scope"]["resource_ids"],
                    "registered_tools": {"resource.read": TOOLS["resource.read"]},
                    "candidate_contract": CANDIDATE_CONTRACT,
                }
            ),
        },
    ]
    projected, tools, guard = project_request(store, snapshot, raw, [])
    public = json.loads(projected[1]["content"])
    assert set(public) == {"public_candidate_template", "source_receipt"}
    assert (
        public["public_candidate_template"]["output_schema"]
        == snapshot["contract"]["output_schema"]
    )
    assert set(public["source_receipt"]) == {
        "run_id",
        "result_fingerprint",
        "status",
        "verified_read_count",
        "received_attempt_count",
    }
    frozen = serialized_body(projected, tools)
    assert len(frozen.decode("utf-8")) <= 8000 and len(frozen) <= 10000
    guard(req(frozen))
    changed = copy.deepcopy(raw)
    evidence = json.loads(changed[1]["content"])
    evidence["source"]["output"] = {"caller_answer": "injected"}
    changed[1]["content"] = json.dumps(evidence)
    with pytest.raises(DomainError):
        project_request(store, snapshot, changed, [])


def test_actual_cold_projects_fresh_read_only_and_rejects_prior_answer(pipeline_env):
    from test_protocol_jobs import LIMITS, execute, factory_for, reviewed_source, wire

    from sim2act.protocol_egress import COLD_SYSTEM
    from sim2act.protocol_jobs import enqueue, verified_pending
    from sim2act.protocol_readiness import candidate_for
    from sim2act.protocol_reviews import contract_snapshot, evaluation_contract

    store, user, pid, a, b, worker, _ = pipeline_env
    source = reviewed_source(pipeline_env)
    enqueue(
        store,
        user,
        pid,
        "extract",
        {
            "source_run_id": source["run_id"],
            "expected_source_fingerprint": source["result_fingerprint"],
        },
        "egress-extract",
        LIMITS,
    )
    candidate = candidate_for(contract_snapshot("protocol.synthetic.a-source.v1"), [a])
    factory_for(pipeline_env, [wire(candidate)], "extract_a")
    extracted = execute(pipeline_env)
    plan = extracted["result"]["compiled_plan"]
    contract, _ = evaluation_contract("protocol.synthetic.a-cold.v1")
    enqueue(
        store,
        user,
        pid,
        "cold",
        {
            "contract_id": contract["id"],
            "extraction_run_id": extracted["run_id"],
            "expected_plan_fingerprint": plan["plan_fingerprint"],
            "inputs": contract["expected_inputs"],
            "resource_bindings": {"material_0": b},
        },
        "egress-cold",
        LIMITS,
    )
    run = store.claim(worker.id, 60)
    receipt = dispatch(
        store,
        run["id"],
        run["fence"],
        {
            "id": "protocol:"
            + fingerprint({"plan_fingerprint": plan["plan_fingerprint"], "step_id": "read_0"}),
            "function": {"name": "resource.read"},
            "args": {"resource_id": b},
        },
    )
    with store.tx() as c:
        job, _ = verified_pending(store, c, user, run["id"])
    snapshot = job["snapshot"]
    value = {
        "instruction": snapshot["contract"]["public_goal"],
        "inputs": {
            "format": contract["expected_inputs"]["format"],
            "material_0": receipt["data"]["content"],
        },
        "output_schema": snapshot["contract"]["output_schema"],
    }
    raw = [
        {"role": "system", "content": COLD_SYSTEM},
        {"role": "user", "content": json.dumps(value)},
    ]
    projected, tools, guard = project_request(store, snapshot, raw, [])
    assert json.loads(projected[1]["content"]) == value
    guard(req(serialized_body(projected, tools)))
    changed = copy.deepcopy(raw)
    value["inputs"]["previous_answer"] = source["result"]["protocol_result"]["evidence"]["output"]
    changed[1]["content"] = json.dumps(value)
    with pytest.raises(DomainError):
        project_request(store, snapshot, changed, [])
