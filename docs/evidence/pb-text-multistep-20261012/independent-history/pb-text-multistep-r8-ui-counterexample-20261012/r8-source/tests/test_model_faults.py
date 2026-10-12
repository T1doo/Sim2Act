import json
import time
from dataclasses import replace

import httpx
import pytest
from sqlalchemy import insert, select, update

from sim2act.db import attempts, new_id, operations, reservations, runs
from sim2act.errors import DomainError
from sim2act.model import InternModel, MockModel, parse_response
from sim2act.worker import Worker


@pytest.mark.parametrize(
    "response",
    [
        {
            "choices": [
                {"finish_reason": "length", "message": {"role": "assistant", "content": "partial"}}
            ]
        },
        {
            "choices": [
                {"finish_reason": None, "message": {"role": "assistant", "content": "unknown"}}
            ]
        },
        {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "cut",
                                "type": "function",
                                "function": {
                                    "name": "resource.read",
                                    "arguments": '{"resource_id":',
                                },
                            }
                        ],
                    },
                }
            ]
        },
        {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "shell",
                                "type": "function",
                                "function": {"name": "os.system", "arguments": "{}"},
                            }
                        ],
                    },
                }
            ]
        },
    ],
)
def test_AT07_incomplete_unknown_tool_never_dispatch(response):
    with pytest.raises(DomainError):
        parse_response(response)


def test_AT07_http429_fault_and_wire_contract(env):
    s = replace(env[1], live_enabled=True, mode="live", token="SYNTHETIC_NOT_A_REAL_KEY")
    seen = []

    def handle(request):
        seen.append(json.loads(request.content))
        return httpx.Response(429, json={"error": "quota fault"})

    model = InternModel(s, httpx.MockTransport(handle))
    with pytest.raises(DomainError) as e:
        model.request([{"role": "user", "content": "synthetic"}], [])
    assert e.value.code == "RATE_LIMITED"
    assert len(seen) == 1  # no invisible SDK retry
    assert seen[0]["stream"] is False
    assert seen[0]["model"] == "intern-s2"


def test_AT07_shared_database_quota(env):
    store, s, client, a, b, pid, res = env
    rid = store.submit(a, pid, "test", [res], "quota")
    run = store.claim("worker", 30)
    one, two = Worker(store, replace(s, rpm=1)), Worker(store, replace(s, rpm=1))
    ctx = dict(run["context"])
    ctx["messages"] = [{"role": "user", "content": "synthetic"}]
    one.reserve(rid, run["fence"], ctx)
    with pytest.raises(DomainError) as e:
        two.reserve(rid, run["fence"], ctx)
    assert e.value.code == "RATE_LIMITED"
    with store.engine.connect() as c:
        assert len(c.execute(select(reservations)).all()) == 1


def test_AT07_repair_count_unknown_usage_and_no_partial_effect(env):
    store, s, client, a, b, pid, res = env
    rid = store.submit(a, pid, "test", [res], "truncated")

    class TruncatedThenMock(MockModel):
        count = 0

        def request(self, messages, tools):
            self.count += 1
            if self.count == 1:
                return {
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {
                                "role": "assistant",
                                "content": "fault injection: 120-second truncation shape",
                            },
                        }
                    ]
                }
            return super().request(messages, tools)

    Worker(store, s, TruncatedThenMock()).once()
    result = client.get(f"/api/runs/{rid}").json()
    assert result["status"] == "PARTIAL"
    with store.engine.connect() as c:
        rows = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
        assert len(rows) == 3
        assert sum(x["status"] == "FAILED" for x in rows) == 1
        assert all(x["usage"]["status"] == "unknown" and x["usage"]["tokens"] is None for x in rows)
        assert len(c.execute(select(operations).where(operations.c.run_id == rid)).all()) == 1
        assert (
            c.execute(select(runs.c.context).where(runs.c.id == rid)).scalar_one()["repairs"] == 1
        )


def test_AT06_unresolved_model_attempt_not_blindly_recalled(env):
    store, s, client, a, b, pid, res = env
    rid = store.submit(a, pid, "test", [res], "lost-response")
    store.claim("lost-worker", 30)
    with store.tx() as c:
        c.execute(
            insert(attempts).values(
                id=new_id("attempt"), run_id=rid, status="STARTED", usage={"status": "unknown"}
            )
        )
        c.execute(update(runs).where(runs.c.id == rid).values(lease_until=time.time() - 1))
    assert store.claim("new-worker", 30) is None
    assert client.get(f"/api/runs/{rid}").json()["status"] == "WAITING_RESOURCE"
    with pytest.raises(DomainError) as e:
        store.command(a, rid, "resume", 2)
    assert e.value.code == "OUTCOME_UNKNOWN"


def test_live_default_blocks_before_network(env):
    def must_not_call(request):
        raise AssertionError("Network must not be called")

    with pytest.raises(DomainError) as e:
        InternModel(env[1], httpx.MockTransport(must_not_call)).request([], [])
    assert e.value.code == "RESOURCE_UNAVAILABLE"
