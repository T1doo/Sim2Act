"""Provider-shaped synthetic responses through MockTransport; no account or network calls."""

import json
import time
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from sim2act.api import create_app
from sim2act.db import attempts, operations, runs
from sim2act.errors import DomainError
from sim2act.model import (
    MODEL_IDENTITY_POLICY_VERSION,
    InternModel,
    MockModel,
    require_returned_model,
    returned_model_identity,
)
from sim2act.tools import definitions
from sim2act.worker import Worker


def live_wire_fixture(env):
    # Exercise the strict LIVE branch with a synthetic token and injected transport only.
    s = replace(env[1], mode="live", live_enabled=True, token="SYNTHETIC_NO_NETWORK", max_repairs=0)
    client = TestClient(create_app(env[0], s))
    client.headers.update({"Authorization": "Bearer synthetic-test-A"})
    return s, client


@pytest.mark.parametrize("returned", ["intern-s2", "Intern-S2"])
def test_provider_verified_name_variants_complete_real_code_tool_loop(env, returned):
    store, _, _, owner, _, pid, _ = env
    s, client = live_wire_fixture(env)
    seen = []

    def handle(request):
        assert str(request.url) == "https://chat.intern-ai.org.cn/api/v1/chat/completions"
        body = json.loads(request.content)
        assert body["model"] == "intern-s2"
        seen.append(body)
        raw = MockModel().request(body["messages"], body["tools"])
        raw["model"] = returned
        feedback = [m for m in body["messages"] if m["role"] == "tool"]
        if feedback:
            receipt = json.loads(feedback[-1]["content"])
            assert receipt["status"] == "VERIFIED" and receipt["data"]["content"] == "42"
            raw["choices"][0]["message"]["content"] = receipt["data"]["content"]
        return httpx.Response(200, json=raw)

    try:
        resource = client.post(
            f"/api/projects/{pid}/resources",
            json={"name": "synthetic42.txt", "format": "txt", "content": "42"},
        ).json()["id"]
        rid = client.post(
            f"/api/projects/{pid}/runs",
            json={
                "goal": "read authorized synthetic value",
                "resource_refs": [resource],
                "request_key": "case-variant",
            },
        ).json()["run_id"]
        Worker(store, s, InternModel(s, httpx.MockTransport(handle))).once()
        result = client.get(f"/api/runs/{rid}").json()
        assert result["status"] == "PARTIAL" and result["result"]["answer"] == "42"
        assert result["result"]["goal_acceptance"] == "NOT_RUN"
        assert len(seen) == 2 and len(result["result"]["receipts"]) == 1
        with store.engine.connect() as c:
            recorded = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
            assert len(recorded) == 2 and all(a["status"] == "RECEIVED" for a in recorded)
            for a in recorded:
                identity = a["parameters"]["model_identity"]
                assert a["request_model"] == identity["requested_model"] == "intern-s2"
                assert a["response_model"] == identity["raw_returned_model"] == returned
                assert identity["normalized_returned_model"] == "intern-s2"
                assert identity["normalization_policy_version"] == MODEL_IDENTITY_POLICY_VERSION
                assert identity["verdict"] == "ACCEPTED" and identity["enforced"] is True
    finally:
        client.close()


@pytest.mark.parametrize(
    "returned", ["intern-s1", "Intern-S1", "gpt-6.1-sol", "INTERN-S2", " intern-s2", None, 123]
)
def test_wrong_unverified_or_missing_model_never_dispatches_tool(env, returned):
    store, _, _, owner, _, pid, resource = env
    s, client = live_wire_fixture(env)

    def handle(request):
        body = json.loads(request.content)
        raw = MockModel().request(body["messages"], body["tools"])
        if returned is not None:
            raw["model"] = returned
        else:
            raw.pop("model")
        return httpx.Response(200, json=raw)

    try:
        rid = client.post(
            f"/api/projects/{pid}/runs",
            json={
                "goal": "must not dispatch",
                "resource_refs": [resource],
                "request_key": "rejected-model",
            },
        ).json()["run_id"]
        Worker(store, s, InternModel(s, httpx.MockTransport(handle))).once()
        result = client.get(f"/api/runs/{rid}").json()
        assert result["status"] == "FAILED" and result["error"]["code"] == "MODEL_OUTPUT_INVALID"
        with store.engine.connect() as c:
            assert not c.execute(select(operations).where(operations.c.run_id == rid)).first()
            a = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one()
            identity = a["parameters"]["model_identity"]
            assert identity["verdict"] == "REJECTED" and identity["enforced"] is True
            assert (
                a["response_model"]
                == identity["raw_returned_model"]
                == (returned if isinstance(returned, str) else None)
            )
            assert a["parameters"]["model_identity_policy_version"] == MODEL_IDENTITY_POLICY_VERSION
    finally:
        client.close()


def test_verified_model_alias_does_not_bypass_tool_scope(env):
    store, _, _, owner, _, pid, resource = env
    s, client = live_wire_fixture(env)
    other = client.post("/api/projects", json={"name": "other synthetic scope"}).json()["id"]
    foreign = client.post(
        f"/api/projects/{other}/resources",
        json={"name": "foreign.txt", "format": "txt", "content": "not authorized in this run"},
    ).json()["id"]

    def handle(request):
        body = json.loads(request.content)
        raw = MockModel().request(body["messages"], body["tools"])
        raw["model"] = "Intern-S2"
        raw["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = json.dumps(
            {"resource_id": foreign}
        )
        return httpx.Response(200, json=raw)

    try:
        rid = client.post(
            f"/api/projects/{pid}/runs",
            json={
                "goal": "scope stays enforced",
                "resource_refs": [resource],
                "request_key": "scope-denied",
            },
        ).json()["run_id"]
        Worker(store, s, InternModel(s, httpx.MockTransport(handle))).once()
        result = client.get(f"/api/runs/{rid}").json()
        assert result["status"] == "FAILED" and result["error"]["code"] == "PERMISSION_DENIED"
        with store.engine.connect() as c:
            assert not c.execute(select(operations).where(operations.c.run_id == rid)).first()
    finally:
        client.close()


@pytest.mark.parametrize(
    "returned,accepted", [("Intern-S2", True), ("intern-s1", False), (None, False)]
)
def test_unknown_attempt_recovery_uses_same_live_identity_policy(env, returned, accepted):
    store, _, _, owner, _, pid, resource = env
    s, client = live_wire_fixture(env)
    try:
        rid = client.post(
            f"/api/projects/{pid}/runs",
            json={
                "goal": "synthetic saved response",
                "resource_refs": [resource],
                "request_key": "recover-model",
            },
        ).json()["run_id"]
        run = store.claim("synthetic-lost-worker", 30)
        ctx = dict(run["context"])
        ctx["messages"] = [
            {
                "role": "user",
                "content": json.dumps({"goal": run["goal"], "resource_refs": [resource]}),
            }
        ]
        aid = Worker(store, s).reserve(rid, run["fence"], ctx)
        raw = MockModel().request(ctx["messages"], definitions())
        if returned is None:
            raw.pop("model")
        else:
            raw["model"] = returned
        with store.tx() as c:
            c.execute(update(runs).where(runs.c.id == rid).values(lease_until=time.time() - 1))
        assert store.claim("synthetic-recover", 30) is None
        version = client.get(f"/api/runs/{rid}").json()["version"]
        unresolved = client.get(f"/api/runs/{rid}/unresolved-attempts").json()[0]
        body = {
            "attempt_id": aid,
            "version": version,
            "decision": "record_response",
            "expected_fingerprint": unresolved["request_fingerprint"],
            "evidence": "SYNTHETIC saved provider-shaped response",
            "acknowledge_unknown_cost": True,
            "response": raw,
        }
        result = client.post(f"/api/runs/{rid}/reconcile", json=body)
        if accepted:
            assert (
                result.status_code == 200
                and result.json()["status"] == "PAUSED"
                and result.json()["tools_dispatched"] == 0
            )
            with store.engine.connect() as c:
                a = c.execute(select(attempts).where(attempts.c.id == aid)).mappings().one()
                assert (
                    a["response_model"] == "Intern-S2"
                    and a["parameters"]["model_identity"]["normalized_returned_model"]
                    == "intern-s2"
                )
                assert a["usage"] == {"status": "unknown", "tokens": None}
        else:
            assert (
                result.status_code == 400
                and result.json()["error"]["code"] == "MODEL_OUTPUT_INVALID"
            )
            with store.engine.connect() as c:
                assert (
                    c.execute(select(attempts.c.status).where(attempts.c.id == aid)).scalar_one()
                    == "STARTED"
                )
        with store.engine.connect() as c:
            assert not c.execute(select(operations).where(operations.c.run_id == rid)).first()
    finally:
        client.close()


def test_request_identity_is_not_case_folded_or_replaced():
    with pytest.raises(DomainError):
        require_returned_model(returned_model_identity("Intern-S2", "Intern-S2"))
    assert (
        returned_model_identity("intern-s2", "Intern-S2")["normalization_policy_version"]
        == "intern-s2-returned-name.v1"
    )
