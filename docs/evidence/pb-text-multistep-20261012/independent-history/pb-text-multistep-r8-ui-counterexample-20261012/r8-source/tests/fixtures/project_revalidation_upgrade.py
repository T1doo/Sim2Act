"""Create genuine previous-source Report/CSV plan and prove new API absent."""

import hashlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from test_conditional_run_bindings import env as bounded_env
from test_delivery_graph_apps import snapshot
from test_report_presentations import prepared

from sim2act import api
from sim2act.config import Settings
from sim2act.db import Store

body = json.load(sys.stdin)
store = Store(body["database_url"], test_only=True)
if body["schema"]:
    store.engine = store.engine.execution_options(schema_translate_map={None: body["schema"]})
settings = Settings(body["database_url"], Path(body["data_root"]), mode="mock")
client = TestClient(api.create_app(store, settings))
client.headers["Authorization"] = "Bearer synthetic-test-A"
env = bounded_env.__wrapped__(
    (store, settings, client, body["owner"], body["other"], body["project"], body["resource"])
)
app, graph, path, _, _, wires = prepared(env, Path(body["data_root"]), peer=True)
base = path.removesuffix("report-presentations") + "scope-checks"
before = snapshot(env)
negative = client.get(base + "/options", params={"plan_key": "presentation-plan"})
assert negative.status_code == 404 and snapshot(env) == before, negative.text
Path(body["output"]).write_text(
    json.dumps(
        dict(
            app=app,
            graph=graph,
            base=base,
            snapshot=before,
            old_api=str(Path(api.__file__).resolve()),
            old_api_hash=hashlib.sha256(Path(api.__file__).read_bytes()).hexdigest(),
            old_negative_status=negative.status_code,
            mock_calls=len(wires),
        ),
        ensure_ascii=False,
        indent=2,
    )
)
client.close()
store.engine.dispose()
