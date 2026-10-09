import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import env
from test_csv_dag_upgrade import raw_history_hashes
from test_delivery_graph_apps import snapshot
from sim2act.db import fingerprint, meta

ROOT = Path(os.environ['SIM2ACT_REPORT_UPGRADE_ROOT'])
OLD = ROOT / 'old-report-source'


def test_old_report_persisted_receipts_cold_upgrade_without_rewrite(env, tmp_path):
    proof = tmp_path / 'old-report-proof.json'
    body = dict(database_url=env[1].database_url,
                schema=env[0].engine.get_execution_options().get('schema_translate_map', {}).get(None),
                data_root=str(tmp_path), owner=env[3], other=env[4], project=env[5],
                resource=env[6], output=str(proof))
    child = subprocess.run([sys.executable, str(ROOT / 'report_upgrade_child.py')],
                           cwd=Path.cwd(), input=json.dumps(body), text=True, capture_output=True,
                           env={**os.environ, 'PYTHONPATH': str(OLD / 'src') + os.pathsep + str(OLD / 'tests'),
                                'LIVE': '0', 'SIM2ACT_LIVE_ENABLED': 'false'}, timeout=90)
    (tmp_path / 'child.log').write_text(child.stdout + child.stderr)
    assert child.returncode == 0, child.stdout + child.stderr
    old = json.loads(proof.read_text())
    source = OLD / 'src/sim2act/report_presentations.py'
    assert Path(old['module_path']).resolve() == source.resolve()
    assert old['module_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    before = snapshot(env)
    assert fingerprint(before) == fingerprint(old['snapshot'])
    names = list(meta.tables)
    raw_before = raw_history_hashes(env[0], names)
    env[0].initialize()  # Explicit ordinary upgrade; runtime never invokes DDL.
    assert snapshot(env) == before
    assert raw_history_hashes(env[0], names) == raw_before
    current = env[2].get(old['url'])
    assert current.status_code == 200, current.text
    assert current.json() == old['history']
    assert current.json()['items'][0]['checks'][0]['text'] == old['output']['explanation']
    assert env[2].get('/api/apps/' + old['app']['id']).json()['candidate'] == old['app']['candidate']
    replay = env[2].post(old['url'], json=old['definition'])
    checked = env[2].post(old['url'] + '/text-version/checks', json=old['check_body'])
    assert replay.status_code == 201 and replay.json()['cached'] is True
    assert checked.status_code == 201 and checked.json()['cached'] is True
    assert checked.json()['check_fingerprint'] == old['checked']['check_fingerprint']
    assert checked.json()['overall_run_acceptance'] == 'NOT_ACCEPTED'
    assert checked.json()['actual_material_verification'] == 'PENDING'
    assert checked.json()['formal_publication_enabled'] is False
    assert snapshot(env) == before
    assert raw_history_hashes(env[0], names) == raw_before
    assert old['mock_transport_calls'] == 4
    (tmp_path / 'upgrade-proof.json').write_text(json.dumps(dict(
        source_sha='ffda5b00a9a1469b454728adb5a0005016cd0a55',
        current_sha='51487fd4787eae66f09f8ff2b01492d8f9c13503',
        source_path=str(source), module_sha256=old['module_sha256'],
        tables_preserved=names, literal_json_storage_preserved=True,
        history=current.json(), models_real=0, status='PASS'), ensure_ascii=False, indent=2))
