"""Separate owned-process audit of a durable skipped prefix, no repeated suite."""

# ruff: noqa: I001 -- standalone audit imports its owned pytest fixture
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import select, update
from conftest import env  # noqa: F401 -- reuse owned isolated fixture
from test_controlled_branches import proof, setup, start
from test_delivery_graph_apps import snapshot

from sim2act import csv_dag as dag
from sim2act.db import events, fingerprint, operations, runs
from sim2act.errors import DomainError

CHILD = '''
import hashlib,json,sys
from pathlib import Path
from sim2act import csv_dag
from sim2act.config import Settings
from sim2act.contracts import Limits
from sim2act.db import Store
from sim2act.worker import Worker
class NoModel:
    def request(self,*a,**k): raise AssertionError("No provider invocation allowed")
info=json.loads(Path(sys.argv[1]).read_text())
store=Store(info["url"],test_only=True)
if info["schema"]: store.engine=store.engine.execution_options(schema_translate_map={None:info["schema"]})
s=Settings(info["url"],Path(sys.argv[1]).parent,mode="mock")
w=Worker(store,s,NoModel())
job=store.claim(w.id,s.lease_seconds)
assert job["id"]==info["run_id"] and job["fence"]>info["old_fence"]
w.process(job)
result=csv_dag.inspect_job(store,info["user"],job["id"],Limits(**{k:getattr(s,k) for k in Limits.model_fields}))
Path(sys.argv[2]).write_text(json.dumps({"job":result,"claimed_fence":job["fence"],"loaded_module":csv_dag.__file__,"module_sha256":hashlib.sha256(Path(csv_dag.__file__).read_bytes()).hexdigest()},indent=2))
store.engine.dispose()
'''


def test_actual_child_claims_new_fence_and_preserves_skipped_prefix(env, tmp_path):  # noqa: F811 -- imported pytest fixture
    _, base, plan, _ = setup(env, target="aggregate")
    worker, old, _ = start(env, base, plan, {"include_report": False})
    assert dag.advance(worker, old)
    assert dag.advance(worker, old)
    prefix = proof(env, old)["steps"]
    assert [step["status"] for step in prefix] == ["VERIFIED", "SKIPPED"]
    with env[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == old["id"]).values(lease_until=0))
    before = snapshot(env)
    info = dict(url=env[1].database_url, schema=env[0].engine.get_execution_options().get("schema_translate_map", {}).get(None),
        run_id=old["id"], old_fence=old["fence"], user=env[3])
    private = tmp_path / "owned-child.json"
    private.write_text(json.dumps(info))
    output = tmp_path / "cold-reclaim-proof.json"
    try:
        child = subprocess.run([sys.executable, "-c", CHILD, str(private), str(output)],
            capture_output=True, text=True, timeout=30, env={**os.environ, "LIVE": "0", "SIM2ACT_LIVE_ENABLED": "false"})
        assert child.returncode == 0, child.stdout + child.stderr
    finally:
        private.unlink()
    saved = json.loads(output.read_text())
    actual = proof(env, old)
    assert saved["module_sha256"] == hashlib.sha256(Path(dag.__file__).read_bytes()).hexdigest()
    assert Path(saved["loaded_module"]).resolve() == Path(dag.__file__).resolve()
    assert saved["claimed_fence"] == old["fence"] + 2
    assert fingerprint(saved["job"]) == fingerprint(actual)
    assert fingerprint(actual["steps"][:2]) == fingerprint(prefix)
    assert actual["status"] == "PARTIAL" and actual["result"]["output"] is None
    assert actual["steps"][2]["branch_decision"]["reason"] == "DEPENDENCY_SKIPPED"
    with env[0].engine.connect() as c:
        assert len(c.execute(select(operations.c.id).where(operations.c.run_id == old["id"])).all()) == 1
        assert len(c.execute(select(events.c.id).where(events.c.run_id == old["id"], events.c.kind == "CSV_DAG_STEP_SKIPPED")).all()) == 2
    after = snapshot(env)
    for name in before:
        if name not in {"runs", "events"}:
            assert fingerprint(before[name]) == fingerprint(after[name]), name
    with pytest.raises(DomainError):
        dag.advance(worker, old)
    assert fingerprint(snapshot(env)) == fingerprint(after)
