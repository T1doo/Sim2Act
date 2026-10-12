"""Local FileReader -> existing authorization/CSV engine, real HTTP and worker, LIVE=0."""

import csv
import hashlib
import io
import json
import shutil
import socket
import subprocess
import threading
import time
from decimal import Decimal
from pathlib import Path

import pytest
import uvicorn
from sqlalchemy import select

from sim2act.api import create_app
from sim2act.db import (
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_releases,
    principals,
    resources,
)
from sim2act.worker import Worker


@pytest.mark.parametrize("case", ["business", "guards", "lost-save", "read-after-save", "manual", "save-ABA", "uncertain-response", "read-ABA"])
def test_local_csv_file_actual_http(env, tmp_path, case):
    store, settings, _, owner, other_owner, project, _ = env
    if not shutil.which("node") or subprocess.run(
        ["node", "-e", "require.resolve('jsdom')"], capture_output=True, timeout=10
    ).returncode:
        pytest.skip("Developer Node/jsdom required")
    other = store.project(owner, "Other owned project")
    store.project(other_owner, "Other identity project")
    fixture = "city,amount,quantity\r\n杭州,1.25,4\r\n成都,19,5\r\n"
    fixture_bytes = fixture.encode("utf-8")
    (tmp_path / "真实 合成.csv").write_bytes(fixture_bytes)
    web = Path("src/sim2act/web")
    with store.tx() as c:
        before = {
            t.name: len(c.execute(select(t)).all())
            for t in (resources, grants, principals, internal_app_runs, internal_instance_data)
        }
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(
        json.dumps({"base": f"http://127.0.0.1:{port}", "project": project,
                    "other": other, "case": case,
                    "web_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in web.iterdir() if p.is_file()}})
    )
    app = create_app(store, settings)

    @app.post("/test-only-worker")
    def work():
        class NoProvider:
            def complete(self, *_args, **_kwargs):
                raise AssertionError("No model allowed")

            request = complete

        assert Worker(store, settings, NoProvider()).once()
        return {"test_only": True}

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(.01)
        outcome = subprocess.run(
            ["node", "tests/resource_file_ui.cjs", str(tmp_path)],
            capture_output=True, text=True, timeout=90,
        )
        (tmp_path / "driver.log").write_text(outcome.stdout + outcome.stderr)
        assert outcome.returncode == 0, outcome.stdout + outcome.stderr
        result = json.loads((tmp_path / "results.json").read_text())
        assert result["status"] == "PASS" and result["real_model_requests"] == 0
        with store.tx() as c:
            after = {
                t.name: len(c.execute(select(t)).all())
                for t in (resources, grants, principals, internal_app_runs, internal_instance_data)
            }
            saved = c.execute(select(resources).where(resources.c.name == "真实 合成.csv")).mappings().all()
            if case == "business":
                assert len(saved) == 1 and saved[0]["content"].encode() == fixture_bytes
                assert saved[0]["hash"] == hashlib.sha256(fixture_bytes).hexdigest()
                parsed = list(csv.DictReader(io.StringIO(fixture)))
                expected = [str(sum((Decimal(r[col]) for r in parsed), Decimal(0)))
                            for col in ("amount", "quantity")]
                runs = c.execute(select(internal_app_runs).where(
                    internal_app_runs.c.instance_id == result["instance_id"]
                ).order_by(internal_app_runs.c.result_version)).mappings().all()
                assert len(runs) == 2 and [r["output"]["sum"] for r in runs] == expected
                assert all(r["status"] == "SUCCEEDED" for r in runs)
                assert [r["result_version"] for r in runs] == [1, 2]
                assert len({r["id"] for r in runs}) == 2
                release = c.execute(select(internal_releases).where(
                    internal_releases.c.id == result["release_id"]
                )).mappings().one()
                assert release["project_id"] == result["project_id"]
                assert after["grants"] - before["grants"] == 8  # Existing project2 + Save4 + CSV draft2.
                assert after["principals"] - before["principals"] == 2  # New project + CSV app.
                assert after["internal_instance_data"] - before["internal_instance_data"] == 2
            elif case == "guards":
                assert before == after
            else:
                count = 4 if case == "uncertain-response" else 1
                assert after["resources"] - before["resources"] == count
                assert after["grants"] - before["grants"] == 4 * count
                assert after["principals"] == before["principals"]
                assert after["internal_app_runs"] == before["internal_app_runs"]
                assert after["internal_instance_data"] == before["internal_instance_data"]
                assert len(saved) == (0 if case == "manual" else count)
    finally:
        server.should_exit = True
        thread.join(8)
        assert not thread.is_alive()
