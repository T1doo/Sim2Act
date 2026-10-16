"""Owned loopback regression children; explicit SQLite/mock configuration only."""

import hashlib
import json
import os
import signal
import socket
import sys
from pathlib import Path

import httpx
import uvicorn
from test_goal_text_applications import wire
from test_natural_spec_apps import COLD, SOURCE, facts, recipe, transport

from sim2act import natural_specs as natural
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store
from sim2act.worker import Worker


def main():
    config_path, role, token = sys.argv[1:]
    config = json.loads(Path(config_path).read_text())
    assert config["token"] == token and role in {"api", "generation", "source", "cold"}
    root = Path(config_path).parent
    settings = Settings(
        "sqlite:///" + str(root / "fixture.db"), root,
        mode="mock", live_enabled=False, token="", goal_planner_provider="intern-s2",
    )
    store = Store(settings.database_url, test_only=True)
    # Initialization belongs to the parent once. Restart never resets the database.
    if role == "api":
        listener = socket.socket()
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", config["port"]))
        listener.listen()
        pid = os.getpid()
        (root / f"api-{pid}-bound.json").write_text(json.dumps(dict(
            pid=pid, starttime=Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19],
            token=token, host="127.0.0.1", port=config["port"],
        )))
        server = uvicorn.Server(uvicorn.Config(
            create_app(store, settings), host="127.0.0.1", port=config["port"],
            log_level="warning", access_log=False,
        ))
        server.run(sockets=[listener])
        return
    sent = []

    def generation(request):
        payload = json.loads(request.content)
        initial = json.loads(payload["messages"][1]["content"])
        feedback = [json.loads(m["content"]) for m in payload["messages"] if m["role"] == "tool"]
        graph = recipe("sequential")
        value = dict(
            recipe=graph,
            sample_nodes=[dict(step_id=step["step_id"], items=[
                item for item in facts(SOURCE)
                if item["kind"] in natural.MODEL_KINDS[step["operator"]]
            ]) for step in graph["steps"] if step["operator"] in natural.MODEL_KINDS],
            source_hash=hashlib.sha256(SOURCE.encode()).hexdigest(),
            goal=initial["saved_goal"]["snapshot"]["content"],
        )
        if len(sent) == 1:
            name, args = "resource.read", dict(resource_id=config["resource"])
        elif len(sent) == 2:
            assert feedback[0]["data"]["content"] == SOURCE
            name, args = "spec.check_candidate", dict(candidate=value)
        else:
            assert len(sent) == 3 and feedback[-1]["data"]["status"] == "PASS"
            return httpx.Response(200, json=wire(dict(role="assistant", content=json.dumps(value)), "stop"))
        return httpx.Response(200, json=wire(dict(role="assistant", content="", tool_calls=[dict(
            id=f"synthetic-{len(sent)}", type="function",
            function=dict(name=name, arguments=json.dumps(args)),
        )]), "tool_calls"))

    runtime_sent = []
    runtime = transport(runtime_sent, SOURCE if role == "source" else COLD)

    def mock(request):
        assert request.method == "POST" and request.url.host == "chat.intern-ai.org.cn"
        sent.append(json.loads(request.content))
        response = generation(request) if role == "generation" else runtime.handle_request(request)
        with (root / f"{role}-wire.jsonl").open("a") as output:
            output.write(json.dumps(dict(request=json.loads(request.content), response=response.json())) + "\n")
        return response

    assert Worker(store, settings, goal_planner_transport=httpx.MockTransport(mock)).once()
    assert len(sent) == (3 if role == "generation" else 2)
    (root / f"{role}-done.json").write_text(json.dumps(dict(calls=len(sent), status="PASS")))
    # Stay alive so stop/restart proves termination of a real owned Worker process.
    while True:
        signal.pause()


if __name__ == "__main__":
    main()
