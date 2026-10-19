"""Explicit table-bar.v1 over legal synthetic generation/Worker and loopback HTTP."""

import hashlib
import json
import re
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
import test_goal_text_applications as literal
import uvicorn
from fastapi import Header
from sqlalchemy import select
from test_local_record_apps import snapshot
from test_persistent_app_runs import NoModel

from sim2act.api import create_app
from sim2act.db import grants
from sim2act.worker import Worker


@pytest.mark.parametrize("case", ["display", "guards"])
def test_explicit_table_chart_actual_http(env, tmp_path, monkeypatch, case):
    data = literal.setup(env)
    store, settings, client, owner, project, resource, _ = data
    assert store.sqlite and store.test_only and settings.mode == "mock" and not settings.token
    raw_http, workers, claims, revocations = [], [], [], []
    original_claim = store.claim

    def trace(response):
        response.read()
        request = response.request
        raw_http.append(dict(method=request.method, url=str(request.url),
            body=request.content.decode() if request.content else None,
            status=response.status_code, response_text=response.text))

    def claim(worker_id, *args, **kwargs):
        value = original_claim(worker_id, *args, **kwargs)
        claims.append(dict(worker_id=worker_id, run_id=value["id"] if value else None,
                           fence=value["fence"] if value else None))
        return value

    def observed_worker(*args, **kwargs):
        worker = Worker(*args, **kwargs)
        original_once = worker.once

        def once():
            row = dict(worker_id=worker.id, started=time.time(),
                runtime="MockTransport generation" if kwargs.get("goal_planner_transport") else "NoModel")
            workers.append(row)
            try:
                row["claimed"] = original_once()
                return row["claimed"]
            finally:
                row["finished"] = time.time()

        worker.once = once
        return worker

    def save(name, value):
        (tmp_path / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")

    client.event_hooks["response"].append(trace)
    monkeypatch.setattr(store, "claim", claim)
    monkeypatch.setattr(literal, "Worker", observed_worker)
    thread = server = None
    try:
        def compose(raw, turn, _):
            if turn == 2:
                value = json.loads(raw["choices"][0]["message"]["content"])
                value["manifest"]["views"] = [dict(component_ref="text", output_field="term"),
                    dict(component_ref="table", output_field="citations"),
                    dict(component_ref="chart", output_field="citations")]
                raw["choices"][0]["message"]["content"] = json.dumps(value, ensure_ascii=False)

        generation, generated, sent = literal.generate(data, mutation=compose)
        save("mock-generation-requests.json", sent)
        assert len(sent) == 2
        aid, _ = literal.confirm(data, generation, generated)
        original_release, instance = literal.release_instance(data, aid)
        empty = client.post(f"/api/internal/releases/{original_release['id']}/instances", json={
            "expected_release_fingerprint": original_release["fingerprint"], "request_key": "chart-empty"})
        assert empty.status_code == 201, empty.text
        outputs = []

        def run(term, release):
            accepted = client.post(f"/api/internal/instances/{instance['id']}/runs", json={
                "expected_revision": instance["revision"],
                "expected_release_fingerprint": release["fingerprint"],
                "input": {"term": term}, "request_key": "chart-" + term})
            assert accepted.status_code == 202, accepted.text
            assert observed_worker(store, settings, NoModel()).once()
            response = client.get(f"/api/internal/instances/{instance['id']}/runs/{accepted.json()['run_id']}")
            assert response.status_code == 200 and response.json()["status"] == "SUCCEEDED", response.text
            outputs.append(response.json())

        run("Alpha", original_release)
        run("NoMatch", original_release)
        candidate = client.get(f"/api/apps/{aid}").json()
        approval = client.post(f"/api/internal/apps/{aid}/release-approvals", json={
            "expected_draft_fingerprint": candidate["fingerprint"], "sample_input": {"term": "Alpha"}})
        assert approval.status_code == 201, approval.text
        committed = client.post(f"/api/internal/approvals/{approval.json()['id']}/commit",
            json={"fingerprint": approval.json()["fingerprint"]})
        assert committed.status_code == 200, committed.text
        newer = committed.json()
        approved = client.post(f"/api/internal/instances/{instance['id']}/switch-approvals", json={
            "target_release_id": newer["id"], "expected_target_fingerprint": newer["fingerprint"],
            "expected_revision": instance["revision"]})
        assert approved.status_code == 201, approved.text
        switched = client.post(f"/api/internal/instances/{instance['id']}/switch-approvals/{approved.json()['id']}/commit",
            json={"fingerprint": approved.json()["fingerprint"]})
        assert switched.status_code == 200, switched.text
        instance.update(switched.json())
        run("Beta", newer)
        assert outputs[0]["release_id"] != outputs[2]["release_id"]
        assert [c["run_id"] for c in claims] == [generation, *[o["id"] for o in outputs]]
        before = snapshot(store)
        save("before-page.json", before)
        with store.tx() as connection:
            grant = dict(connection.execute(select(grants).where(grants.c.principal_id == owner,
                grants.c.resource_id == resource, grants.c.tool_ref == "resource.read")).mappings().one())
        app = create_app(store, settings)

        @app.post("/test-only-chart-revoke")
        def revoke(authorization: str = Header()):
            assert case == "guards" and authorization == "Bearer synthetic-test-A" and not revocations
            response = client.post(f"/api/grants/{grant['id']}/revoke",
                json={"command": "revoke", "version": grant["revision"]})
            assert response.status_code == 200, response.text
            current = snapshot(store)
            assert all(current[k] == before[k] for k in before if k != "grants")
            revocations.append(current)
            return {"status": "REVOKED"}

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        web = Path("src/sim2act/web")
        assets = ["index.html", "app.css", *re.findall(r'<script[^>]+src="/([^"]+)"', (web / "index.html").read_text())]
        save("info.json", dict(base=f"http://127.0.0.1:{port}", case=case, project=project, app=aid,
            instance=instance["id"], empty=empty.json()["id"], original_release=original_release["id"],
            current_release=newer["id"], outputs=outputs,
            manifest=original_release["snapshot"]["draft"]["candidate"]["manifest"],
            web_hashes={name: hashlib.sha256((web / name).read_bytes()).hexdigest() for name in assets}))
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
            log_level="error", timeout_graceful_shutdown=5))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(.01)
        try:
            child = subprocess.run(["node", "tests/table_chart.cjs", str(tmp_path)],
                capture_output=True, text=True, timeout=240 if case == "guards" else 100)
        except subprocess.TimeoutExpired as error:
            save("driver-timeout.json", dict(timeout_seconds=error.timeout,
                stdout=str(error.stdout), stderr=str(error.stderr)))
            raise
        (tmp_path / "driver.log").write_text(child.stdout + child.stderr)
        assert child.returncode == 0, child.stdout + child.stderr
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS"
        after = snapshot(store)
        save("after-page.json", after)
        assert after == (revocations[0] if case == "guards" else before)
        assert len(revocations) == int(case == "guards")
        assert len(workers) == len(claims) == 4
        save("measurement.json", dict(status="PASS", tables=len(before), case=case,
            page_checks=len(proof["checks"]), page_gets=len(proof["requests"]),
            assets=len(proof["assets"]), charts=len(proof["charts"]), fixture_workers=4,
            fixture_mock_requests=len(sent), page_workers=0, page_posts=0, model_calls=0,
            native_browser="NOT_RUN", windows="NOT_RUN", pg="NOT_RUN", remote_ci="NOT_RUN"))
    finally:
        # Preserve observations before any shutdown assertion can mask the error.
        save("workers.json", workers)
        save("claims.json", claims)
        save("fixture-http.json", raw_http)
        save("after-page-or-failure.json", snapshot(store))
        if server:
            server.should_exit = True
        if thread:
            thread.join(10)
            save("shutdown.json", dict(server_thread_alive=thread.is_alive()))
            assert not thread.is_alive()
        client.close()
