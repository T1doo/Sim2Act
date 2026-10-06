"""Authenticated durable protocol HTTP; actual Intern adapter, zero network."""

import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from sim2act.api import create_app
from sim2act.db import attempts, fingerprint, grants, operations, principals, protocol_jobs
from sim2act.errors import DomainError
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider, initialize_ledger
from sim2act.model_protocol import obj
from sim2act.protocol_api import ProtocolAttemptRunner
from sim2act.protocol_reviews import contract_snapshot, evaluation_contract
from sim2act.worker import Worker


@pytest.fixture
def env(env):
    from sim2act.protocol_pool import initialize_pools

    initialize_pools(env[0], offline_limit=14)
    material = (
        Path(__file__).parents[1]
        / "docs/evidence/model-protocol-preparation-20261006/materials/a-source/policy.txt"
    )
    response = env[2].post(
        f"/api/projects/{env[5]}/resources",
        json={"name": "synthetic-policy.txt", "format": "txt", "content": material.read_text()},
    )
    assert response.status_code == 201, response.text
    return (*env[:6], response.json()["id"])


def body(env, **changes):
    return {
        "goal": evaluation_contract("protocol.synthetic.a-source.v1")[0]["public_goal"],
        "inputs": evaluation_contract("protocol.synthetic.a-source.v1")[0]["expected_inputs"],
        "resource_ids": [env[6]],
        "contract_id": "protocol.synthetic.a-source.v1",
        "request_key": "protocol-source",
        **changes,
    }


def url(env):
    return f"/api/projects/{env[5]}/protocol"


def state(env, rid):
    result = env[2].get(url(env) + "/runs/" + rid)
    assert result.status_code == 200, result.text
    return result.json()


class NoProvider:
    def request(self, *_):
        pytest.fail("Legacy/default model must never receive protocol request")


def test_http_durable_async_default_provider_unavailable_and_idempotent(env):
    response = env[2].post(url(env) + "/source", json=body(env))
    assert response.status_code == 202, response.text
    made = response.json()
    rid = made["run_id"]
    repeat = env[2].post(url(env) + "/source", json=body(env))
    assert repeat.status_code == 202 and repeat.json()["run_id"] == rid
    changed = env[2].post(url(env) + "/source", json=body(env, goal="other"))
    assert changed.status_code in {403, 409}
    assert Worker(env[0], env[1], NoProvider()).once()
    actual = state(env, rid)
    assert actual["status"] == "WAITING_RESOURCE"
    assert actual["formal_publication_enabled"] is False
    with env[0].tx() as c:
        assert c.execute(select(func.count()).select_from(attempts)).scalar_one() == 0
        assert c.execute(select(func.count()).select_from(protocol_jobs)).scalar_one() == 1


@pytest.mark.parametrize(
    "field",
    [
        "candidate",
        "gold",
        "responses",
        "Replay",
        "PASS",
        "scope",
        "runtime_id",
        "permissions",
        "limits",
    ],
)
def test_http_closed_source_rejects_client_execution_and_verdict(env, field):
    response = env[2].post(url(env) + "/source", json=body(env, **{field: {}}))
    assert response.status_code == 422


@pytest.mark.parametrize(
    "phase, payload",
    [
        ("extract", {"source_run_id": "run_" + "a" * 32, "expected_source_fingerprint": "b" * 64}),
        (
            "cold",
            {
                "extraction_run_id": "run_" + "a" * 32,
                "expected_plan_fingerprint": "b" * 64,
                "inputs": {},
                "resource_bindings": {"material": "res_" + "a" * 32},
                "contract_id": "protocol.synthetic.a-cold.v1",
            },
        ),
    ],
)
def test_http_closed_extract_cold_and_no_forged_source(env, phase, payload):
    payload["request_key"] = phase
    forged = env[2].post(url(env) + "/" + phase, json=payload)
    assert forged.status_code in {400, 403}
    payload["candidate"] = {}
    assert env[2].post(url(env) + "/" + phase, json=payload).status_code == 422


def test_http_owner_project_and_live_boundaries(env):
    made = env[2].post(url(env) + "/source", json=body(env))
    assert made.status_code == 202, made.text
    rid = made.json()["run_id"]
    other_project = env[2].post("/api/projects", json={"name": "other"}).json()["id"]
    assert env[2].get(f"/api/projects/{other_project}/protocol/runs/{rid}").status_code == 403
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    assert env[2].get(url(env) + "/runs/" + rid).status_code == 403
    assert env[2].post(url(env) + "/source", json=body(env)).status_code == 403
    with TestClient(create_app(env[0], replace(env[1], mode="live"))) as live:
        live.headers["Authorization"] = "Bearer synthetic-test-A"
        assert live.post(url(env) + "/source", json=body(env)).status_code == 403
    with pytest.raises(DomainError, match="test-only"):
        Worker(env[0], replace(env[1], mode="live"), protocol_runner_factory=lambda *_: None)


def envelope(value=None, *, resource=None, model="intern-s2", usage=None):
    message = {
        "role": "assistant",
        "content": json.dumps(value),
        "reasoning_content": "PRIVATE never persist",
        "unknown_field": "omit",
    }
    if resource:
        message["content"] = ""
        message["tool_calls"] = [
            {
                "id": "actual-read",
                "type": "function",
                "function": {
                    "name": "resource.read",
                    "arguments": json.dumps({"resource_id": resource}),
                },
            }
        ]
    return {
        "model": model,
        "usage": usage or {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        "choices": [{"finish_reason": "tool_calls" if resource else "stop", "message": message}],
    }


def factory(env, tmp_path, replies, seen, stage="source_a"):
    def build(worker, run, snapshot):
        scope = snapshot["scope"]
        ledger = tmp_path / (run["id"] + ".json")
        initialize_ledger(ledger, scope)
        clock = [1000.0]  # Explicit synthetic time, no sleeps or production rate bypass.

        def handler(request):
            assert str(request.url) == "https://chat.intern-ai.org.cn/api/v1/chat/completions"
            wire = json.loads(request.content)
            seen.append(wire)
            clock[0] += 7
            assert wire["stream"] is False and wire["max_tokens"] == 1024
            return httpx.Response(200, json=replies.pop(0))

        model = InternModel(
            replace(env[1], live_enabled=True, token="synthetic-offline"),
            transport=httpx.MockTransport(handler),
        )

        def authorize(_):
            with env[0].tx() as c:
                env[0].guard(c, run["id"], run["fence"])
                for ref in scope["resource_ids"]:
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
            model, ledger, scope, stage, authorize=authorize, clock=lambda: clock[0]
        )
        return ProtocolAttemptRunner(worker, run, snapshot, provider)

    return build


def test_actual_http_worker_attempt_tools_safe_raw_and_pending_semantics(env, tmp_path):
    seen = []
    with env[0].tx() as c:
        grants_before = [dict(x) for x in c.execute(select(grants)).mappings()]
        principals_before = c.execute(select(func.count()).select_from(principals)).scalar_one()
    queued = env[2].post(url(env) + "/source", json=body(env))
    assert queued.status_code == 202, queued.text
    rid = queued.json()["run_id"]
    worker = Worker(
        env[0],
        env[1],
        NoProvider(),
        protocol_runner_factory=factory(
            env, tmp_path, [envelope(resource=env[6]), envelope({"summary": "fixture"})], seen
        ),
    )
    assert worker.once()
    actual = state(env, rid)
    assert actual["status"] == "WAITING_APPROVAL", actual
    technical = actual["result"]["protocol_result"]
    assert technical["semantic_status"] == "UNKNOWN"
    assert len(seen) == 2 and seen[0]["tools"][0]["function"]["name"] == "resource.read"
    assert "gold" not in json.dumps(seen)
    with env[0].tx() as c:
        recorded = (
            c.execute(
                select(attempts).where(attempts.c.run_id == rid).order_by(attempts.c.created_at)
            )
            .mappings()
            .all()
        )
        assert len(recorded) == 2 and all(x["status"] == "RECEIVED" for x in recorded)
        assert all(x["usage"]["status"] == "known" for x in recorded)
        assert all(x["parameters"]["model_identity"]["enforced"] for x in recorded)
        assert all("PRIVATE" not in json.dumps(x["response"]) for x in recorded)
        assert all("unknown_field" not in json.dumps(x["response"]) for x in recorded)
        assert all(
            x["parameters"]["safe_response_fingerprint"] == fingerprint(x["response"])
            for x in recorded
        )
        assert (
            recorded[0]["response"]["choices"][0]["message"]["tool_calls"][0]["id"] == "actual-read"
        )
        assert recorded[0]["parameters"]["request_fingerprint"] == fingerprint(
            {"messages": seen[0]["messages"], "tools": seen[0]["tools"], "model": "intern-s2"}
        )
        assert len(c.execute(select(operations).where(operations.c.run_id == rid)).all()) == 1
        assert [dict(x) for x in c.execute(select(grants)).mappings()] == grants_before
        assert (
            c.execute(select(func.count()).select_from(principals)).scalar_one()
            == principals_before
        )


@pytest.mark.parametrize(
    "reply",
    [
        envelope({"summary": "bad"}, model="other-model"),
        envelope({"summary": "bad"}, usage={"total_tokens": 20}),
    ],
)
def test_real_intern_refusal_consumes_attempt_without_repair(env, tmp_path, reply):
    seen = []
    queued = env[2].post(url(env) + "/source", json=body(env))
    assert queued.status_code == 202, queued.text
    rid = queued.json()["run_id"]
    worker = Worker(
        env[0], env[1], NoProvider(), protocol_runner_factory=factory(env, tmp_path, [reply], seen)
    )
    assert worker.once()
    assert state(env, rid)["status"] in {"FAILED", "WAITING_RESOURCE"}
    assert not worker.once()
    assert len(seen) == 1
    with env[0].tx() as c:
        rows = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
        assert len(rows) == 1 and rows[0]["status"] == "FAILED"
        assert rows[0]["response_model"] == reply["model"]
        assert rows[0]["parameters"]["model_identity"]["enforced"] is True
        assert rows[0]["parameters"]["raw_response_fingerprint"] == fingerprint(reply)
        assert "PRIVATE" not in json.dumps(rows[0]["response"])
        assert not c.execute(select(operations).where(operations.c.run_id == rid)).first()


def test_started_crash_is_not_automatically_resent(env, tmp_path):
    queued = env[2].post(url(env) + "/source", json=body(env))
    assert queued.status_code == 202, queued.text
    rid = queued.json()["run_id"]
    seen = []

    def crash_factory(worker, run, snapshot):
        runner = factory(env, tmp_path, [], seen)(worker, run, snapshot)

        def crash(_messages, _tools):
            raise KeyboardInterrupt("simulated crash after durable reservation")

        runner.provider.call = crash
        return runner

    worker = Worker(env[0], env[1], NoProvider(), protocol_runner_factory=crash_factory)
    with pytest.raises(KeyboardInterrupt):
        worker.once()
    from sqlalchemy import update

    from sim2act.db import runs

    with env[0].tx() as c:
        row = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one()
        assert row["status"] == "STARTED"
        c.execute(update(runs).where(runs.c.id == rid).values(lease_until=0))
    recovery = Worker(env[0], env[1], NoProvider())
    recovery.once()
    assert state(env, rid)["status"] == "WAITING_RESOURCE"
    with env[0].tx() as c:
        assert (
            c.execute(
                select(func.count()).select_from(attempts).where(attempts.c.run_id == rid)
            ).scalar_one()
            == 1
        )
    assert seen == []


@pytest.mark.parametrize(
    "field", ["responses", "Replay", "candidate", "gold", "PASS", "runtime_id"]
)
def test_nested_execution_evidence_is_not_protocol_input(env, field):
    response = env[2].post(url(env) + "/source", json=body(env, inputs={"nested": {field: {}}}))
    assert response.status_code == 400


@pytest.mark.parametrize("tamper_attempt", [False, True])
def test_complete_authenticated_http_source_review_extract_cold_and_independent_review(
    env, tmp_path, tamper_attempt
):
    source_contract, _ = evaluation_contract("protocol.synthetic.a-source.v1")
    cold_contract, _ = evaluation_contract("protocol.synthetic.a-cold.v1")
    source_response = env[2].post(url(env) + "/source", json=body(env))
    assert source_response.status_code == 202, source_response.text
    source_id = source_response.json()["run_id"]
    assert source_response.json()["semantic_review"] == "WAITING_APPROVAL"
    seen = []
    assert Worker(
        env[0],
        env[1],
        NoProvider(),
        protocol_runner_factory=factory(
            env,
            tmp_path,
            [envelope(resource=env[6]), envelope(source_contract["expected_output"])],
            seen,
        ),
    ).once()
    source = state(env, source_id)
    assert source["status"] == "WAITING_APPROVAL"

    def accept(rid, completed, contract):
        result = env[2].post(
            f"/api/internal/protocol/runs/{rid}/reviews",
            json={
                "contract_id": contract["id"],
                "expected_result_fingerprint": completed["result_fingerprint"],
                "expected_fence": completed["fence"],
                "expected_version": completed["version"],
                "request_key": "independent-" + rid,
            },
        )
        assert result.status_code == 201, result.text
        assert result.json()["decision"] == "PASS"
        return state(env, rid)

    accepted = accept(source_id, source, source_contract)
    assert accepted["status"] == "SUCCEEDED"
    output_schema = contract_snapshot(source_contract["id"])["output_schema"]
    candidate = {
        "schema_version": "model-protocol.v1",
        "input_schema": obj({"format": {"type": "string"}}),
        "resources": {"material": env[6]},
        "steps": [
            {
                "id": "read",
                "kind": "registered_tool",
                "depends_on": [],
                "inputs": {
                    "resource_id": {"source": "data", "ref": "material", "field": "resource_id"}
                },
                "tool_ref": "resource.read",
            },
            {
                "id": "interpret",
                "kind": "language",
                "depends_on": ["read"],
                "inputs": {
                    "content": {"source": "step", "ref": "read", "field": "content"},
                    "format": {"source": "input", "ref": "input", "field": "format"},
                },
                "instruction": source_contract["public_goal"],
                "output_schema": output_schema,
            },
        ],
        "output_schema": output_schema,
        "outputs": {
            key: {"source": "step", "ref": "interpret", "field": key}
            for key in output_schema["properties"]
        },
    }
    extracted = env[2].post(
        url(env) + "/extract",
        json={
            "source_run_id": source_id,
            "expected_source_fingerprint": accepted["result_fingerprint"],
            "request_key": "extract-authenticated",
        },
    )
    assert extracted.status_code == 202, extracted.text
    extraction_id = extracted.json()["run_id"]
    assert Worker(
        env[0],
        env[1],
        NoProvider(),
        protocol_runner_factory=factory(env, tmp_path, [envelope(candidate)], [], "extract_a"),
    ).once()
    compiled = state(env, extraction_id)
    assert compiled["status"] == "SUCCEEDED", compiled
    plan = compiled["result"]["compiled_plan"]
    material = (
        Path(__file__).parents[1]
        / "docs/evidence/model-protocol-preparation-20261006/materials/a-cold/policy.txt"
    )
    cold_resource = (
        env[2]
        .post(
            f"/api/projects/{env[5]}/resources",
            json={"name": "unseen-cold.txt", "format": "txt", "content": material.read_text()},
        )
        .json()["id"]
    )
    cold = env[2].post(
        url(env) + "/cold",
        json={
            "extraction_run_id": extraction_id,
            "expected_plan_fingerprint": plan["plan_fingerprint"],
            "inputs": cold_contract["expected_inputs"],
            "resource_bindings": {"material": cold_resource},
            "contract_id": cold_contract["id"],
            "request_key": "cold-authenticated",
        },
    )
    assert cold.status_code == 202, cold.text
    cold_id = cold.json()["run_id"]
    if tamper_attempt:
        from sqlalchemy import update

        with env[0].tx() as c:
            response = c.execute(
                select(attempts.c.response).where(attempts.c.run_id == extraction_id)
            ).scalar_one()
            response["choices"][0]["message"]["content"] = "{}"
            c.execute(
                update(attempts).where(attempts.c.run_id == extraction_id).values(response=response)
            )
    cold_seen = []
    assert Worker(
        env[0],
        env[1],
        NoProvider(),
        protocol_runner_factory=factory(
            env, tmp_path, [envelope(cold_contract["expected_output"])], cold_seen, "cold_a"
        ),
    ).once()
    if tamper_attempt:
        refused = env[2].get(url(env) + "/runs/" + cold_id)
        assert (
            refused.status_code == 400 and refused.json()["error"]["code"] == "VERIFICATION_FAILED"
        )
        assert cold_seen == []
        from sim2act.db import runs

        with env[0].tx() as c:
            failed = c.execute(select(runs).where(runs.c.id == cold_id)).mappings().one()
            assert failed["status"] == "FAILED"
            assert failed["error"]["code"] == "VERIFICATION_FAILED"
            assert not c.execute(select(operations).where(operations.c.run_id == cold_id)).first()
        return
    completed = state(env, cold_id)
    assert completed["status"] == "WAITING_APPROVAL", completed
    trace = completed["result"]["protocol_result"]["evidence"]["tool_trace"]
    assert trace[0]["args"]["resource_id"] == cold_resource
    assert (
        trace[0]["data"]["hash"]
        != source["result"]["protocol_result"]["evidence"]["tool_trace"][0]["data"]["hash"]
    )
    assert "海岚工作室" not in json.dumps(cold_seen, ensure_ascii=False)
    assert accept(cold_id, completed, cold_contract)["status"] == "SUCCEEDED"
    with env[0].tx() as c:
        extract_attempt = (
            c.execute(select(attempts).where(attempts.c.run_id == extraction_id)).mappings().one()
        )
        assert (
            extract_attempt["parameters"]["protocol_candidate_receipt"] == plan["candidate_receipt"]
        )
        assert plan["candidate_receipt"]["attempt_id"] == extract_attempt["id"]
