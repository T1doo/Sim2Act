"""One bounded existing-Windows-runner UI check, synthetic seed and no live model."""
import argparse
import base64
import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient
from sim2act import synthetic_workspace as workspace
from sim2act.api import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    if os.name != 'nt' or os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('Actual authorized Windows Actions runner required')
    root = args.root.resolve()
    assert root.is_relative_to(Path(os.environ['RUNNER_TEMP']).resolve()) and not root.exists()
    root.mkdir()
    repo = Path(__file__).resolve().parents[1]
    # The existing fixture performs three explicit MockTransport definition calls.
    # Runtime is the unchanged installed synthetic-workspace NeverModel service.
    sys.path.insert(0, str(repo/'tests'))
    from test_pa_spec_apps import SOURCE, material, generate, confirm, instance
    data_root, store, marker = workspace.open_workspace(root/'workspace', new=True)
    settings = replace(workspace.settings_for(data_root), goal_planner_provider='intern-s2')
    with TestClient(create_app(store, settings)) as client:
        client.headers['Authorization'] = 'Bearer '+workspace.TOKEN
        project = client.post('/api/projects', json={'name':'Synthetic desktop recovery'}).json()['id']
        resource, card = material(client, project, SOURCE)
        data = store, settings, client, marker['principal_id'], project, resource, card
        generation, result, sent = generate(data)
        assert len(sent) == 3
        app = confirm(data, generation, result)
        assert app.status_code == 200, app.text
        release, inst = instance(data, app.json()['id'])
        csv = client.post(f'/api/projects/{project}/resources', json={'name':'Synthetic totals.csv','format':'csv','content':'amount,tax\n10,5\n20,10\n'})
        assert csv.status_code == 201, csv.text
        draft = client.post(f'/api/projects/{project}/apps/csv-preview', json={'name':'Synthetic CSV desktop','resource_id':csv.json()['id'],'goal':'Sum chosen numeric column'})
        assert draft.status_code == 201, draft.text
    store.engine.dispose()
    info = {'root':str(root),'data_dir':str(data_root),'project':project,'spec_instance':inst['id'],
        'spec_app':app.json()['id'],'csv_app':draft.json()['id'],'python':sys.executable,
        'commit':os.environ['GITHUB_SHA'],'fixture_mock_definition_calls':3}
    (root/'info.json').write_text(json.dumps(info))
    try:
        subprocess.run(['node','scripts/browser-ci/desktop-workspace.cjs',str(root)],cwd=repo,check=True,timeout=210)
    finally:
        # Preserve the original no-artifact-upload, synthetic allowlisted log route.
        for name in ['desktop-results.json','workspace-1366x768.png','workspace-1440x900.png','failure.png']:
            file = root/name
            if not file.is_file():
                continue
            raw = file.read_bytes()
            assert len(raw) <= 2_000_000
            encoded = base64.b64encode(raw).decode()
            print('SIM2ACT_BROWSER_FILE '+json.dumps({'name':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'chunks':(len(encoded)+3999)//4000}))
            for serial, begin in enumerate(range(0,len(encoded),4000)):
                print(f'SIM2ACT_BROWSER_CHUNK {name} {serial} {encoded[begin:begin+4000]}')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
