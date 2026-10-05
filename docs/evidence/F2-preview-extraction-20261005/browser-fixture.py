"""Synthetic local-only source task and new input; no F1 run/model requests."""
import tempfile
from pathlib import Path

import uvicorn
from fastapi.testclient import TestClient

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store

root = Path(tempfile.mkdtemp(prefix='sim2act-pb-'))
url = 'sqlite:///' + str(root / 'fixture.db')
store = Store(url, test_only=True)
store.initialize()
store.user('SYNTHETIC P-B browser', 'synthetic-pb-browser')
app = create_app(store, Settings(url, root, mode='mock'))
with TestClient(app) as client:
    client.headers.update({'Authorization': 'Bearer synthetic-pb-browser'})
    project = client.post('/api/projects', json={'name': 'SYNTHETIC source project'}).json()['id']
    client.post('/api/projects', json={'name': 'SYNTHETIC other project'})
    def material(name, content):
        return client.post(f'/api/projects/{project}/resources', json={'name': name, 'format': 'csv', 'content': content}).json()['id']
    old = material('old.csv', 'amount,quantity\n1.25,7\n2.75,8\n')
    material('new.csv', 'amount,quantity\n10,2\n30,3\n')
    material('invalid.csv', 'amount\nnot-numeric\n')
    goal = {'title': 'SYNTHETIC completed preview source', 'goal': 'sum authorized CSV',
            'known': ['synthetic'], 'assumptions': [], 'unresolved': ['semantic acceptance not run'],
            'constraints': ['no outbound writes'], 'acceptance_checks': ['independent sum'], 'resource_refs': [old]}
    card = client.post(f'/api/projects/{project}/goal-cards', json=goal).json()['id']
    source = client.post(f'/api/goal-cards/{card}/candidates', json={'expected_version': 1, 'resource_id': old,
        'capability': 'csv.sum', 'request_key': 'source'}).json()['id']
    for key,column in [('source-success','amount'),('source-failure','missing')]:
        result = client.post(f'/api/apps/{source}/previews', json={'input': {'column': column}, 'request_key': key})
        assert result.status_code == 200
print('SYNTHETIC fixture ready on http://127.0.0.1:8071', flush=True)
uvicorn.run(app, host='127.0.0.1', port=8071, access_log=False)
