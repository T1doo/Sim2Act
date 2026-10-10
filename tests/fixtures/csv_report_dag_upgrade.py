"""Run the actual archived two-node adapter and persist its immutable version/results."""

import hashlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from test_csv_dag_instances import create, enqueue, release, work

from sim2act import csv_dag_instances
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store

body = json.load(sys.stdin)
store = Store(body["database_url"], test_only=True)
if body["schema"]:
    store.engine = store.engine.execution_options(schema_translate_map={None: body["schema"]})
settings = Settings(body["database_url"], Path(body["data_root"]), mode="mock")
client = TestClient(create_app(store, settings))
client.headers["Authorization"] = "Bearer synthetic-test-A"
env = (store, settings, client, body["owner"], body["other"], body["project"], body["resource"])
_, _, _, _, rel = release(env)
i = create(env, rel)
a, _ = enqueue(env, i, rel)
work(env, a)
result = csv_dag_instances.inspect_job(store, body["owner"], a["run_id"],
    __import__("test_internal_lifecycle").limits(env))
Path(body["output"]).write_text(json.dumps(dict(release=rel, instance=i, accepted=a, result=result,
    module_path=csv_dag_instances.__file__,
    module_sha256=hashlib.sha256(Path(csv_dag_instances.__file__).read_bytes()).hexdigest()), indent=2))
client.close()
store.engine.dispose()
