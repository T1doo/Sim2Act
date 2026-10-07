"""Actual product DOM to HTTP/Worker/Mock binding; no gold or product provider activation."""

from pathlib import Path
import hashlib
import json
import shutil
import socket
import subprocess
import threading
import time

import pytest
import uvicorn
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, update
from test_conditional_run_bindings import POLICY, envelope, factory
from test_independent_binding import handwritten
import conftest

from sim2act.api import create_app
from sim2act.conditional_runs import candidate_for
from sim2act.db import (
    attempts,
    grants,
    operations,
    principals,
    protocol_jobs,
    protocol_request_slots,
    resources,
    runs,
)
from sim2act.protocol_pool import initialize_pools
from sim2act.worker import Worker


@pytest.fixture
def env(tmp_path):
    base_fixture = conftest.env.__wrapped__(tmp_path)
    baseline = next(base_fixture)
    initialize_pools(baseline[0], offline_limit=14)
    ids=[]
    for name in ["Independent public source", "Independent fresh cold source"]:
        reply=baseline[2].post(f"/api/projects/{baseline[5]}/resources",json={"name":name,"format":"txt","content":POLICY.read_text()})
        assert reply.status_code==201
        ids.append(reply.json()["id"])
    try:
        yield (*baseline[:6],*ids)
    finally:
        try: next(base_fixture)
        except StopIteration: pass


def test_source_bound_product_actual_http_dom(env, tmp_path):
    if (
        not shutil.which("node")
        or subprocess.run(
            ["node", "-e", "require.resolve('jsdom')"], capture_output=True, timeout=10
        ).returncode
    ):
        pytest.skip("Developer Node/jsdom required")
    store, settings, _, owner, _, pid, source, fresh = env
    other = store.project(owner, "Product source ABA project")
    with store.tx() as c:
        baseline = [
            c.execute(select(func.count()).select_from(t)).scalar() for t in [principals, grants]
        ]
    app = create_app(store, settings)
    wires = []
    metadata_fault = [False]

    @app.middleware("http")
    async def synthetic_metadata_failure(request, call_next):
        if (
            metadata_fault[0]
            and request.method == "GET"
            and request.url.path == f"/api/projects/{pid}/resources"
        ):
            return JSONResponse({"error": {"code": "AUTH_LIST_UNAVAILABLE"}}, status_code=503)
        return await call_next(request)

    @app.post("/test-only-bounded-metadata/{mode}")
    def set_metadata_failure(mode: str):
        metadata_fault[0] = mode == "fail"
        return {"test_only": True}

    @app.post("/test-only-bounded-work/{phase}")
    def execute(phase: str):
        with store.tx() as c:
            job = (
                c.execute(
                    select(protocol_jobs)
                    .join(runs, runs.c.id == protocol_jobs.c.run_id)
                    .where(runs.c.project_id == pid, runs.c.status == "QUEUED")
                )
                .mappings()
                .one()
            )
        snapshot = job["accepted_snapshot"]
        if phase == "source":
            values = [envelope(resource=source), envelope(handwritten(680))]
        elif phase == "extract":
            values = [envelope(candidate_for(snapshot["contract"], source))]
        elif phase == "cold":
            values = [
                envelope(handwritten(500))
            ]
        else:
            assert phase == "no-provider"
            assert Worker(store, settings).once()
            return {"test_only": True}
        assert job["kind"] == phase
        worker = Worker(
            store, settings, protocol_runner_factory=factory(env, tmp_path, values, wires)
        )
        assert worker.once() and not values
        return {"test_only": True}

    @app.post("/test-only-bounded-source-version/{mode}")
    def source_version(mode: str):
        value = POLICY.read_text() + (
            "\nChanged bounded source version." if mode == "change" else ""
        )
        with store.tx() as c:
            c.execute(
                update(resources)
                .where(resources.c.id == source)
                .values(content=value, hash=hashlib.sha256(value.encode()).hexdigest())
            )
        return {"test_only": True}

    @app.post("/test-only-bounded-revoke")
    def revoke():
        with store.tx() as c:
            c.execute(update(grants).where(grants.c.resource_id == source).values(revoked=True))
        return {"test_only": True}

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(
        json.dumps(
            {
                "base": f"http://127.0.0.1:{port}",
                "project": pid,
                "other": other,
                "resource": source,
                "fresh": fresh,
            }
        )
    )
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        end = time.time() + 10
        while not server.started:
            assert thread.is_alive() and time.time() < end
            time.sleep(0.01)
        out = subprocess.run(
            ["node", "/tmp/core-conditional-integration-review/independent-loopback.cjs", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=90,
        )
        (tmp_path / "dom-driver.log").write_text(out.stdout + out.stderr)
        assert out.returncode == 0, out.stdout + out.stderr
        result = json.loads((tmp_path / "results.json").read_text())
        assert result["status"] == "PASS" and len(result["checks"]) >= 22
        shutil.copy2(tmp_path / "results.json", "/tmp/core-conditional-integration-review/independent-loopback-results.json")
        assert len(wires) == 4
        with store.tx() as c:
            assert c.execute(select(func.count()).select_from(attempts)).scalar() == 4
            slots = list(c.execute(select(protocol_request_slots)).mappings())
            assert len(slots) == 4 and len({v["pool_id"] for v in slots}) == 1
            authority_after = [
                c.execute(select(func.count()).select_from(t)).scalar()
                for t in [principals, grants]
            ]
            assert authority_after == baseline
            audit = {
                "actual_attempts": [
                    {"id": a["id"], "run_id": a["run_id"], "status": a["status"]}
                    for a in c.execute(select(attempts)).mappings()
                ],
                "actual_operations": [
                    {
                        "id": o["id"],
                        "run_id": o["run_id"],
                        "status": o["status"],
                        "tool_ref": o["tool_ref"],
                    }
                    for o in c.execute(select(operations)).mappings()
                ],
                "slots_count": len(slots),
                "chain_pool_count": len({v["pool_id"] for v in slots}),
                "authority_before": baseline,
                "authority_after": authority_after,
                "mock_wire_requests": len(wires),
                "live_requests": 0,
            }
            (tmp_path / "actual-ledger.json").write_text(json.dumps(audit, indent=2))
            Path("/tmp/core-conditional-integration-review/independent-loopback-ledger.json").write_text(json.dumps(audit,indent=2))
            (tmp_path / "mock-wires.json").write_text(
                json.dumps(wires, ensure_ascii=False, indent=2)
            )
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
