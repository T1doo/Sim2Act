"""Opt-in pytest diagnostic: owned synthetic schema/role only; no query text or secrets."""

import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url

from sim2act.db import events, heartbeats, internal_instance_data, operations, runs

OUT = Path(os.environ["SIM2ACT_RECOVERY_DIAG_DIR"])
OUT.mkdir(parents=True, exist_ok=True)
WRAPPER = Path(__file__).with_name("pg_trace_child.py")


def bounded_engine(store):
    return create_engine(
        store.engine.url,
        connect_args={
            "connect_timeout": 1,
            "options": "-cstatement_timeout=200 -clock_timeout=200",
        },
        pool_size=1,
        max_overflow=0,
        pool_timeout=1,
    ).execution_options(**store.engine.get_execution_options())


@pytest.fixture(autouse=True)
def owned_probe(request, monkeypatch):
    if "real_pg_process" not in request.node.name:
        yield
        return
    env = request.getfixturevalue("env")
    role = make_url(request.getfixturevalue("runtime_role")).username
    fixture = Path(request.node.fspath).parent / "fixtures" / "internal_app_worker.py"
    popen = subprocess.Popen
    stopped = threading.Event()
    samples = []
    sampler = bounded_engine(env[0])

    def launch(argv, *args, **kwargs):
        if len(argv) > 1 and Path(argv[1]).resolve() == fixture.resolve():
            argv = [argv[0], str(WRAPPER), str(fixture)]
        return popen(argv, *args, **kwargs)

    def sample():
        while not stopped.wait(0.1) and len(samples) < 200:
            try:
                with sampler.connect() as c:
                    c.execute(text("SET TRANSACTION READ ONLY"))
                    rows = (
                        c.execute(
                            text(
                                "SELECT pid,state,wait_event_type,wait_event FROM pg_stat_activity WHERE usename=:role"
                            ),
                            {"role": role},
                        )
                        .mappings()
                        .all()
                    )
                    pids = [r["pid"] for r in rows]
                    locks = (
                        c.execute(
                            text(
                                "SELECT pid,locktype,mode,granted FROM pg_locks WHERE pid = ANY(:pids)"
                            ),
                            {"pids": pids},
                        )
                        .mappings()
                        .all()
                        if pids
                        else []
                    )
                    snapshots = [
                        dict(r)
                        for r in c.execute(
                            select(
                                runs.c.id,
                                runs.c.status,
                                runs.c.fence,
                                runs.c.lease_until,
                                runs.c.worker_id,
                            )
                        ).mappings()
                    ]
                    samples.append(
                        {
                            "runs": snapshots,
                            "wall": time.time(),
                            "mono": time.monotonic(),
                            "activity": [dict(r) for r in rows],
                            "locks": [dict(r) for r in locks],
                        }
                    )
            except Exception as e:
                samples.append({"error_class": type(e).__name__})
                return

    monkeypatch.setattr(subprocess, "Popen", launch)
    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    yield
    stopped.set()
    thread.join(timeout=2)
    name = request.node.name.replace("[", "-").replace("]", "")
    try:
        (OUT / (name + "-locks.json")).write_text(
            json.dumps({"thread_stopped": not thread.is_alive(), "samples": samples}, indent=2)
            + "\n"
        )
        for path in env[1].data_dir.glob("diagnostic-child-*.jsonl"):
            (OUT / (name + "-" + path.name)).write_bytes(path.read_bytes())
    except Exception as e:
        print("Observer archive unavailable: " + type(e).__name__)
    try:
        sampler.dispose()
    except Exception as e:
        print("Observer sampler close unavailable: " + type(e).__name__)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or "real_pg_process" not in item.name or "env" not in item.funcargs:
        return
    try:
        store = item.funcargs["env"][0]
        import sim2act.app_jobs

        j = {
            "node": item.nodeid,
            "outcome": report.outcome,
            "wall": time.time(),
            "mono": time.monotonic(),
            "module": sim2act.app_jobs.__file__,
            "app_jobs_sha256": hashlib.sha256(
                Path(sim2act.app_jobs.__file__).read_bytes()
            ).hexdigest(),
        }
        observer = bounded_engine(store)
        with observer.connect() as c:
            c.execute(text("SET TRANSACTION READ ONLY"))
            j["runs"] = [
                dict(r)
                for r in c.execute(
                    select(
                        runs.c.id,
                        runs.c.status,
                        runs.c.fence,
                        runs.c.lease_until,
                        runs.c.worker_id,
                        runs.c.version,
                    )
                ).mappings()
            ]
            j["events"] = [
                dict(r)
                for r in c.execute(
                    select(events.c.run_id, events.c.kind, events.c.created_at).order_by(
                        events.c.created_at
                    )
                ).mappings()
            ]
            j["operations"] = [
                dict(r)
                for r in c.execute(select(operations.c.run_id, operations.c.status)).mappings()
            ]
            j["heartbeats"] = [
                dict(r) for r in c.execute(select(heartbeats.c.id, heartbeats.c.at)).mappings()
            ]
            j["result_count"] = len(c.execute(select(internal_instance_data.c.instance_id)).all())
        name = item.name.replace("[", "-").replace("]", "")
        (OUT / (name + "-final.json")).write_text(json.dumps(j, indent=2) + "\n")
    except Exception as e:
        print("Observer final snapshot unavailable: " + type(e).__name__)
    finally:
        if "observer" in locals():
            try:
                observer.dispose()
            except Exception as e:
                print("Observer snapshot close unavailable: " + type(e).__name__)
