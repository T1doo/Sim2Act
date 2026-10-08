"""Disposable loopback OFFLINE_TEST fixture for the normal page; never production.

No environment/config/secret discovery, existing database, real model or arbitrary
provider. Explicitly initializes only its own temporary synthetic SQLite fixture.
"""
import argparse
import json
import socket
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

import httpx
import uvicorn

from sim2act import natural_activations as activation
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store
from sim2act.goals import create_card, inspect_card
from sim2act.worker import Worker

PUBLIC_FIXTURE_TOKEN = "synthetic-offline-activation-demo"


@contextmanager
def demo():
    with tempfile.TemporaryDirectory(prefix="sim2act-natural-offline-") as folder:
        root = Path(folder)
        url = "sqlite:///" + str(root / "synthetic.db")
        store = Store(url, test_only=True)
        try:
            store.initialize()  # Explicit fixture migration, before API construction.
            settings = Settings(url, root, goal_planner_provider="intern-s2",
                                natural_activation_enabled=True, rpm=1)
            owner = store.user("Public synthetic demo identity", PUBLIC_FIXTURE_TOKEN)
            project = store.project(owner, "OFFLINE_TEST — fixed synthetic CSV")
            resource = store.resource(owner, project, "fixed.csv", "csv", activation.CSV)
            cards = {kind: create_card(store, owner, project, activation.synthetic_goal(resource, kind))
                     for kind in activation.KINDS}
            cards = {kind: inspect_card(store, owner, card["id"]) for kind,card in cards.items()}
            draft = activation.create(store, owner, project, {"goal_bindings": [
                {"kind": k, "card_id": c["id"], "expected_version": c["version"],
                 "expected_fingerprint": c["fingerprint"]} for k,c in cards.items()
            ], "request_key": "owned-synthetic-demo"}, settings)
            session = activation.approve(store, owner, draft["id"], {
                "expected_version": draft["version"],
                "expected_scope_fingerprint": draft["scope_fingerprint"],
                "request_key": "owned-offline-test-only", "consent": activation.CONSENT,
            }, settings)
            calls = []
            def handler(request):
                body = json.loads(request.content)
                fp = json.loads(body["messages"][1]["content"])["saved_goal"]["fingerprint"]
                kind = next(k for k,c in cards.items() if c["fingerprint"] == fp)
                calls.append(kind)
                plan = {"version": "natural-goal-plan.v1", "source_goal_fingerprint": fp,
                        "interpretation": {"objective": cards[kind]["content"]["goal"],
                                           "assumptions": [], "unresolved": []},
                        "steps": [{"id": "only", "tool_ref": "resource.read" if kind=="read_preview"
                                   else "data.aggregate_csv", "resource_id": resource,
                                   "depends_on": [],
                                   **({"column": "quantity_z"} if kind=="sum_quantity_z" else {})}]}
                return httpx.Response(200, json={"model": "Intern-S2",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                    "choices": [{"finish_reason": "stop", "message": {
                        "role": "assistant", "content": json.dumps(plan)}}]})
            worker = Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler))
            yield {"app": create_app(store, settings), "store": store, "settings": settings,
                   "owner": owner, "project": project, "cards": cards, "session": session,
                   "worker": worker, "calls": calls, "root": root}
        finally:
            store.engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    with demo() as fixture, socket.socket() as listener:
        listener.bind(("127.0.0.1", args.port))
        port = listener.getsockname()[1]
        stop = threading.Event()
        errors = []
        def work():
            try:
                while not stop.is_set():
                    fixture["worker"].once()
                    stop.wait(.2)
            except Exception as error:
                errors.append(type(error).__name__)
                stop.set()
        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        print(f"OFFLINE_TEST fixture only: http://127.0.0.1:{port}", flush=True)
        print("Public synthetic fixture login: " + PUBLIC_FIXTURE_TOKEN, flush=True)
        print("Read sessions → choose OFFLINE_TEST → open frozen goal → generate → acknowledge plan.", flush=True)
        print("Wait at least 60s between planning sends; each Run expires 120s after acceptance.", flush=True)
        print("Fixed handwritten offline plans; actual registered tools. No real model or LIVE authority.", flush=True)
        print("Ctrl+C stops this fixture and deletes only its temporary synthetic data.", flush=True)
        try:
            uvicorn.Server(uvicorn.Config(fixture["app"], host="127.0.0.1", port=port,
                log_level="error", timeout_graceful_shutdown=5)).run(sockets=[listener])
        except KeyboardInterrupt:
            pass  # Uvicorn may re-raise the owned Ctrl+C after stopping the server.
        finally:
            stop.set()
            thread.join(5)
            if thread.is_alive() or errors:
                raise RuntimeError("Owned offline worker did not finish cleanly: " + ",".join(errors))


if __name__ == "__main__":
    main()
