import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from sqlalchemy import select

from sim2act.db import attempts, runs
from sim2act.errors import DomainError
from sim2act.model import MockModel, normalize_usage
from sim2act.probe import offline_probe, parse_model_list
from sim2act.worker import Worker


def test_AT06_independent_heartbeat_while_model_waits(env):
    store, s, client, a, b, pid, res = env
    rid = store.submit(a, pid, "slow synthetic model", [res], "slow")
    entered = threading.Event()
    release = threading.Event()

    class WaitingMock(MockModel):
        def request(self, messages, tools):
            if not entered.is_set():
                entered.set()
                assert release.wait(5), "Bounded fault wait expired"
            return super().request(messages, tools)

    worker = Worker(store, replace(s, lease_seconds=1), WaitingMock())
    thread = threading.Thread(target=worker.once)
    thread.start()
    try:
        assert entered.wait(3)
        time.sleep(1.2)  # Exceeds initial lease while independent heartbeat must refresh it.
        assert store.claim("competitor", 1) is None
        with store.engine.connect() as c:
            run = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
            assert run["fence"] == 1 and run["lease_until"] > time.time()
    finally:
        release.set()
        thread.join(timeout=5)
        assert not thread.is_alive()
    assert store.inspect(a, rid)["status"] == "PARTIAL"


def test_AT06_two_concurrent_claims_do_not_share_run(env):
    store, s, client, a, b, pid, res = env
    store.submit(a, pid, "first", [res], "claim-one")
    store.submit(a, pid, "second", [res], "claim-two")
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda name: store.claim(name, 30), ["one", "two"]))
    assert len({r["id"] for r in claims}) == 2
    assert all(r["fence"] == 1 for r in claims)


def test_AT07_invalid_response_usage_is_not_lost(env):
    store, s, client, a, b, pid, res = env
    rid = store.submit(a, pid, "quota fixture", [res], "failed-usage")

    class Invalid:
        def request(self, messages, tools):
            return {
                "model": "MOCK-intern-contract",
                "choices": [],
                "usage": {"prompt_tokens": 11, "completion_tokens": 2, "total_tokens": 13},
            }

    Worker(store, s, Invalid()).once()
    with store.engine.connect() as c:
        rows = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
        assert len(rows) == 2 and all(r["status"] == "FAILED" for r in rows)
        assert all(r["usage"]["tokens"]["total_tokens"] == 13 for r in rows)
        ctx = c.execute(select(runs.c.context).where(runs.c.id == rid)).scalar_one()
        assert ctx["repairs"] == 1 and ctx["requests"] == 2
    assert normalize_usage({"usage": {"total_tokens": -1}}) == {"status": "unknown", "tokens": None}


def test_offline_probe_never_loads_ambient_credentials(monkeypatch):
    from sim2act.config import Settings

    def forbidden():
        raise AssertionError("No ambient configuration allowed in offline probe")

    monkeypatch.setattr(Settings, "from_env", forbidden)
    report = offline_probe()
    assert report["live_status"] == "BLOCKED" and report["model_list"]["provenance"] == "SYNTHETIC"
    assert report["attempt_modes"] == ["MOCK", "MOCK"]
    assert len(report["wire_requests"]) == 2 and all(
        x["stream"] is False for x in report["wire_requests"]
    )
    assert report["tool_feedback_revision"] == "PASS (MOCK)"
    try:
        parse_model_list({"object": "list", "data": [{"object": "model", "id": 123}]})
    except DomainError:
        pass
    else:
        raise AssertionError("Invalid model list accepted")
