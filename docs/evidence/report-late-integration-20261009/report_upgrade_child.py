import hashlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from test_conditional_run_bindings import env as bounded_env
from test_delivery_graph_apps import snapshot
from test_report_presentations import prepared
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store
import sim2act.report_presentations as presentation_module

body = json.load(sys.stdin)
store = Store(body['database_url'], test_only=True)
if body['schema']:
    store.engine = store.engine.execution_options(schema_translate_map={None: body['schema']})
settings = Settings(body['database_url'], Path(body['data_root']), mode='mock')
client = TestClient(create_app(store, settings))
client.headers['Authorization'] = 'Bearer synthetic-test-A'
base = (store, settings, client, body['owner'], body['other'], body['project'], body['resource'])
env = bounded_env.__wrapped__(base)
app, graph, url, definition, output, wires = prepared(env, Path(body['data_root']))
reply = client.post(url, json=definition)
assert reply.status_code == 201, reply.text
patch = reply.json()
check_body = dict(expected_patch_fingerprint=patch['patch_fingerprint'], request_key='old-source-check')
checked = client.post(url + '/text-version/checks', json=check_body)
assert checked.status_code == 201, checked.text
history = client.get(url)
assert history.status_code == 200, history.text
Path(body['output']).write_text(json.dumps(dict(
    app=app, url=url, definition=definition, check_body=check_body,
    patch=patch, checked=checked.json(), history=history.json(), output=output,
    snapshot=snapshot(env), mock_transport_calls=len(wires),
    module_path=presentation_module.__file__,
    module_sha256=hashlib.sha256(Path(presentation_module.__file__).read_bytes()).hexdigest(),
), ensure_ascii=False, indent=2))
client.close()
store.engine.dispose()
