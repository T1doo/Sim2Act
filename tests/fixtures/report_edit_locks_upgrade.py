"""Run under exact old PYTHONPATH against a caller-owned synthetic test schema."""

import hashlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from test_conditional_run_bindings import env as bounded_env
from test_delivery_graph_apps import snapshot
from test_report_presentations import prepared

from sim2act import manual_locks
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
base = (store, settings, client, body["owner"], body["other"], body["project"], body["resource"])
env = bounded_env.__wrapped__(base)
app, anchor, url, definition, output, wires = prepared(env, Path(body["data_root"]))
patch = client.post(url, json=definition)
assert patch.status_code == 201, patch.text
checked = client.post(
    url + "/text-version/checks",
    json=dict(
        expected_patch_fingerprint=patch.json()["patch_fingerprint"], request_key="old-source-check"
    ),
)
assert checked.status_code == 201, checked.text
node = next(n for n in anchor["graph"]["nodes"] if n["key"] == "view:text:decision")
request = dict(
    expected_graph_fingerprint=anchor["graph_fingerprint"],
    expected_graph_revision=anchor["graph_revision"],
    change=dict(
        node_id=node["id"],
        expected_revision=node["revision"],
        expected_content_fingerprint=node["content_fingerprint"],
    ),
    expected_lock_revision=0,
    locked=True,
    request_key="unsupported-old-report-lock",
    consent=manual_locks.CONSENT,
)
before = snapshot(env)
denied = client.post(url.removesuffix("report-presentations") + "manual-locks", json=request)
assert denied.status_code == 400 and denied.json()["error"]["code"] == "UNSUPPORTED_CAPABILITY", (
    denied.text
)
assert snapshot(env) == before
Path(body["output"]).write_text(
    json.dumps(
        dict(
            app=app,
            anchor=anchor,
            url=url,
            lock_request=request,
            definition=definition,
            patch=patch.json(),
            check=checked.json(),
            output=output,
            snapshot=before,
            old_negative_status=denied.status_code,
            old_negative_error=denied.json(),
            old_manual_module=str(Path(manual_locks.__file__).resolve()),
            old_manual_sha256=hashlib.sha256(Path(manual_locks.__file__).read_bytes()).hexdigest(),
            mock_calls=len(wires),
        ),
        ensure_ascii=False,
        indent=2,
    )
)
client.close()
store.engine.dispose()
