"""Run only under archived old PYTHONPATH against a caller-owned test schema."""

import hashlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from test_column_patches import check_body, setup, url
from test_delivery_graph_apps import snapshot

from sim2act import csv_dag
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store
from sim2act.worker import Worker


class NoModel:
    def respond(self, *args, **kwargs):
        raise AssertionError("Upgrade engineering fixture must never call a model")


body = json.load(sys.stdin)
store = Store(body["database_url"], test_only=True)
if body["schema"]:
    store.engine = store.engine.execution_options(schema_translate_map={None: body["schema"]})
settings = Settings(body["database_url"], Path(body["data_root"]), mode="mock")
client = TestClient(create_app(store, settings))
client.headers["Authorization"] = "Bearer synthetic-test-A"
env = (store, settings, client, body["owner"], body["other"], body["project"], body["resource"])
other_aid, _, _, _, _ = setup(env)
aid, _, graph, patch_body, preview = setup(env)
patch = client.post(url(env, aid), json=patch_body)
assert patch.status_code == 201, patch.text
checked = client.post(url(env, aid) + "/new-definition/checks", json=check_body(patch.json()))
assert checked.status_code == 201 and checked.json()["outputs"]["patched"]["sum"] == "15"
other_app = client.get(f"/api/apps/{other_aid}").json()
other_graph = client.post(f"/api/projects/{body['project']}/apps/{other_aid}/delivery-graph/derive", json=dict(
    expected_candidate_fingerprint=other_app["fingerprint"], request_key="other-final-authority"))
assert other_graph.status_code == 201, other_graph.text
base = f"/api/projects/{body['project']}/apps/{aid}/csv-dag"
plan_body = dict(expected_candidate_fingerprint=graph["candidate_fingerprint"],
                 expected_graph_fingerprint=graph["graph_fingerprint"], column="quantity",
                 request_key="old-plan")
plan = client.post(base, json=plan_body)
assert plan.status_code == 201, plan.text
confirmation = dict(expected_plan_fingerprint=plan.json()["plan_fingerprint"],
                    consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key="old-run")
accepted = client.post(base + "/old-plan/runs", json=confirmation)
assert accepted.status_code == 202, accepted.text
worker = Worker(store, settings, NoModel())
job = store.claim(worker.id, settings.lease_seconds)
assert job["id"] == accepted.json()["run_id"]
worker.process(job)
result = client.get(f"/api/csv-dag/runs/{job['id']}")
assert result.status_code == 200 and result.json()["status"] == "SUCCEEDED"
Path(body["output"]).write_text(json.dumps(dict(
    old_module_path=csv_dag.__file__,
    old_module_sha256=hashlib.sha256(Path(csv_dag.__file__).read_bytes()).hexdigest(),
    app_id=aid, other_app_id=other_aid, base=base, old_plan=plan.json(),
    old_confirmation=confirmation, old_run=job["id"], old_result=result.json(),
    old_preview=preview, old_snapshot=snapshot(env)), ensure_ascii=False, indent=2))
client.close()
store.engine.dispose()
