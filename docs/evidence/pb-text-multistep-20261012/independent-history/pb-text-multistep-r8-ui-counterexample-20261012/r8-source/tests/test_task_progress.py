"""Readonly progress projection from real normal Mock worker receipts plus UI boundaries."""
import json
import shutil
import subprocess

import pytest

from sim2act.worker import Worker


def test_task_progress_actual_worker_and_ui_boundaries(env, tmp_path):
    store, settings, client, *_ = env
    if not shutil.which('node') or subprocess.run(['node', '-e', "require.resolve('jsdom')"],
                                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                                timeout=10).returncode:
        pytest.skip('Developer Node/jsdom required')
    project = env[5]
    response = client.post(f'/api/projects/{project}/runs', json={
        'goal': 'Readonly progress sample', 'resource_refs': [env[6]], 'request_key': 'progress',
    })
    assert response.status_code == 202
    assert Worker(store, settings).once()
    run = client.get('/api/runs/' + response.json()['run_id']).json()
    assert run['status'] == 'PARTIAL' and run['result']['mode'] == 'MOCK'
    data, result_path = tmp_path / 'received-run.json', tmp_path / 'progress-results.json'
    data.write_text(json.dumps(run))
    outcome = subprocess.run(['node', 'tests/task_progress.cjs', str(data), str(result_path)], capture_output=True, text=True, timeout=30)
    assert outcome.returncode == 0, outcome.stdout + outcome.stderr
    result = json.loads(result_path.read_text())
    assert result['status'] == 'PASS' and len(result['checks']) >= 14
