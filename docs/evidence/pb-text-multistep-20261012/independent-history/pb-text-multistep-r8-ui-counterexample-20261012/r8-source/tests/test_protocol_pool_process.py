"""Independent owned PostgreSQL processes: budget cap and crash seams, no network."""

import json
import os
import pathlib
import subprocess
import sys
import time
from dataclasses import dataclass, field

import pytest
from sqlalchemy import select, update
from test_protocol_jobs import LIMITS, factory_for, source_payload, wire
from test_protocol_pool import claimed_source
from test_protocol_pool import env as _pool_env

from sim2act.db import Store, runs
from sim2act.errors import DomainError
from sim2act.protocol_jobs import enqueue
from sim2act.protocol_pool import OFFLINE_POOL, inspect_pool, require_pool
from sim2act.protocol_recovery import recover

env = _pool_env

PYTHON = sys.executable


@dataclass(repr=False)
class ProcessCase:
    fixture: tuple = field(repr=False)

    def __repr__(self):
        return "ProtocolProcessCase(connection omitted)"


@pytest.fixture
def process_case(env):
    if env[0].sqlite:
        pytest.skip("Actual independent PostgreSQL process regression")
    return ProcessCase(env)


def child(env, run, mode, folder):
    store = env[0]
    schema = store.engine.get_execution_options().get("schema_translate_map", {}).get(None)
    cfg = folder / (run["id"] + ".cfg.json")
    cfg.write_text(
        json.dumps({"folder": str(folder), "schema": schema, "run_id": run["id"], "mode": mode})
    )
    child_env = os.environ.copy()
    child_env["SIM2ACT_PROTOCOL_PROCESS_DATABASE_URL"] = env[5].s.database_url
    script = pathlib.Path(__file__).parent / "fixtures" / "protocol_pool_process_child.py"
    return subprocess.Popen(
        [PYTHON, str(script), str(cfg)],
        env=child_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def pause(store, run):
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == run["id"]).values(status="PAUSED", lease_until=0))


def test_actual_pg_two_process_final_slot(process_case, tmp_path):
    env = process_case.fixture
    store, user, pid, a, b, worker, _ = env
    if store.sqlite:
        pytest.skip("owned PG required")
    for i in range(13):
        _, run, snapshot = claimed_source(env, "warm-" + str(i))
        factory_for(env, [wire({"synthetic_warm": i})], "source_a")
        worker.protocol_runner_factory(worker, run, snapshot).call(
            [{"role": "user", "content": "owned budget warm probe"}], []
        )
        pause(store, run)
    _, first, _ = claimed_source(env, "last-a")
    otheruser = store.user("independent second owner", "synthetic-other-owner")
    otherpid = store.project(otheruser, "independent second project")
    content = pathlib.Path(
        "docs/evidence/model-protocol-preparation-20261006/materials/a-source/policy.txt"
    ).read_text()
    otherres = store.resource(otheruser, otherpid, "synthetic own policy", "txt", content)
    enqueue(store, otheruser, otherpid, "source", source_payload(otherres), "last-b", LIMITS)
    second = store.claim(worker.id, 30)
    assert second["id"] != first["id"]
    folder = tmp_path / "race"
    folder.mkdir()
    children = [child(env, r, "race", folder) for r in [first, second]]
    try:
        deadline = time.monotonic() + 10
        while not all((folder / (r["id"] + ".ready")).exists() for r in [first, second]):
            assert time.monotonic() < deadline
            time.sleep(0.01)
        (folder / "go").write_text("go")
        for p in children:
            assert p.wait(timeout=15) == 0
        observations = [
            json.loads((folder / (r["id"] + ".result.json")).read_text()) for r in [first, second]
        ]
        actual = (folder / "sends.jsonl").read_text().splitlines()
        assert len(actual) == 1, observations
        assert sum(o["status"] == "RECEIVED" for o in observations) == 1
        summary = inspect_pool(store, OFFLINE_POOL)
        assert summary["reserved_requests"] == 14
        print(
            "PG_FINAL_SLOT_TWO_OWNER_PROCESSES",
            json.dumps(observations),
            "actual_sends",
            len(actual),
        )
    finally:
        for p in children:
            if p.poll() is None:
                p.kill()
                p.wait()


@pytest.mark.parametrize(
    "mode,code,sendcount",
    [
        ("after_db_started", 73, 0),
        ("before_transport_after_sidecar", 77, 0),
        ("during_transport", 74, 1),
        ("after_response_before_db", 75, 1),
        ("after_finished", 76, 1),
    ],
)
def test_actual_pg_crash_restart_state_only(process_case, tmp_path, mode, code, sendcount, request):
    env = process_case.fixture
    store, user, pid, a, b, worker, _ = env
    if store.sqlite:
        pytest.skip("owned PG required")
    _, run, snapshot = claimed_source(env)
    folder = tmp_path / mode
    folder.mkdir()
    p = child(env, run, mode, folder)
    try:
        assert p.wait(timeout=15) == code
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()
    actual = (
        (folder / "sends.jsonl").read_text().splitlines()
        if (folder / "sends.jsonl").exists()
        else []
    )
    assert len(actual) == sendcount
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == run["id"]).values(lease_until=0))
    cold = Store(worker.s.database_url, test_only=True)
    cold.engine = cold.engine.execution_options(**store.engine.get_execution_options())
    request.addfinalizer(cold.engine.dispose)
    store = cold
    assert store.claim(worker.id, 30) is None
    with store.tx() as c:
        current = dict(c.execute(select(runs).where(runs.c.id == run["id"])).mappings().one())
    response = recover(
        store,
        user,
        run["id"],
        {
            "expected_version": current["version"],
            "expected_fence": current["fence"],
            "request_key": "state-only",
        },
    )
    assert response["provider_requests"] == 0 and response["automatic_resend"] is False
    if mode != "after_finished":
        with pytest.raises(DomainError):
            require_pool(store, OFFLINE_POOL)
        assert inspect_pool(store, OFFLINE_POOL)["halted"]
        accepted = enqueue(
            store, user, pid, "source", source_payload(a), "other-run-after-crash", LIMITS
        )
        other = store.claim(worker.id, 30)
        assert other["id"] == accepted["run_id"]
        restarted = child(env, other, "normal", folder)
        try:
            assert restarted.wait(timeout=15) == 0
        finally:
            if restarted.poll() is None:
                restarted.kill()
                restarted.wait()
        rejected = json.loads((folder / (other["id"] + ".result.json")).read_text())
        assert rejected == {"status": "REJECTED", "code": "OUTCOME_UNKNOWN"}
        observed_after_restart = (
            (folder / "sends.jsonl").read_text().splitlines()
            if (folder / "sends.jsonl").exists()
            else []
        )
        assert len(observed_after_restart) == sendcount
        assert inspect_pool(store, OFFLINE_POOL)["reserved_requests"] == 1
    else:
        require_pool(store, OFFLINE_POOL)
        assert response["recovery"] == "CONTINUATION_NOT_IMPLEMENTED"
    assert len(actual) == sendcount
    print(
        "PG_CRASH_STATE_ONLY",
        mode,
        "exit",
        code,
        "actual_sends",
        sendcount,
        "recovery",
        response["recovery"],
    )
