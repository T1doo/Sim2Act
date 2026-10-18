"""Projects history opens the same saved natural result, with offline models only."""

import hashlib
import json
import os
import socket
import subprocess
import threading
import time
from pathlib import Path
from unittest.mock import patch

import httpx
import uvicorn
from test_natural_spec_apps import enqueue, inspect, ready, setup, transport
from test_spec_app_operations import snapshot

from sim2act.api import create_app
from sim2act.db import fingerprint
from sim2act.worker import Worker


def test_project_history_opens_original_natural_result_and_review(env, tmp_path):
    root = Path.cwd()
    production = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (root / "src/sim2act").rglob("*")
        if path.is_file() and path.suffix in {".py", ".js", ".html", ".css", ".json"}
    }
    data = setup(env)
    store, settings, client, principal, project, *_ = data
    assert store.sqlite and settings.mode == "mock"
    mocks, fixture_http, business = [], [], []

    def capture(reply):
        reply.read()
        request = reply.request
        fixture_http.append(dict(method=request.method, path=request.url.raw_path.decode(),
            body_text=request.content.decode(), status=reply.status_code,
            response_text=reply.content.decode(), sha256=hashlib.sha256(reply.content).hexdigest()))

    client.event_hooks["response"].append(capture)
    handle = httpx.MockTransport.handle_request
    async_handle = httpx.MockTransport.handle_async_request

    def mock_response(request, reply):
        mocks.append(dict(request_text=request.content.decode(), status=reply.status_code,
            response_text=reply.content.decode(), sha256=hashlib.sha256(reply.content).hexdigest()))
        return reply

    def mocked(transport_self, request):
        return mock_response(request, handle(transport_self, request))

    async def async_mocked(transport_self, request):
        return mock_response(request, await async_handle(transport_self, request))

    try:
        with patch.object(httpx.MockTransport, "handle_request", mocked), patch.object(
            httpx.MockTransport, "handle_async_request", async_mocked
        ):
            _, aid, release, instance, generation = ready(data, "single")
            rid = enqueue(data, release, instance, key="project-history-result")
            worker = Worker(store, settings, goal_planner_transport=transport(business))
            assert worker.once()
            run = inspect(data, instance, rid).json()
            assert run["status"] == "SUCCEEDED"
        assert len(generation) == 3 and len(business) == 1 and len(mocks) == 4
        assert run["result"]["checklist"]["owner_acceptance"] == "PENDING"
        other = store.project(principal, "Other result-navigation project")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        (tmp_path / "info.json").write_text(json.dumps(dict(
            base=f"http://127.0.0.1:{port}", project=project, other_project=other,
            app=aid, instance=instance["id"], release=release["id"], run=rid,
            app_run=run["app_run_id"])), encoding="utf-8")
        (tmp_path / "fixture-run.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
        before = snapshot(store)
        assert len(before["internal_app_runs"]) == len(before["internal_instance_data"]) == 1
        server = uvicorn.Server(uvicorn.Config(create_app(store, settings), host="127.0.0.1",
            port=port, log_level="error"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            until = time.monotonic() + 10
            while not server.started:
                assert thread.is_alive() and time.monotonic() < until
                time.sleep(.01)
            try:
                result = subprocess.run(["node", str(Path(__file__).with_name("project_run_result_ui.cjs")),
                    str(tmp_path)], capture_output=True, text=True, timeout=360,
                    env={**os.environ, "NODE_PATH": str(root / "scripts/engineering-ci/node_modules")})
            except subprocess.TimeoutExpired as error:
                for name, content in [("stdout", error.stdout), ("stderr", error.stderr)]:
                    (tmp_path / ("driver." + name)).write_bytes(
                        content.encode() if isinstance(content, str) else content or b"")
                raise
            (tmp_path / "driver.stdout").write_text(result.stdout, encoding="utf-8")
            (tmp_path / "driver.stderr").write_text(result.stderr, encoding="utf-8")
            assert result.returncode == 0, result.stdout + result.stderr
            page = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
            assert page["status"] == "PASS"
            assert not [r for r in page["requests"] if r["method"] != "GET"]
            assert not page["downloads"]
            assert len(page["static_resource_loads"]) == 27
            for row in page["static_resource_loads"]:
                path = root / "src/sim2act/web" / (row["path"].lstrip("/") or "index.html")
                assert row["status"] == 200
                assert row["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
            after = snapshot(store)
            assert before == after, [table for table in before if before[table] != after[table]]
            assert production == {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in production}
            proof = dict(status="PASS", production_sha256=production,
                before_fingerprint=fingerprint(before), after_fingerprint=fingerprint(after),
                protected_tables_unchanged=sorted(before), changed_tables=[],
                table_fingerprints={table: dict(rows=len(rows), sha256=fingerprint(rows)) for table, rows in before.items()},
                generation_mock_requests=3, fixture_business_mock_requests=1, mock_requests=len(mocks),
                fixture_business_worker_calls=1, fixture_worker_id=worker.id, page_worker_calls=0,
                real_model_requests=0, page_post_requests=0, native_browser="NOT_RUN", pg="NOT_RUN",
                windows="NOT_RUN", pb_dynamic="NOT_RUN", real_semantic_acceptance="NOT_RUN")
            (tmp_path / "proof.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
        finally:
            server.should_exit = True
            thread.join(10)
            assert not thread.is_alive(), "Owned loopback server did not stop"
    finally:
        (tmp_path / "mock-wire.json").write_text(json.dumps(mocks, indent=2), encoding="utf-8")
        (tmp_path / "fixture-http.json").write_text(json.dumps(fixture_http, indent=2), encoding="utf-8")
        client.close()
