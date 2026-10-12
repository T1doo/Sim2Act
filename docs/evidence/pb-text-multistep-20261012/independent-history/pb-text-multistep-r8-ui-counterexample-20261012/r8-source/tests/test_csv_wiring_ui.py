"""Each allowed wiring tuple through real loopback HTTP, product DOM and worker."""

import csv
import hashlib
import io
import json
import shutil
import socket
import subprocess
import threading
import time
from fractions import Fraction
from pathlib import Path

import pytest
import uvicorn
from fastapi import Header
from test_csv_dag import CSV, NoModel, setup

from sim2act.api import create_app
from sim2act.worker import Worker


@pytest.mark.parametrize("aggregate,resource,source_hash", [(a, r, h) for a in [0, 1] for r in [0, 1] for h in [0, 1]])
def test_all_allowed_wire_choices_actual_product_http_dom(env, tmp_path, aggregate, resource, source_hash):
    _, _, plan, _, previous, job = setup(env)
    previous.model = NoModel()
    previous.process(job)
    app = create_app(env[0], env[1])
    worker = Worker(env[0], env[1], NoModel())

    @app.post("/__fixture__/work")
    def work(body: dict, authorization: str = Header()):
        assert authorization == "Bearer synthetic-test-A"
        claim = env[0].claim(worker.id, env[1].lease_seconds)
        assert claim["id"] == body["run_id"]
        worker.process(claim)
        return {"run_id": claim["id"]}

    rows = list(csv.DictReader(io.StringIO(CSV.read_text())))
    expected = {column: str(sum((Fraction(row[column]) for row in rows), Fraction()))
                for column in ["amount", "quantity"]}
    assert expected == {"amount": "30", "quantity": "15"}
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(json.dumps(dict(base=f"http://127.0.0.1:{port}",
        project=env[5], app=plan["app_id"], choices=[aggregate, resource, source_hash], expected=expected)))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        until = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < until
            time.sleep(.01)
        assert shutil.which("node")
        result = subprocess.run(["node", "tests/csv_wiring_combinations.cjs", str(tmp_path)],
                                capture_output=True, text=True, timeout=90)
        (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and proof["choices"] == [aggregate, resource, source_hash]
        assert len(proof["checks"]) == 10
        web = Path(__file__).parents[1] / "src/sim2act/web"
        assert proof["loaded_source_sha256"] == {name: hashlib.sha256((web / name).read_bytes()).hexdigest()
                                               for name in proof["loaded_source_sha256"]}
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
