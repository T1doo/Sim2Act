"""Synthetic child; inherited owned DB URL never enters config, output or traceback."""

import json
import os
import pathlib
import sys
import time
from dataclasses import replace

import httpx
from sqlalchemy import select

from sim2act.config import Settings
from sim2act.db import Store, protocol_jobs, runs
from sim2act.errors import DomainError
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider, initialize_ledger
from sim2act.protocol_api import ProtocolAttemptRunner
from sim2act.worker import Worker

cfg = json.loads(pathlib.Path(sys.argv[1]).read_text())
folder = pathlib.Path(cfg["folder"])
mode = cfg["mode"]
url = os.environ["SIM2ACT_PROTOCOL_PROCESS_DATABASE_URL"]
store = Store(url, test_only=True)
if cfg["schema"] is not None:
    store.engine = store.engine.execution_options(schema_translate_map={None: cfg["schema"]})
with store.tx() as c:
    run = dict(c.execute(select(runs).where(runs.c.id == cfg["run_id"])).mappings().one())
    snapshot = c.execute(
        select(protocol_jobs.c.accepted_snapshot).where(protocol_jobs.c.run_id == run["id"])
    ).scalar_one()
settings = Settings(url, folder, max_requests=3, max_repairs=0)
worker = Worker(store, settings)
worker.id = run["worker_id"]
clock = [0]


def tick():
    clock[0] += 7
    return clock[0]


def response(request):
    with open(folder / "sends.jsonl", "a") as stream:
        stream.write(json.dumps({"pid": os.getpid(), "run_id": run["id"], "mode": mode}) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    if mode == "during_transport":
        os._exit(74)
    return httpx.Response(
        200,
        json={
            "model": "intern-s2",
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": '{"synthetic_probe":true}'},
                }
            ],
        },
    )


model = InternModel(
    replace(settings, live_enabled=True, token="synthetic-only-no-network"),
    httpx.MockTransport(response),
)
ledger = folder / (run["id"] + "-child.json")
initialize_ledger(ledger, snapshot["scope"])


def authorize(scope):
    with store.tx() as c:
        store.guard(c, run["id"], run["fence"])
        for ref in scope["resource_ids"]:
            store.authorize(
                c, run["principal_id"], run["runtime_id"], run["project_id"], ref, "resource.read"
            )
    return True


provider = BudgetedProvider(
    model, ledger, snapshot["scope"], "source_a", authorize=authorize, clock=tick
)
runner = ProtocolAttemptRunner(worker, run, snapshot, provider)
if mode == "before_transport_after_sidecar":

    def before_transport(*args, **kwargs):
        os._exit(77)

    model.request = before_transport

if mode == "after_db_started":
    ctx = run["context"]
    ctx["messages"] = [{"role": "user", "content": "synthetic owned global budget probe"}]
    worker.reserve(run["id"], run["fence"], ctx, request_tools=[])
    os._exit(73)
if mode == "after_response_before_db":

    def die(*args, **kwargs):
        os._exit(75)

    runner._record = die
if mode == "race":
    (folder / (run["id"] + ".ready")).write_text("ready")
    deadline = time.monotonic() + 10
    while not (folder / "go").exists():
        if time.monotonic() > deadline:
            raise RuntimeError("barrier timeout")
        time.sleep(0.01)
try:
    runner.call([{"role": "user", "content": "synthetic owned global budget probe"}], [])
    if mode == "after_finished":
        os._exit(76)
    result = {"status": "RECEIVED"}
except DomainError as exc:
    result = {"status": "REJECTED", "code": exc.code}
except BaseException as exc:
    result = {"status": "ERROR", "error_class": type(exc).__name__}
(folder / (run["id"] + ".result.json")).write_text(json.dumps(result))
store.engine.dispose()
