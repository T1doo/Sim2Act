"""Owned SQLite/mock children; observer waits only after a real advance commits."""

import json
import os
import socket
import sys
from pathlib import Path

import httpx
import uvicorn
from sqlalchemy import select
from test_natural_spec_apps import SOURCE, transport

from sim2act import pa_spec_apps
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, attempts, operations
from sim2act.worker import Worker


def main():
    config_path, role, token = sys.argv[1:]
    config = json.loads(Path(config_path).read_text())
    assert config["token"] == token and role in {"api", "old-worker", "new-worker"}
    root = Path(config_path).parent
    initialize_calls = []

    def forbidden_initialize(*args, **kwargs):
        initialize_calls.append(True)
        raise AssertionError("Child must reopen without initialize")

    Store.initialize = forbidden_initialize
    store = Store(config["database_url"], test_only=True)
    settings = Settings(config["database_url"], root, mode="mock", live_enabled=False,
                        token="", goal_planner_provider="intern-s2", lease_seconds=30, run_seconds=300)
    assert store.sqlite

    def emit(event, **values):
        value = dict(event=event, role=role, pid=os.getpid(),
                     starttime=Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()[19],
                     token=token, initialize_calls=len(initialize_calls),
                     lease_seconds=settings.lease_seconds, run_seconds=settings.run_seconds, **values)
        with (root / f"{role}-events.jsonl").open("a") as output:
            output.write(json.dumps(value) + "\n")
        print(json.dumps(value), flush=True)

    if role == "api":
        listener = socket.socket()
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", config["port"]))
        listener.listen()
        emit("BOUND", host="127.0.0.1", port=config["port"])
        server = uvicorn.Server(uvicorn.Config(create_app(store, settings),
            host="127.0.0.1", port=config["port"], log_level="warning", access_log=False))
        server.run(sockets=[listener])
        return

    sent = []
    active = [0]
    runtime = transport([], SOURCE)

    def mock(request):
        active[0] += 1
        try:
            response = runtime.handle_request(request)
            sent.append(json.loads(request.content))
            with (root / f"{role}-wire.jsonl").open("a") as output:
                output.write(json.dumps(dict(request=sent[-1], response=response.json())) + "\n")
            return response
        finally:
            active[0] -= 1

    worker = Worker(store, settings, goal_planner_transport=httpx.MockTransport(mock))
    if role == "old-worker":
        original = pa_spec_apps.advance
        observed = [False]

        def advance(current_worker, run, **kwargs):
            again = original(current_worker, run, **kwargs)
            # The original function and its transaction have returned. Never
            # intercept its commit/guard/model callback or change a product row.
            if again and not observed[0] and len(sent) == 1:
                with store.tx() as c:
                    rows = c.execute(select(attempts.c.id, attempts.c.status).where(
                        attempts.c.run_id == run["id"])).all()
                    ops = c.execute(select(operations.c.id, operations.c.status).where(
                        operations.c.run_id == run["id"])).all()
                assert len(rows) == 1 and rows[0].status == "VERIFIED"
                assert len(ops) == 2 and all(row.status == "VERIFIED" for row in ops)
                assert active[0] == 0
                observed[0] = True
                emit("SAFE_BOUNDARY", run_id=run["id"], worker_id=worker.id,
                     calls=len(sent), active_senders=active[0])
                assert json.loads(sys.stdin.readline()) == {"command": "continue-to-pause"}
            return again

        pa_spec_apps.advance = advance
        claimed = worker.once()
        assert claimed and observed[0] and len(sent) == 1 and active[0] == 0
        emit("PAUSE_SETTLED", worker_id=worker.id, claimed=claimed, calls=len(sent))
    else:
        assert not worker.once() and not sent
        emit("IDLE_BEFORE_DOM", worker_id=worker.id, claimed=False, calls=0)
        assert json.loads(sys.stdin.readline()) == {"command": "probe-before-resume"}
        assert not worker.once() and not sent
        emit("IDLE_AFTER_DOM", worker_id=worker.id, claimed=False, calls=0)
        assert json.loads(sys.stdin.readline()) == {"command": "run-after-resume"}
        assert worker.once() and len(sent) == 1 and active[0] == 0
        assert not worker.once() and len(sent) == 1
        emit("RESUMED_DONE", worker_id=worker.id, calls=len(sent), second_claim=False)
    store.engine.dispose()


if __name__ == "__main__":
    main()
